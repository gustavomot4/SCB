"""drift — M6.2 (candidato C3): correção PIT de janela móvel do canal de GOLS.

Família APROVADA no SCM (D-84: over +0,0025 / BTTS +0,0021 IC>0) e indicada aqui pela
REJEIÇÃO da M6.1 (D-19): o nível de gols deriva por ERA (BRA 2,18→2,66) — conserto
estático corrige ao contrário; o certo é a média móvel do resíduo, PIT:

    r(d) = média de (y − p) nos jogos da MESMA LIGA com data em [d−W, d)   (exclui o dia)
    p_ajustado = clip(p + r, 0.01, 0.99)          # só over2.5 e BTTS; 1X2 INTOCADO
    r = 0 se n na janela < min_n (sem taxa inventada)

Zero parâmetro ajustado além de W (escolhido na era de calibração; validação decide).
Resíduos vêm da tabela `predictions` (p_over/p_btts são PIT: λ de dr_adj; a curva de
empate não toca o canal de gols). Kill-switch: corr(r, dr_adj) < 0,95.

Uso:  python -m scb.drift            # gate nas duas ligas; adoção = config.USE_MKT_DRIFT
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np

from . import backtest_harness as bh
from . import config, db
from .ingest import DEFAULT_DB

W_GRID_DIAS = [1825, 3650]          # 5 e 10 anos (grade herdada do SCM)
MIN_N = 300


def _serie(conn, league: str):
    rows = conn.execute(
        """SELECT julianday(m.date) d, m.season, mf.dr_adj,
                  p.p_over25, p.p_btts, m.home_score hs, m.away_score aws
           FROM matches m JOIN match_features mf USING (match_id)
           JOIN predictions p ON p.match_id = m.match_id AND p.versao_modelo = ?
           WHERE m.league=? ORDER BY m.date, m.match_id""",
        (config.MODEL_VERSION, league)).fetchall()
    d = np.array([r["d"] for r in rows])
    season = np.array([r["season"] for r in rows])
    dr = np.array([r["dr_adj"] for r in rows])
    po = np.array([r["p_over25"] for r in rows])
    pb = np.array([r["p_btts"] for r in rows])
    yo = np.array([1.0 if r["hs"] + r["aws"] >= 3 else 0.0 for r in rows])
    yb = np.array([1.0 if r["hs"] > 0 and r["aws"] > 0 else 0.0 for r in rows])
    return d, season, dr, po, pb, yo, yb


def trailing_residual(d: np.ndarray, resid: np.ndarray, W: float, min_n: int = MIN_N):
    """r_i = média PIT do resíduo em [d_i − W, d_i). Vetorizado (cumsum + searchsorted)."""
    cs = np.concatenate([[0.0], np.cumsum(resid)])
    hi = np.searchsorted(d, d, side="left")          # exclui o próprio dia
    lo = np.searchsorted(d, d - W, side="left")
    n = hi - lo
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (cs[hi] - cs[lo]) / np.maximum(n, 1)
    r[n < min_n] = 0.0
    return r


def gate(conn, league: str, burn_in: int = 2, B: int = 10_000) -> dict:
    d, season, dr, po, pb, yo, yb = _serie(conn, league)
    seasons = sorted(set(season.tolist()))
    test = seasons[burn_in:]
    meio = max(1, len(test) // 2)
    calib_s, valid_s = set(test[:meio]), set(test[meio:])
    m_cal = np.isin(season, list(calib_s))
    m_val = np.isin(season, list(valid_s))
    melhor_w, melhor = None, -1e9
    for W in W_GRID_DIAS:                            # W escolhido na ERA DE CALIBRAÇÃO
        ro = trailing_residual(d, yo - po, W)
        rb = trailing_residual(d, yb - pb, W)
        po2 = np.clip(po + ro, 0.01, 0.99)
        pb2 = np.clip(pb + rb, 0.01, 0.99)
        ganho = (((po - yo) ** 2 - (po2 - yo) ** 2)[m_cal].mean()
                 + ((pb - yb) ** 2 - (pb2 - yb) ** 2)[m_cal].mean())
        if ganho > melhor:
            melhor, melhor_w = ganho, W
    W = melhor_w
    ro = trailing_residual(d, yo - po, W)
    rb = trailing_residual(d, yb - pb, W)
    po2 = np.clip(po + ro, 0.01, 0.99)
    pb2 = np.clip(pb + rb, 0.01, 0.99)
    d_over = ((po - yo) ** 2 - (po2 - yo) ** 2)[m_val]
    d_btts = ((pb - yb) ** 2 - (pb2 - yb) ** 2)[m_val]
    lo_o, hi_o = bh.boot_ci(d_over, B=B)
    lo_b, hi_b = bh.boot_ci(d_btts, B=B)
    corr = float(np.corrcoef(ro[m_val], dr[m_val])[0, 1]) if ro[m_val].std() > 0 else 0.0
    passa = lo_o > 0 and lo_b > 0 and abs(corr) < 0.95
    print(f"\n== {league} — drift PIT (W*={W // 365}a; validação n={int(m_val.sum())}) ==")
    print(f"  over2.5: Δ {d_over.mean():+.5f} IC[{lo_o:+.5f},{hi_o:+.5f}] "
          f"-> {'PASSA ✅' if lo_o > 0 else 'não passa'}")
    print(f"  BTTS   : Δ {d_btts.mean():+.5f} IC[{lo_b:+.5f},{hi_b:+.5f}] "
          f"-> {'PASSA ✅' if lo_b > 0 else 'não passa'}")
    print(f"  kill-switch corr(r, dr_adj) = {corr:+.3f} ({'ok' if abs(corr) < 0.95 else 'MATA'}) "
          f"· correção vigente: over {ro[-1]:+.3f} / btts {rb[-1]:+.3f}")
    print(f"  1X2: INTOCADO por construção. Veredito: "
          f"{'ADOTAR (config.USE_MKT_DRIFT=True + D-NN)' if passa else 'rejeitar (D-NN com números)'}")
    return {"league": league, "W": W, "d_over": float(d_over.mean()), "ic_over": [lo_o, hi_o],
            "d_btts": float(d_btts.mean()), "ic_btts": [lo_b, hi_b],
            "corr_dr": corr, "n_valid": int(m_val.sum()), "passa": bool(passa),
            "corr_vigente_over": float(ro[-1]), "corr_vigente_btts": float(rb[-1])}


def correction_now(conn, league: str, W: float = 3650.0):
    """Correção vigente HOJE (p/ o predict_match quando USE_MKT_DRIFT=True)."""
    d, _, _, po, pb, yo, yb = _serie(conn, league)
    ro = trailing_residual(d, yo - po, W)
    rb = trailing_residual(d, yb - pb, W)
    # trailing no fim da série ~ correção p/ um jogo de hoje (inclui o último dia jogado)
    cs_o = np.concatenate([[0.0], np.cumsum(yo - po)])
    cs_b = np.concatenate([[0.0], np.cumsum(yb - pb)])
    lo = np.searchsorted(d, d[-1] + 1 - W, side="left")
    n = len(d) - lo
    if n < MIN_N:
        return 0.0, 0.0
    return float((cs_o[-1] - cs_o[lo]) / n), float((cs_b[-1] - cs_b[lo]) / n)


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="M6.2 (C3): gate do drift PIT do canal de gols.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--league", action="append")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print("[erro] rode o pipeline (até o predictor) antes.")
        return 1
    with db.session(args.db) as conn:
        leagues = args.league or [r[0] for r in conn.execute(
            "SELECT DISTINCT league FROM matches ORDER BY league")]
        for lg in leagues:
            gate(conn, lg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
