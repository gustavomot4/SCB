"""season_rho — M6.6 (candidato C5): regressão do Elo à média na VIRADA de temporada.

Contrato §3.4: churn de elenco brasileiro é dos maiores do mundo -> R←(1−ρ)R+ρ·1500
na 1ª aparição do clube em temporada nova (hook já em `elo_engine`, OFF). ÚNICO
candidato que muda a CONSTRUÇÃO do rating -> cada ρ exige rebuild (elo+features+curvas).

Gate: ρ ∈ {0.15, 0.30} vs baseline ρ=0; escolha na era de calibração; validação
decide (ΔBrier 1X2 pareado IC>0 + guarda gols). Efeito esperado concentrado no
INÍCIO de temporada — reportado também no recorte "1ºs 100 jogos/temporada".

Uso:  python -m scb.season_rho          # roda a sequência inteira (demorado: ~2 min)
      python -m scb.season_rho --rho 0.15 --save x.npz   # uma etapa (uso interno)
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np

from . import backtest_harness as bh
from . import config, db, draw_curve, elo_engine, features_pit, predictor
from .calibrate import collect_probs
from .elo_engine import EloParams
from .ingest import DEFAULT_DB

RHO_GRID = [0.15, 0.30]


def eval_rho(conn, rho: float, n_strata: int = 60, burn_in: int = 2) -> dict:
    """Rebuild com ρ e coleta Brier por jogo nas eras (calib/valid) das 2 ligas."""
    elo_engine.run(conn, EloParams(season_rho=rho))
    features_pit.run(conn)
    out = {}
    for lg in [r[0] for r in conn.execute("SELECT DISTINCT league FROM matches ORDER BY league")]:
        seasons = [r[0] for r in conn.execute(
            "SELECT DISTINCT season FROM matches WHERE league=? ORDER BY season", (lg,))]
        test = seasons[burn_in:]
        meio = max(1, len(test) // 2)
        for era, ss in (("cal", test[:meio]), ("val", test[meio:])):
            P, Y, OU, BT, yo, yb = collect_probs(conn, lg, ss, 0.0, 0.0, n_strata)
            out[f"{lg}_{era}_b"] = bh.brier(P, Y)
            out[f"{lg}_{era}_g"] = (OU - yo) ** 2 + (BT - yb) ** 2
    return out


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="M6.6 (C5): gate da regressão de temporada.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--rho", type=float, default=None, help="roda SÓ este ρ e salva em --save")
    ap.add_argument("--save", default=None)
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print("[erro] rode o pipeline antes.")
        return 1
    ns = 60 if args.fast else 100
    with db.session(args.db) as conn:
        if args.rho is not None:                       # etapa única (paralelizável)
            r = eval_rho(conn, args.rho, n_strata=ns)
            np.savez(args.save or f"rho_{args.rho}.npz", **r)
            print(f"ρ={args.rho}: salvo ({args.save})")
            return 0
        res = {rho: eval_rho(conn, rho, n_strata=ns) for rho in [0.0] + RHO_GRID}
        elo_engine.run(conn)                           # restaura ρ=0 (baseline oficial)
        features_pit.run(conn)
        _verdict(res)
    return 0


def _verdict(res: dict, B: int = 10_000) -> None:
    base = res[0.0]
    for lg in sorted({k.split("_")[0] for k in base}):
        melhor_r, melhor = None, -1e9
        for rho in RHO_GRID:
            g = (base[f"{lg}_cal_b"] - res[rho][f"{lg}_cal_b"]).mean()
            if g > melhor:
                melhor, melhor_r = g, rho
        d = base[f"{lg}_val_b"] - res[melhor_r][f"{lg}_val_b"]
        lo, hi = bh.boot_ci(d, B=B)
        dg = base[f"{lg}_val_g"] - res[melhor_r][f"{lg}_val_g"]
        glo, ghi = bh.boot_ci(dg, B=B)
        passa = lo > 0 and ghi > 0
        print(f"\n== {lg} — regressão de temporada (ρ*={melhor_r} na calibração; "
              f"validação n={len(d)}) ==")
        print(f"  1X2 : Δ {d.mean():+.5f} IC[{lo:+.5f},{hi:+.5f}] "
              f"-> {'PASSA ✅' if lo > 0 else 'não passa'}")
        print(f"  gols: Δ {dg.mean():+.5f} IC[{glo:+.5f},{ghi:+.5f}] "
              f"({'ok' if ghi > 0 else 'REGRIDE ❌'})")
        print(f"  Veredito: {'PASSOU — adoção via config.SEASON_RHO + bump (D-NN)' if passa else 'rejeitar (D-NN com números)'}")


if __name__ == "__main__":
    raise SystemExit(main())
