"""descanso — M6.4 (candidato C1): diferencial de DESCANSO intra-liga, PIT.

Prior (viabilidade 2026-06-28): morto p/ seleções (corr 0,0005 — calendário simétrico),
candidato REAL p/ clubes (qua/dom). LIMITAÇÃO DECLARADA: só o descanso INTRA-LIGA —
Libertadores/Copa do Brasil/estaduais não estão na fonte (atenua o sinal; se um dia
houver calendário externo grátis, re-testar é ângulo novo).

    rest(T, jogo) = dias desde o jogo ANTERIOR do time NA LIGA (PIT; 1º da temporada
                    ou estreia -> neutro). clip em [2, 8] (acima de 8 = descansado normal)
    diff          = clip(rest_home) − clip(rest_away)          ∈ [−6, +6] dias
    dr'           = dr_adj + β·diff        β em Elo/dia, grade {2,4,6,8} na era de
                                           calibração; era de validação decide (gate)

Gate: ΔBrier 1X2 IC>0 + guarda gols + kill-switch corr(β·diff, dr_adj) < 0,95.
Uso:  python -m scb.descanso [--league BRA] [--fast]
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np

from . import backtest_harness as bh
from . import db
from .ingest import DEFAULT_DB
from .mando_rolling import _probs

BETA_GRID = [2.0, 4.0, 6.0, 8.0]
CLIP_LO, CLIP_HI = 2.0, 8.0
NEUTRO = 6.0                      # sem jogo anterior na temporada -> descanso neutro


def rest_series(rows) -> np.ndarray:
    """diff de descanso por jogo (PIT: só jogos anteriores). rows ordenadas por data."""
    last: dict = {}
    out = np.zeros(len(rows))
    for i, r in enumerate(rows):
        d = r["d"]
        rh = d - last.get((r["season"], r["h"]), None) if (r["season"], r["h"]) in last else None
        ra = d - last.get((r["season"], r["a"]), None) if (r["season"], r["a"]) in last else None
        ch = min(max(rh, CLIP_LO), CLIP_HI) if rh is not None else NEUTRO
        ca = min(max(ra, CLIP_LO), CLIP_HI) if ra is not None else NEUTRO
        out[i] = ch - ca
        last[(r["season"], r["h"])] = d
        last[(r["season"], r["a"])] = d
    return out


def _serie(conn, league: str):
    return conn.execute(
        """SELECT m.match_id, julianday(m.date) d, m.season,
                  m.home_team_id h, m.away_team_id a,
                  m.home_score hs, m.away_score aws, mf.dr_adj, mf.sigma_dr
           FROM matches m JOIN match_features mf USING (match_id)
           WHERE m.league=? ORDER BY m.date, m.match_id""", (league,)).fetchall()


def gate(conn, league: str, burn_in: int = 2, n_strata: int = 100, B: int = 10_000) -> dict:
    rows = _serie(conn, league)
    diff = rest_series(rows)
    season = np.array([r["season"] for r in rows])
    seasons = sorted(set(season.tolist()))
    test = seasons[burn_in:]
    meio = max(1, len(test) // 2)
    m_cal = np.isin(season, test[:meio])
    m_val = np.isin(season, test[meio:])
    print(f"\n== {league} — descanso intra-liga (|diff|>0 em "
          f"{(diff != 0).mean():.0%} dos jogos; média |diff| {np.abs(diff).mean():.2f}d) ==")
    zero = np.zeros(len(rows))
    P0c, Yc, *_ = _probs(conn, league, rows, m_cal, zero, n_strata)
    melhor_b, melhor = None, -1e9
    for b in BETA_GRID:
        P1c, _, *_ = _probs(conn, league, rows, m_cal, b * diff, n_strata)
        ganho = (bh.brier(P0c, Yc) - bh.brier(P1c, Yc)).mean()
        if ganho > melhor:
            melhor, melhor_b = ganho, b
    beta = melhor_b
    P0, Y, OU0, BT0, yo, yb = _probs(conn, league, rows, m_val, zero, n_strata)
    P1, _, OU1, BT1, _, _ = _probs(conn, league, rows, m_val, beta * diff, n_strata)
    d1x2 = bh.brier(P0, Y) - bh.brier(P1, Y)
    lo, hi = bh.boot_ci(d1x2, B=B)
    d_gols = ((OU0 - yo) ** 2 + (BT0 - yb) ** 2) - ((OU1 - yo) ** 2 + (BT1 - yb) ** 2)
    glo, ghi = bh.boot_ci(d_gols, B=B)
    drv = np.array([r["dr_adj"] for i, r in enumerate(rows) if m_val[i]])
    dv = (beta * diff)[m_val]
    corr = float(np.corrcoef(dv, drv)[0, 1]) if dv.std() > 0 else 0.0
    passa = lo > 0 and ghi > 0 and abs(corr) < 0.95
    print(f"  β* = {beta:.0f} Elo/dia (calib) · shift médio |β·diff| validação: "
          f"{np.abs(dv).mean():.1f} Elo")
    print(f"  1X2 : Δ {d1x2.mean():+.5f} IC[{lo:+.5f},{hi:+.5f}] "
          f"-> {'PASSA ✅' if lo > 0 else 'não passa'}")
    print(f"  gols: Δ {d_gols.mean():+.5f} IC[{glo:+.5f},{ghi:+.5f}] "
          f"({'ok' if ghi > 0 else 'REGRIDE ❌'}) · kill-switch corr {corr:+.3f}")
    print(f"  Veredito: {'PASSOU — adoção é decisão separada (D-NN)' if passa else 'rejeitar (D-NN com números)'}")
    return {"league": league, "beta": beta, "delta_1x2": float(d1x2.mean()), "ic": [lo, hi],
            "delta_gols": float(d_gols.mean()), "ic_gols": [glo, ghi], "corr": corr,
            "n_valid": int(len(Y)), "passa": bool(passa)}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="M6.4 (C1): gate do descanso diferencial intra-liga.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--league", action="append")
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print("[erro] rode o pipeline antes.")
        return 1
    ns, B = (60, 2000) if args.fast else (100, 10_000)
    with db.session(args.db) as conn:
        leagues = args.league or [r[0] for r in conn.execute(
            "SELECT DISTINCT league FROM matches ORDER BY league")]
        for lg in leagues:
            gate(conn, lg, n_strata=ns, B=B)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
