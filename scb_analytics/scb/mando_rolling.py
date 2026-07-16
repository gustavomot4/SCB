"""mando_rolling — M6.3: correção PIT do MANDO por janela móvel (ângulo novo da D-19).

O H estático morreu no portão (D-19) porque o mando é não-estacionário (caiu pós-COVID
— evidência E2 do contrato). Aqui o desvio vem do dado recente da PRÓPRIA liga:

    ā(d)  = pontuação média REAL do mandante em [d−W, d)      (1/0,5/0; PIT, exclui o dia)
    w̄(d)  = expectativa média do modelo (we_home) na mesma janela
    δ(d)  = elo_inv(ā) − elo_inv(w̄)      onde elo_inv(p) = −400·log10(1/p − 1)
    dr'   = dr_adj + δ(d)                 (clip |δ| ≤ 60; δ=0 se n<min_n)

Zero parâmetro além de W (grade {2,5,10} anos; escolhido na era de calibração;
era de validação decide). Gate: ΔBrier 1X2 pareado IC>0 + guarda gols não-regride
+ kill-switch corr(δ, dr_adj) < 0,95. Se passar: adoção (wiring + bump) é decisão
separada, registrada em D-NN — como manda o método.

Uso:  python -m scb.mando_rolling [--league BRA] [--fast]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Optional

import numpy as np

from . import backtest_harness as bh
from . import config, db, draw_curve, predictor
from .ingest import DEFAULT_DB

W_GRID = [730.0, 1825.0, 3650.0]
MIN_N = 200
CAP = 60.0


def elo_inv(p: float) -> float:
    p = min(max(p, 0.05), 0.95)
    return -400.0 * math.log10(1.0 / p - 1.0)


def delta_series(d: np.ndarray, pts_home: np.ndarray, we_home: np.ndarray,
                 W: float, min_n: int = MIN_N) -> np.ndarray:
    """δ(d_i) PIT: inversão Elo da (pontuação real − esperada) do mandante na janela."""
    cs_a = np.concatenate([[0.0], np.cumsum(pts_home)])
    cs_w = np.concatenate([[0.0], np.cumsum(we_home)])
    hi = np.searchsorted(d, d, side="left")
    lo = np.searchsorted(d, d - W, side="left")
    n = np.maximum(hi - lo, 1)
    a_bar = (cs_a[hi] - cs_a[lo]) / n
    w_bar = (cs_w[hi] - cs_w[lo]) / n
    out = np.array([elo_inv(a) - elo_inv(w) for a, w in zip(a_bar, w_bar)])
    out = np.clip(out, -CAP, CAP)
    out[(hi - lo) < min_n] = 0.0
    return out


def _serie(conn, league: str):
    rows = conn.execute(
        """SELECT julianday(m.date) d, m.season, m.home_score hs, m.away_score aws,
                  mf.dr_adj, mf.sigma_dr, mr.we_home
           FROM matches m JOIN match_features mf USING (match_id)
           JOIN match_ratings mr USING (match_id)
           WHERE m.league=? ORDER BY m.date, m.match_id""", (league,)).fetchall()
    d = np.array([r["d"] for r in rows])
    season = np.array([r["season"] for r in rows])
    pts = np.array([1.0 if r["hs"] > r["aws"] else (0.5 if r["hs"] == r["aws"] else 0.0)
                    for r in rows])
    we = np.array([r["we_home"] for r in rows])
    return rows, d, season, pts, we


def _probs(conn, league: str, rows, mask, delta, n_strata: int):
    """Previsões walk-forward (curva por fold) com dr_adj + δ, só nos jogos do mask."""
    P, Y, OU, BT, yo, yb = [], [], [], [], [], []
    cache = {}
    for i, r in enumerate(rows):
        if not mask[i]:
            continue
        S = r["season"]
        if S not in cache:
            curve = draw_curve.build(conn, league, max_season=S - 1)
            cache[S] = predictor.PredictParams(t_base=config.t_base_for(league),
                                               n_strata=n_strata, curve=curve)
        o = predictor.predict(r["dr_adj"] + delta[i], r["sigma_dr"], cache[S])
        P.append((o["p_v"], o["p_e"], o["p_d"]))
        OU.append(o["p_over25"]); BT.append(o["p_btts"])
        Y.append(0 if r["hs"] > r["aws"] else (1 if r["hs"] == r["aws"] else 2))
        yo.append(1.0 if r["hs"] + r["aws"] >= 3 else 0.0)
        yb.append(1.0 if r["hs"] > 0 and r["aws"] > 0 else 0.0)
    A = lambda x: np.asarray(x, dtype=float)
    return A(P), np.asarray(Y, int), A(OU), A(BT), A(yo), A(yb)


def gate(conn, league: str, burn_in: int = 2, n_strata: int = 100, B: int = 10_000) -> dict:
    rows, d, season, pts, we = _serie(conn, league)
    seasons = sorted(set(season.tolist()))
    test = seasons[burn_in:]
    meio = max(1, len(test) // 2)
    m_cal = np.isin(season, test[:meio])
    m_val = np.isin(season, test[meio:])
    zero = np.zeros(len(d))
    # grid de W na ERA DE CALIBRAÇÃO
    P0c, Yc, *_ = _probs(conn, league, rows, m_cal, zero, n_strata)
    melhor_w, melhor = None, -1e9
    for W in W_GRID:
        delta = delta_series(d, pts, we, W)
        P1c, _, *_ = _probs(conn, league, rows, m_cal, delta, n_strata)
        ganho = (bh.brier(P0c, Yc) - bh.brier(P1c, Yc)).mean()
        if ganho > melhor:
            melhor, melhor_w = ganho, W
    W = melhor_w
    delta = delta_series(d, pts, we, W)
    # GATE na ERA DE VALIDAÇÃO
    P0, Y, OU0, BT0, yo, yb = _probs(conn, league, rows, m_val, zero, n_strata)
    P1, _, OU1, BT1, _, _ = _probs(conn, league, rows, m_val, delta, n_strata)
    d1x2 = bh.brier(P0, Y) - bh.brier(P1, Y)
    lo, hi = bh.boot_ci(d1x2, B=B)
    d_gols = ((OU0 - yo) ** 2 + (BT0 - yb) ** 2) - ((OU1 - yo) ** 2 + (BT1 - yb) ** 2)
    glo, ghi = bh.boot_ci(d_gols, B=B)
    dv = delta[m_val]
    corr = float(np.corrcoef(dv, np.array([r["dr_adj"] for i, r in enumerate(rows)
                                           if m_val[i]]))[0, 1]) if dv.std() > 0 else 0.0
    passa = lo > 0 and ghi > 0 and abs(corr) < 0.95
    print(f"\n== {league} — mando rolling (W*={int(W // 365)}a; validação n={len(Y)}) ==")
    print(f"  δ vigente: {delta[-1]:+.1f} Elo · δ médio na validação: {dv.mean():+.1f} "
          f"[{dv.min():+.1f},{dv.max():+.1f}]")
    print(f"  1X2 : Δ {d1x2.mean():+.5f} IC[{lo:+.5f},{hi:+.5f}] "
          f"-> {'PASSA ✅' if lo > 0 else 'não passa'}")
    print(f"  gols: Δ {d_gols.mean():+.5f} IC[{glo:+.5f},{ghi:+.5f}] "
          f"({'ok' if ghi > 0 else 'REGRIDE ❌'}) · kill-switch corr {corr:+.3f}")
    print(f"  Veredito: {'PASSOU — adoção (wiring+bump) é decisão separada, D-NN' if passa else 'rejeitar (D-NN com números)'}")
    return {"league": league, "W": W, "delta_1x2": float(d1x2.mean()), "ic": [lo, hi],
            "delta_gols": float(d_gols.mean()), "ic_gols": [glo, ghi], "corr": corr,
            "delta_vigente": float(delta[-1]), "n_valid": int(len(Y)), "passa": bool(passa)}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="M6.3: gate do mando por janela móvel PIT.")
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
