"""calibrate — M6.1: grid de H (camada de previsão) e T_base por liga, com gate honesto.

Método (contrato §5; insumos medidos: we_home 0,619 vs real 0,595 → H alto;
over sobreprevisto +3-4pp → T_base alto):
  - H entra aqui como DESLOCAMENTO na previsão: dr_pred = dr_adj + (H_pred − H_LIGA).
    O H de CONSTRUÇÃO do Elo fica em 100 (D-47 SCM: dentro do ruído) — zero rebuild.
  - split temporal: ERA DE CALIBRAÇÃO = primeira ~metade das temporadas de teste
    (grid escolhe H*, T_base*); ERA DE VALIDAÇÃO = restante (gate: ΔBrier 1X2 pareado
    vs valores atuais, IC bootstrap B=10k; guarda: Brier over2.5+BTTS não regride).
  - adoção: IC>0 na validação → atualizar config (H_LIGA/T_BASE_LIGA) + bump
    MODEL_VERSION → rebuild predictions. Rejeição também é resultado (D-NN).

Uso:  python -m scb.calibrate --league BRA [--fast]
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np

from . import backtest_harness as bh
from . import config, db, draw_curve, predictor
from .ingest import DEFAULT_DB

H_GRID = [40.0, 60.0, 80.0, 100.0, 120.0]        # H_pred candidatos
TB_GRID = [-0.20, -0.10, 0.0, +0.10]             # deslocamento sobre T_BASE_LIGA


def collect_probs(conn, league: str, seasons: list, dr_shift: float, tb_shift: float,
                  n_strata: int = 100):
    """Previsões walk-forward nas temporadas dadas com (dr_shift, tb_shift). PIT por fold."""
    P, Y, OU, BT, y_ou, y_bt = [], [], [], [], [], []
    for S in seasons:
        curve = draw_curve.build(conn, league, max_season=S - 1)
        p = predictor.PredictParams(t_base=config.t_base_for(league) + tb_shift,
                                    n_strata=n_strata, curve=curve)
        rows = conn.execute(
            """SELECT m.home_score hs, m.away_score aws, mf.dr_adj, mf.sigma_dr
               FROM matches m JOIN match_features mf USING (match_id)
               WHERE m.league=? AND m.season=?""", (league, S)).fetchall()
        for r in rows:
            o = predictor.predict(r["dr_adj"] + dr_shift, r["sigma_dr"], p)
            P.append((o["p_v"], o["p_e"], o["p_d"]))
            OU.append(o["p_over25"]); BT.append(o["p_btts"])
            Y.append(0 if r["hs"] > r["aws"] else (1 if r["hs"] == r["aws"] else 2))
            y_ou.append(1.0 if r["hs"] + r["aws"] >= 3 else 0.0)
            y_bt.append(1.0 if r["hs"] > 0 and r["aws"] > 0 else 0.0)
    A = lambda x: np.asarray(x, dtype=float)
    return A(P), np.asarray(Y, int), A(OU), A(BT), A(y_ou), A(y_bt)


def run(conn, league: str, burn_in: int = 2, n_strata: int = 100, B: int = 10_000) -> dict:
    seasons = [r[0] for r in conn.execute(
        "SELECT DISTINCT season FROM matches WHERE league=? ORDER BY season", (league,))]
    test = seasons[burn_in:]
    meio = max(1, len(test) // 2)
    calib, valid = test[:meio], test[meio:]
    print(f"\n== {league}: calib {calib[0]}–{calib[-1]} | validação {valid[0]}–{valid[-1]} ==")
    # 1) grid na ERA DE CALIBRAÇÃO (Brier 1X2 + gols somados — 1 número p/ ordenar)
    melhor, melhor_score = None, 1e9
    for h in H_GRID:
        for tb in TB_GRID:
            P, Y, OU, BT, yo, yb = collect_probs(conn, league, calib,
                                                 h - config.h_for(league), tb, n_strata)
            score = bh.brier(P, Y).mean() + 0.5 * (((OU - yo) ** 2).mean()
                                                   + ((BT - yb) ** 2).mean())
            if score < melhor_score:
                melhor_score, melhor = score, (h, tb)
    h_star, tb_star = melhor
    print(f"  grid (calib): H* = {h_star:.0f}  ·  T_base* = "
          f"{config.t_base_for(league) + tb_star:.2f}  (score {melhor_score:.4f})")
    # 2) GATE na ERA DE VALIDAÇÃO: candidato vs valores ATUAIS, pareado
    P0, Y, OU0, BT0, yo, yb = collect_probs(conn, league, valid, 0.0, 0.0, n_strata)
    P1, _, OU1, BT1, _, _ = collect_probs(conn, league, valid,
                                          h_star - config.h_for(league), tb_star, n_strata)
    d1x2 = bh.brier(P0, Y) - bh.brier(P1, Y)
    lo, hi = bh.boot_ci(d1x2, B=B)
    d_gols = (((OU0 - yo) ** 2 + (BT0 - yb) ** 2) - ((OU1 - yo) ** 2 + (BT1 - yb) ** 2))
    glo, ghi = bh.boot_ci(d_gols, B=B)
    passa = lo > 0 and ghi > 0                     # 1X2 melhora COM IC; gols não regride
    print(f"  gate 1X2 (validação, n={len(Y)}): Δ {d1x2.mean():+.4f} IC[{lo:+.4f},{hi:+.4f}]"
          f" -> {'PASSA ✅' if lo > 0 else 'não passa'}")
    print(f"  guarda gols: Δ {d_gols.mean():+.4f} IC[{glo:+.4f},{ghi:+.4f}]"
          f" -> {'ok' if ghi > 0 else 'REGRIDE ❌'}")
    return {"league": league, "h_star": h_star, "t_base_star": config.t_base_for(league) + tb_star,
            "delta_1x2": float(d1x2.mean()), "ic": [lo, hi],
            "delta_gols": float(d_gols.mean()), "ic_gols": [glo, ghi],
            "n_valid": int(len(Y)), "passa": bool(passa)}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="M6.1: grid H_pred + T_base com gate fora-de-amostra.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--league", action="append")
    ap.add_argument("--fast", action="store_true", help="estratos=60, B=2000 (exploração)")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print("[erro] rode o pipeline antes.")
        return 1
    ns, B = (60, 2000) if args.fast else (100, 10_000)
    with db.session(args.db) as conn:
        leagues = args.league or [r[0] for r in conn.execute(
            "SELECT DISTINCT league FROM matches ORDER BY league")]
        for lg in leagues:
            r = run(conn, lg, n_strata=ns, B=B)
            if r["passa"]:
                print(f"  ADOTAR: config.H_LIGA['{lg}']={r['h_star']:.0f}, "
                      f"T_BASE_LIGA['{lg}']={r['t_base_star']:.2f} + bump de versão + "
                      f"rebuild (`python -m scb.predictor`) + D-NN no vault")
            else:
                print("  manter valores atuais; registrar D-NN 'rejeitado' com os números")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
