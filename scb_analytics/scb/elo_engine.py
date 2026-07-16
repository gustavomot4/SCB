"""Motor Elo do SCB: reconstrução cronológica por liga (port do scm/elo_engine, D-02).

Consome `matches` (do ingest) e grava:
  - `match_ratings`   : rating PRÉ-jogo (snapshot point-in-time — anti look-ahead)
  - `ratings_current` : estado final por clube (+ σ_R, provisório se <30 jogos)

Adaptações de LIGA (contrato SCB v1.0 §1/§2/§3):
  - K único por liga [a calibrar] (era por tipo de torneio em seleções);
  - mando em TODO jogo: dr = R_h − R_a + H_liga (não existe "neutro" na fonte);
  - hook de REGRESSÃO DE TEMPORADA (candidato C5, OFF): na 1ª aparição do clube
    numa temporada nova, R ← (1−ρ)·R + ρ·1500. Substitui o `_revert` do SCM
    (rejeitado lá; a lista-morta não transfere — D-05 — mas re-testar é na M6);
  - ligas isoladas por construção (clubes de ligas distintas nunca se enfrentam;
    zero-sum por jogo conserva a média 1500 POR liga).

Uso:
    python -m scb.elo_engine --db dados/scb.sqlite --top 10
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import config, db
from .ingest import DEFAULT_DB


@dataclass(frozen=True)
class EloParams:
    init: float = 1500.0             # rating inicial (promovido idem + σ alto; prior manual = candidato)
    provisional_games: int = 30      # <30 jogos => provisório
    sigma_floor: float = 40.0        # σ_R mínimo (maduro)              [a calibrar]
    sigma_provisional: float = 200.0 # σ_R de estreante (n=0)           [a calibrar]
    sigma_tau: float = 20.0          # escala de decaimento de σ_R      [a calibrar]
    season_rho: Optional[float] = None   # None = POR LIGA via config (D-25); valor
                                         # explícito força o MESMO ρ em todas (testes/gates)


def we(dr: float) -> float:
    """Expectativa de pontuação do Elo. we(0)=0.5, we(100)≈0.640, we(-x)=1-we(x)."""
    return 1.0 / (1.0 + 10.0 ** (-dr / 400.0))


def g_factor(goal_diff: int) -> float:
    """Multiplicador de margem (anti-saturação) — família herdada do contrato §1 [re-gate M6]."""
    m = abs(goal_diff)
    if m <= 1:
        return 1.0
    if m == 2:
        return 1.5
    return (11.0 + m) / 8.0


def sigma_r(n_games: int, p: EloParams) -> float:
    """σ_R decrescente com o nº de jogos (estreante incerto -> maduro confiável)."""
    return p.sigma_floor + (p.sigma_provisional - p.sigma_floor) * math.exp(-n_games / p.sigma_tau)


def run(conn, params: EloParams = EloParams()) -> dict:
    """Reconstrói o Elo cronologicamente (todas as ligas). Idempotente (limpa e refaz)."""
    db.init_schema(conn)
    conn.execute("DELETE FROM match_ratings")
    conn.execute("DELETE FROM ratings_current")

    ratings: dict[int, float] = {}
    ngames: dict[int, int] = {}
    last_season: dict[int, int] = {}

    rows = conn.execute(
        """SELECT match_id, league, season, date, home_team_id, away_team_id,
                  home_score, away_score
           FROM matches ORDER BY date, match_id"""
    ).fetchall()

    for r in rows:
        h, a = r["home_team_id"], r["away_team_id"]
        rh = ratings.get(h, params.init)
        ra = ratings.get(a, params.init)
        rho = params.season_rho if params.season_rho is not None \
            else config.season_rho_for(r["league"])    # D-25: POR LIGA (BRA=0,30; E0=0)
        if rho > 0:                                    # virada de temporada (C5 adotado no BRA)
            if last_season.get(h) is not None and r["season"] > last_season[h]:
                rh = (1 - rho) * rh + rho * params.init
            if last_season.get(a) is not None and r["season"] > last_season[a]:
                ra = (1 - rho) * ra + rho * params.init
            ratings[h], ratings[a] = rh, ra            # regressão é estado, não só leitura
        nh, na = ngames.get(h, 0), ngames.get(a, 0)

        dr = rh - ra + config.h_for(r["league"])       # mando em TODO jogo (liga)
        we_home = we(dr)

        # snapshot PRÉ-jogo (point-in-time) ANTES de atualizar — espinha do anti look-ahead
        conn.execute(
            """INSERT OR REPLACE INTO match_ratings
               (match_id, home_elo_pre, away_elo_pre, home_n_pre, away_n_pre, dr, we_home)
               VALUES (?,?,?,?,?,?,?)""",
            (r["match_id"], rh, ra, nh, na, dr, we_home),
        )

        gd = r["home_score"] - r["away_score"]
        w = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
        delta = config.k_for(r["league"]) * g_factor(gd) * (w - we_home)

        ratings[h] = rh + delta                        # zero-sum: o que um ganha, o outro perde
        ratings[a] = ra - delta
        ngames[h], ngames[a] = nh + 1, na + 1
        last_season[h] = last_season[a] = r["season"]

    for team_id, elo in ratings.items():
        n = ngames[team_id]
        conn.execute(
            """INSERT OR REPLACE INTO ratings_current
               (team_id, elo, sigma_r, n_games, provisional) VALUES (?,?,?,?,?)""",
            (team_id, elo, sigma_r(n, params), n, 1 if n < params.provisional_games else 0),
        )
    db.set_meta(conn, "elo_k", str(config.K_LIGA))
    db.set_meta(conn, "elo_h", str(config.H_LIGA))
    db.set_meta(conn, "elo_season_rho", params.season_rho)
    conn.commit()
    return {"matches": len(rows), "teams": len(ratings)}


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Reconstrói o Elo histórico por liga.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--top", type=int, default=10, help="imprime as N maiores por liga (sanidade)")
    args = p.parse_args(argv)

    if not Path(args.db).exists():
        print(f"[erro] SQLite não encontrado: {args.db}. Rode `python -m scb.ingest` primeiro.")
        return 1

    with db.session(args.db) as conn:
        stats = run(conn)
        print(f"Elo reconstruído: {stats['matches']} jogos, {stats['teams']} clubes")
        for lg in [r[0] for r in conn.execute("SELECT DISTINCT league FROM matches ORDER BY league")]:
            print(f"\nTop {args.top} {lg} (sanidade de futebol — confira a olho):")
            for row in conn.execute(
                """SELECT t.name, r.elo, r.n_games, r.provisional
                   FROM ratings_current r JOIN teams t USING (team_id)
                   WHERE t.team_id IN (SELECT DISTINCT home_team_id FROM matches WHERE league=?)
                   ORDER BY r.elo DESC LIMIT ?""", (lg, args.top)):
                flag = " (prov)" if row["provisional"] else ""
                print(f"  {row['elo']:7.1f}  {row['name']}{flag}  [{row['n_games']}j]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
