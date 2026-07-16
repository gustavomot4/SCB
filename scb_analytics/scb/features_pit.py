"""features_pit: features POINT-IN-TIME por jogo (só dados com data < t) — port do SCM.

Consome `match_ratings` (elo_engine) + `matches`; grava `match_features`.
**Portão do módulo (M3.2): teste ANTI LOOK-AHEAD** — a feature de um jogo não muda
quando jogos FUTUROS entram na base.

Adaptações de LIGA (contrato SCB v1.0 §1/§2):
  - recência da forma por JOGO (base^k, k=0 é o mais recente) em vez de por mês
    [a calibrar M6] — calendário de clube é denso (2 jogos/semana);
  - sem peso de amistoso (liga é uma competição só; a fonte nem traz `tournament`);
  - sem confederação (D-06) e sem hook Glicko (rejeitado no SCM; re-propor só via
    fila do portão com ângulo novo — D-05);
  - σ_ajuste = c·desvio_forma (descanso/viagem são candidatos C1/C4 — entram AQUI
    quando/se passarem o portão, sem mudar a forma da RSS).

Fórmulas herdadas intactas: residual = pontuação_real − we (we já embute Elo+mando
→ ajuste a adversário); form = clamp(±cap, scale·média_ponderada); vol_mult (D-28);
σ_dr = RSS(σ_R·vol, σ_ajuste).
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import db
from .elo_engine import EloParams, sigma_r
from .ingest import DEFAULT_DB


@dataclass(frozen=True)
class FeatureParams:
    form_window: int = 10        # últimas N partidas
    form_scale: float = 60.0     # residual[-1,1] -> Elo          [a calibrar M6]
    form_cap: float = 30.0       # cap ±30 Elo (contrato §1)
    recency_base: float = 0.9    # peso = base^k (k por JOGO)     [a calibrar M6]
    sigma_ajuste_c: float = 80.0 # σ_ajuste = c·desvio_forma      [a calibrar M6]


def vol_mult(desvio: float, n_form: int = 99, ref: float = 0.35, min_n: int = 5) -> float:
    """Multiplicador de σ_R pela (in)consistência recente (D-28 SCM).

    Errático (desvio alto) → σ_R maior; consistente → menor; ~1.0 em desvio≈ref;
    clamp [0.6, 1.6]. Com pouca forma (n<min_n) retorna 1.0: desvio≈0 ali é
    'sem informação', não 'consistente'.
    """
    if n_form < min_n:
        return 1.0
    return max(0.6, min(1.6, 0.4 + 0.6 * desvio / ref))


def team_form(conn, team_id: int, before_date: str, p: FeatureParams = FeatureParams()):
    """(form_ΔE, desvio_forma, n) usando SÓ jogos com date < before_date (PIT).

    Residual por jogo = pontuação real − we (ajustado a adversário e mando, pois o
    we vem do match_ratings). Peso = recency_base^k, k = idade em JOGOS (0 = último).
    """
    rows = conn.execute(
        """SELECT m.date, m.home_team_id, m.home_score, m.away_score, mr.we_home
           FROM matches m JOIN match_ratings mr USING (match_id)
           WHERE (m.home_team_id = ? OR m.away_team_id = ?) AND m.date < ?
           ORDER BY m.date DESC, m.match_id DESC LIMIT ?""",
        (team_id, team_id, before_date, p.form_window),
    ).fetchall()
    if not rows:
        return 0.0, 0.0, 0
    resid, wts = [], []
    for k, r in enumerate(rows):                     # k=0 é o jogo mais recente
        gd = r["home_score"] - r["away_score"]
        if r["home_team_id"] == team_id:
            actual = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
            exp = r["we_home"]
        else:
            actual = 1.0 if gd < 0 else (0.5 if gd == 0 else 0.0)
            exp = 1.0 - r["we_home"]
        resid.append(actual - exp)
        wts.append(p.recency_base ** k)
    sw = sum(wts)
    wmean = sum(x * w for x, w in zip(resid, wts)) / sw
    var = sum(w * (x - wmean) ** 2 for x, w in zip(resid, wts)) / sw
    form = max(-p.form_cap, min(p.form_cap, p.form_scale * wmean))
    return form, math.sqrt(var), len(rows)


def run(conn, params: FeatureParams = FeatureParams(),
        elo_params: EloParams = EloParams(), incremental: bool = False) -> dict:
    """Monta match_features (todas as ligas). Idempotente. Exige elo_engine antes.

    incremental=True: só jogos ainda sem feature — correto pela invariância PIT
    (feature de jogo antigo não muda com jogo novo; é o que o teste anti look-ahead
    prova). Após CORREÇÃO de jogo antigo ou mudança de código: rebuild completo.
    """
    db.init_schema(conn)
    if conn.execute("SELECT COUNT(*) FROM match_ratings").fetchone()[0] == 0:
        raise RuntimeError("match_ratings vazio — rode elo_engine.run primeiro.")
    if incremental:
        done = {r[0] for r in conn.execute("SELECT match_id FROM match_features")}
    else:
        conn.execute("DELETE FROM match_features")
        done = set()
    rows = conn.execute(
        """SELECT m.match_id, m.date, m.home_team_id, m.away_team_id,
                  mr.dr AS dr_elo, mr.home_n_pre, mr.away_n_pre
           FROM matches m JOIN match_ratings mr USING (match_id)
           ORDER BY m.date, m.match_id"""
    ).fetchall()
    n = 0
    for r in rows:
        if r["match_id"] in done:
            continue
        fh, dh, nh_f = team_form(conn, r["home_team_id"], r["date"], params)
        fa, da, na_f = team_form(conn, r["away_team_id"], r["date"], params)
        sr_h = sigma_r(r["home_n_pre"], elo_params) * vol_mult(dh, nh_f)
        sr_a = sigma_r(r["away_n_pre"], elo_params) * vol_mult(da, na_f)
        sa_h = params.sigma_ajuste_c * dh
        sa_a = params.sigma_ajuste_c * da
        dr_adj = r["dr_elo"] + fh - fa               # produção = backtest (D-34 SCM)
        sigma_dr = math.sqrt(sr_h ** 2 + sr_a ** 2 + sa_h ** 2 + sa_a ** 2)
        conn.execute(
            """INSERT OR REPLACE INTO match_features
               (match_id, dr_elo, form_home, form_away, dr_adj,
                sigma_r_home, sigma_r_away, sigma_ajuste_home, sigma_ajuste_away,
                sigma_dr, n_home_pre, n_away_pre)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["match_id"], r["dr_elo"], fh, fa, dr_adj, sr_h, sr_a, sa_h, sa_a,
             sigma_dr, r["home_n_pre"], r["away_n_pre"]),
        )
        n += 1
    conn.commit()
    return {"features": n}


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Monta features point-in-time por jogo.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--incremental", action="store_true",
                   help="só jogos novos (após correção de jogo antigo, rode SEM esta flag)")
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] SQLite não encontrado: {args.db}. Rode ingest + elo_engine antes.")
        return 1
    with db.session(args.db) as conn:
        stats = run(conn, incremental=args.incremental)
        print(f"features montadas: {stats['features']} jogos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
