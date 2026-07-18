"""predict_match — porta da frente: prever UM confronto com o estado ATUAL.

Consistência produção↔backtest (D-34 SCM): dr = elo_A − elo_B + (forma_A − forma_B) + H_liga
— a MESMA fórmula do features_pit. σ_dr da mesma família (σ_R·vol_mult + c·desvio).

Uso:
    python -m scb.predict_match BRA "Flamengo RJ" "Palmeiras"
    python -m scb.predict_match BRA "Flamengo RJ" "Palmeiras" --odds 2.10 3.30 3.60
"""
from __future__ import annotations

import argparse
import difflib
import math
from pathlib import Path
from typing import Optional

from . import config, db, draw_curve, odds, predictor
from .elo_engine import EloParams, sigma_r
from .features_pit import FeatureParams, team_form, vol_mult
from .ingest import DEFAULT_DB


def _team(conn, name: str):
    row = conn.execute("SELECT team_id, name FROM teams WHERE name=?", (name,)).fetchone()
    if row:
        return row
    known = [r[0] for r in conn.execute("SELECT name FROM teams")]
    sug = difflib.get_close_matches(name, known, n=5, cutoff=0.4)
    raise ValueError(f"time '{name}' não encontrado. Sugestões: {sug}")


def predict_now(conn, league: str, home: str, away: str,
                market: Optional[dict] = None) -> dict:
    h = _team(conn, home); a = _team(conn, away)
    ep, fp = EloParams(), FeatureParams()
    cur = {r["team_id"]: r for r in conn.execute("SELECT * FROM ratings_current")}
    rh, ra = cur[h["team_id"]], cur[a["team_id"]]
    fh, dh, nh = team_form(conn, h["team_id"], "9999-12-31", fp)
    fa, da, na = team_form(conn, a["team_id"], "9999-12-31", fp)
    dr = rh["elo"] - ra["elo"] + (fh - fa) + config.h_for(league)     # produção = backtest
    if config.mando_rolling_for(league):                              # D-26 (mesma fórmula do features)
        from . import mando_rolling
        dr += mando_rolling.delta_today(conn, league, config.MANDO_ROLLING_W)
    sr_h = sigma_r(rh["n_games"], ep) * vol_mult(dh, nh)
    sr_a = sigma_r(ra["n_games"], ep) * vol_mult(da, na)
    sigma_dr = math.sqrt(sr_h ** 2 + sr_a ** 2 + (fp.sigma_ajuste_c * dh) ** 2
                         + (fp.sigma_ajuste_c * da) ** 2)
    curve = draw_curve.load(conn, league) or draw_curve.build(conn, league)
    p = predictor.PredictParams(t_base=config.t_base_for(league), curve=curve)
    out = predictor.predict(dr, sigma_dr, p)
    out.update({"dr": dr, "sigma_dr": sigma_dr, "elo_home": rh["elo"], "elo_away": ra["elo"],
                "form_home": fh, "form_away": fa, "mando": config.h_for(league),
                "versao": config.MODEL_VERSION})
    if market:                                          # blend opcional (peso ≤0,20, D-09)
        mix = odds.blend({"p_v": out["p_v"], "p_e": out["p_e"], "p_d": out["p_d"]}, market)
        out["com_mercado"] = mix
    return out


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Previsão de 1 confronto (estado atual).")
    ap.add_argument("league"); ap.add_argument("home"); ap.add_argument("away")
    ap.add_argument("--odds", nargs=3, type=float, metavar=("CASA", "EMPATE", "FORA"))
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print("[erro] rode o pipeline antes.")
        return 1
    with db.session(args.db) as conn:
        mk = odds.implied_probs(*args.odds) if args.odds else None
        o = predict_now(conn, args.league, args.home, args.away, market=mk)
        print(f"{args.home} x {args.away} [{args.league}] — {o['versao']}")
        print(f"  dr {o['dr']:+.1f} (elo {o['elo_home']:.0f}−{o['elo_away']:.0f} · "
              f"forma {o['form_home']:+.1f}/{o['form_away']:+.1f} · mando +{o['mando']:.0f}) "
              f"· σ_dr {o['sigma_dr']:.0f}")
        print(f"  V {o['p_v']:.1%} · E {o['p_e']:.1%} · D {o['p_d']:.1%}  "
              f"(banda P(V) [{o['band_lo']:.1%},{o['band_hi']:.1%}])")
        print(f"  λ {o['lambda_a']:.2f} x {o['lambda_b']:.2f} · over2.5 {o['p_over25']:.1%} · "
              f"BTTS {o['p_btts']:.1%} · top5 {o['top5']}")
        if mk:
            m = o["com_mercado"]
            print(f"  c/ mercado (20%): V {m['p_v']:.1%} · E {m['p_e']:.1%} · D {m['p_d']:.1%}")
        print("  Probabilidade, nunca certeza.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
