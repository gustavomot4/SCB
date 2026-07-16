"""simulate_league — Monte Carlo da temporada de PONTOS CORRIDOS (substitui o bracket do SCM).

Para a temporada corrente de uma liga:
  - jogos DISPUTADOS entram como verdade (disciplina D-83/85 SCM: a realidade trava a sim);
  - jogos RESTANTES são DERIVADOS do turno-returno (pares ainda não jogados — a fonte não
    traz calendário futuro; datas não importam: força é estática na sim, como no SCM);
  - placares amostrados da Poisson do modelo (λ do dr atual: Elo + forma + H_liga —
    consistência com o backtest, D-34) com seed FIXA;
  - classificação com desempate PARAMETRIZADO: pontos → vitórias → saldo → gols pró →
    [cartões: LACUNA de dado, pulado — declarado] → sorteio.  **Q-03 [confirmar]: ordem
    CBF vigente; confronto direto (2 clubes) não implementado na V1 — simplificação
    declarada, efeito só em empates exatos raros.**

Saídas por clube: P(título) · P(G4) · P(G6) · P(Z4) · pontos esperados · posição média.
Uso:  python -m scb.simulate_league --league BRA --season 2026 [--sims 5000]
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

from . import config, db, draw_curve, predictor
from .features_pit import team_form
from .ingest import DEFAULT_DB

SEED = 12345


def current_state(conn, league: str, season: int):
    """(tabela dos jogos disputados, elos/formas atuais, pares restantes)."""
    teams = [r[0] for r in conn.execute(
        """SELECT DISTINCT home_team_id FROM matches WHERE league=? AND season=?
           UNION SELECT DISTINCT away_team_id FROM matches WHERE league=? AND season=?""",
        (league, season, league, season))]
    played = conn.execute(
        """SELECT home_team_id h, away_team_id a, home_score hs, away_score aws
           FROM matches WHERE league=? AND season=?""", (league, season)).fetchall()
    played_pairs = {(r["h"], r["a"]) for r in played}
    remaining = [(h, a) for h in teams for a in teams
                 if h != a and (h, a) not in played_pairs]
    elo = {r["team_id"]: r["elo"] for r in conn.execute("SELECT * FROM ratings_current")}
    form = {t: team_form(conn, t, "9999-12-31")[0] for t in teams}
    return teams, played, remaining, elo, form


def _standings_base(teams, played):
    pts = defaultdict(int); wins = defaultdict(int); gd = defaultdict(int); gf = defaultdict(int)
    for r in played:
        h, a, hs, aws = r["h"], r["a"], r["hs"], r["aws"]
        gd[h] += hs - aws; gd[a] += aws - hs; gf[h] += hs; gf[a] += aws
        if hs > aws: pts[h] += 3; wins[h] += 1
        elif hs == aws: pts[h] += 1; pts[a] += 1
        else: pts[a] += 3; wins[a] += 1
    return pts, wins, gd, gf


def run(conn, league: str, season: int, sims: int = 5000, seed: int = SEED,
        params: Optional[predictor.PredictParams] = None) -> dict:
    teams, played, remaining, elo, form = current_state(conn, league, season)
    if not teams:
        raise ValueError(f"sem jogos de {league}/{season} na base")
    curve = draw_curve.load(conn, league) or draw_curve.build(conn, league)
    p = params or predictor.PredictParams(t_base=config.t_base_for(league), curve=curve)
    H = config.h_for(league)
    lam = {}
    for h, a in remaining:                              # λ estático por confronto (como no SCM)
        dr = elo.get(h, 1500.0) - elo.get(a, 1500.0) + form.get(h, 0.0) - form.get(a, 0.0) + H
        lam[(h, a)] = predictor.lambdas(dr, p)
    base = _standings_base(teams, played)
    rng = np.random.default_rng(seed)
    n = len(teams)
    idx = {t: i for i, t in enumerate(teams)}
    titulo = np.zeros(n); g4 = np.zeros(n); g6 = np.zeros(n); z4 = np.zeros(n)
    pos_sum = np.zeros(n); pts_sum = np.zeros(n)
    for _ in range(sims):
        pts = dict(base[0]); wins = dict(base[1]); gd = dict(base[2]); gf = dict(base[3])
        for (h, a), (la, lb) in lam.items():
            hs = rng.poisson(la); aws = rng.poisson(lb)
            gd[h] = gd.get(h, 0) + hs - aws; gd[a] = gd.get(a, 0) + aws - hs
            gf[h] = gf.get(h, 0) + hs; gf[a] = gf.get(a, 0) + aws
            if hs > aws: pts[h] = pts.get(h, 0) + 3; wins[h] = wins.get(h, 0) + 1
            elif hs == aws: pts[h] = pts.get(h, 0) + 1; pts[a] = pts.get(a, 0) + 1
            else: pts[a] = pts.get(a, 0) + 3; wins[a] = wins.get(a, 0) + 1
        ordem = sorted(teams, key=lambda t: (pts.get(t, 0), wins.get(t, 0), gd.get(t, 0),
                                             gf.get(t, 0), rng.random()), reverse=True)
        for rank, t in enumerate(ordem):                # rank 0 = campeão
            i = idx[t]
            pos_sum[i] += rank + 1
            pts_sum[i] += pts.get(t, 0)
            if rank == 0: titulo[i] += 1
            if rank < 4: g4[i] += 1
            if rank < 6: g6[i] += 1
            if rank >= n - 4: z4[i] += 1
    nomes = {r["team_id"]: r["name"] for r in conn.execute("SELECT team_id, name FROM teams")}
    out = []
    for t in teams:
        i = idx[t]
        out.append({"team": nomes[t], "titulo": titulo[i] / sims, "g4": g4[i] / sims,
                    "g6": g6[i] / sims, "z4": z4[i] / sims,
                    "pts_esp": pts_sum[i] / sims, "pos_media": pos_sum[i] / sims})
    out.sort(key=lambda r: -r["pts_esp"])
    return {"league": league, "season": season, "sims": sims, "seed": seed,
            "played": len(played), "remaining": len(remaining), "tabela": out}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Monte Carlo da temporada (pontos corridos).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--league", default="BRA")
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--sims", type=int, default=5000)
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print("[erro] rode o pipeline antes.")
        return 1
    with db.session(args.db) as conn:
        r = run(conn, args.league, args.season, sims=args.sims)
        print(f"{r['league']} {r['season']} — {r['played']} jogados, {r['remaining']} restantes, "
              f"{r['sims']} sims (seed {r['seed']}). Probabilidade, nunca certeza.")
        print(f"{'clube':22s} {'título':>7s} {'G4':>6s} {'G6':>6s} {'Z4':>6s} {'ptsE':>6s} {'posM':>5s}")
        for t in r["tabela"]:
            print(f"{t['team']:22s} {t['titulo']:7.1%} {t['g4']:6.1%} {t['g6']:6.1%} "
                  f"{t['z4']:6.1%} {t['pts_esp']:6.1f} {t['pos_media']:5.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
