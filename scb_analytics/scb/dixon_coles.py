"""dixon_coles — M6.5 (candidato C2): correção τ(ρ) dos placares baixos, re-teste em liga.

Rejeitado em seleções (D-39 SCM: ρ=−0,06 piorava BTTS); liga de clubes é o habitat
ORIGINAL do DC (Dixon & Coles 1997, liga inglesa) — re-teste exigido pela D-05.

    τ: M[0,0]·(1−λa·λb·ρ) · M[0,1]·(1+λa·ρ) · M[1,0]·(1+λb·ρ) · M[1,1]·(1−ρ)
    matriz renormalizada; ρ<0 sobe 0-0/1-1 (dependência de placar baixo). ρ=0 ≡ baseline.

Gate (canal que o DC alega consertar): ΔBrier de BTTS + over2.5 + EMPATE-binário
(da matriz Poisson) na era de validação, ρ escolhido na era de calibração.
λ vêm das `predictions` armazenadas (PIT). Se adotado, o re-blend do 1X2 do
ensemble exigiria um SEGUNDO gate — declarado.

Uso:  python -m scb.dixon_coles [--league BRA]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Optional

import numpy as np

from . import backtest_harness as bh
from . import config, db
from .ingest import DEFAULT_DB

RHO_GRID = [-0.15, -0.10, -0.05, 0.0, 0.05]
KMAX = 10


def dc_reads(la: float, lb: float, rho: float, kmax: int = KMAX) -> dict:
    """P(E)-Poisson, over2.5 e BTTS da matriz com correção τ(ρ), renormalizada."""
    pa = [math.exp(-la)]
    for k in range(1, kmax + 1):
        pa.append(pa[-1] * la / k)
    pb = [math.exp(-lb)]
    for k in range(1, kmax + 1):
        pb.append(pb[-1] * lb / k)
    M = np.outer(pa, pb)
    M[0, 0] *= max(0.0, 1.0 - la * lb * rho)
    M[0, 1] *= 1.0 + la * rho
    M[1, 0] *= 1.0 + lb * rho
    M[1, 1] *= 1.0 - rho
    M /= M.sum()
    pe = float(np.trace(M))
    over = float(sum(M[i, j] for i in range(kmax + 1) for j in range(kmax + 1) if i + j >= 3))
    btts = float(1.0 - M[0, :].sum() - M[:, 0].sum() + M[0, 0])
    return {"pe": pe, "over25": over, "btts": btts}


def _serie(conn, league: str):
    rows = conn.execute(
        """SELECT m.season, m.home_score hs, m.away_score aws,
                  p.lambda_a, p.lambda_b, mf.dr_adj
           FROM matches m JOIN match_features mf USING (match_id)
           JOIN predictions p ON p.match_id = m.match_id AND p.versao_modelo = ?
           WHERE m.league=? ORDER BY m.date, m.match_id""",
        (config.MODEL_VERSION, league)).fetchall()
    return rows


def _canais(rows, mask, rho):
    PE, OU, BT, ye, yo, yb = [], [], [], [], [], []
    for i, r in enumerate(rows):
        if not mask[i]:
            continue
        d = dc_reads(r["lambda_a"], r["lambda_b"], rho)
        PE.append(d["pe"]); OU.append(d["over25"]); BT.append(d["btts"])
        ye.append(1.0 if r["hs"] == r["aws"] else 0.0)
        yo.append(1.0 if r["hs"] + r["aws"] >= 3 else 0.0)
        yb.append(1.0 if r["hs"] > 0 and r["aws"] > 0 else 0.0)
    A = lambda x: np.asarray(x, dtype=float)
    return A(PE), A(OU), A(BT), A(ye), A(yo), A(yb)


def gate(conn, league: str, burn_in: int = 2, B: int = 10_000) -> dict:
    rows = _serie(conn, league)
    season = np.array([r["season"] for r in rows])
    seasons = sorted(set(season.tolist()))
    test = seasons[burn_in:]
    meio = max(1, len(test) // 2)
    m_cal = np.isin(season, test[:meio])
    m_val = np.isin(season, test[meio:])
    melhor_r, melhor = 0.0, -1e9
    base_cal = _canais(rows, m_cal, 0.0)
    for rho in RHO_GRID:
        if rho == 0.0:
            continue
        c = _canais(rows, m_cal, rho)
        ganho = sum(((base_cal[k] - base_cal[k + 3]) ** 2
                     - (c[k] - c[k + 3]) ** 2).mean() for k in range(3))
        if ganho > melhor:
            melhor, melhor_r = ganho, rho
    rho = melhor_r
    b = _canais(rows, m_val, 0.0)
    c = _canais(rows, m_val, rho)
    nomes = ["empate(Poisson)", "over2.5", "BTTS"]
    print(f"\n== {league} — Dixon-Coles (ρ*={rho:+.2f} na calibração; validação "
          f"n={int(m_val.sum())}) ==")
    deltas, passa_algum, regride = {}, False, False
    for k, nome in enumerate(nomes):
        dl = (b[k] - b[k + 3]) ** 2 - (c[k] - c[k + 3]) ** 2
        lo, hi = bh.boot_ci(dl, B=B)
        deltas[nome] = {"delta": float(dl.mean()), "ic": [lo, hi]}
        stat = "PASSA ✅" if lo > 0 else ("REGRIDE ❌" if hi < 0 else "IC cruza")
        passa_algum |= lo > 0
        regride |= hi < 0
        print(f"  {nome:16s}: Δ {dl.mean():+.5f} IC[{lo:+.5f},{hi:+.5f}] -> {stat}")
    passa = passa_algum and not regride
    print(f"  Veredito: {'PASSOU no canal de gols — re-blend do 1X2 = 2º gate (D-NN)' if passa else 'rejeitar (D-NN com números)'}")
    return {"league": league, "rho": rho, "canais": deltas,
            "n_valid": int(m_val.sum()), "passa": bool(passa)}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="M6.5 (C2): gate do Dixon-Coles em liga.")
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
