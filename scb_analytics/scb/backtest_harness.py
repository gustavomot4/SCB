"""backtest_harness — O PORTÃO DO BASELINE (M4): walk-forward por temporada + 4 réguas.

Método (contrato SCB v1.0 §5 / D-08):
  - split: para cada temporada de teste S (após burn-in), treino = temporadas < S.
    A CURVA DE EMPATE é reconstruída POR FOLD com `max_season=S-1` (anti-vazamento —
    fecha o caveat N-B do SCM). Elo/forma já são PIT por construção (M3).
  - previsões do MODELO calculadas on-the-fly por fold (predictor.predict com a curva
    do treino) — a tabela `predictions` (curva cheia) é para PRODUÇÃO, não p/ o gate.
  - 4 réguas: UNIFORME (1/3) · TAXA-BASE do treino da liga · ELO-PURO (we + curva do
    treino, sem forma/Poisson/ensemble — D-27 SCM) · MERCADO de-vigged (fechamento,
    fallback D-16; pareado só nos jogos com odds).
  - métricas: Brier forma-soma (máx 2; uniforme=0,667), LogLoss, RPS, ECE (10 bins de
    p_max), cobertura da banda por faixa de P(V).
  - IC 95%: bootstrap PAREADO da ΔBrier (régua − modelo), B=10.000, seed=12345,
    vetorizado (D-15). PASSA = IC não cruza zero.

Constantes do modelo são placeholders fixados ex-ante ([a calibrar M6]) — declarado.
Uso:  python -m scb.backtest_harness [--league BRA] [--burn-in 2] [--fast]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Optional

import numpy as np

from . import config, db, draw_curve, odds, predictor
from .ingest import DEFAULT_DB

SEED = 12345
B_BOOT = 10_000


# ---------------------------------------------------------------- métricas
def brier(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Brier forma-soma por jogo: Σ_k (p_k − 1[y=k])². p: (n,3); y: (n,) em {0,1,2}."""
    onehot = np.eye(3)[y]
    return ((p - onehot) ** 2).sum(axis=1)


def logloss(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1.0))


def rps(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Ranked Probability Score (ordinal V<E<D)."""
    cp = np.cumsum(p, axis=1)[:, :2]
    cy = np.cumsum(np.eye(3)[y], axis=1)[:, :2]
    return ((cp - cy) ** 2).sum(axis=1) / 2.0


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    """Expected Calibration Error do top-pick (aposta mais provável)."""
    conf = p.max(axis=1)
    pick = p.argmax(axis=1)
    hit = (pick == y).astype(float)
    edges = np.linspace(conf.min(), conf.max() + 1e-9, bins + 1)
    out, n = 0.0, len(y)
    for i in range(bins):
        m = (conf >= edges[i]) & (conf < edges[i + 1])
        if m.sum() == 0:
            continue
        out += (m.sum() / n) * abs(hit[m].mean() - conf[m].mean())
    return out


def boot_ci(delta: np.ndarray, B: int = B_BOOT, seed: int = SEED, chunk: int = 1000):
    """IC95 bootstrap da média da ΔBrier pareada (vetorizado, D-15)."""
    rng = np.random.default_rng(seed)
    n = len(delta)
    means = []
    done = 0
    while done < B:
        m = min(chunk, B - done)
        idx = rng.integers(0, n, size=(m, n))
        means.append(delta[idx].mean(axis=1))
        done += m
    means = np.concatenate(means)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def band_coverage(p_v: np.ndarray, lo: np.ndarray, hi: np.ndarray, y: np.ndarray,
                  bins: int = 10):
    """Cobertura por faixa de P(V) (D-30): freq. observada de vitória dentro da banda média."""
    out = []
    edges = np.linspace(0, 1, bins + 1)
    win = (y == 0).astype(float)
    for i in range(bins):
        m = (p_v >= edges[i]) & (p_v < edges[i + 1])
        if m.sum() < 30:
            continue
        obs = win[m].mean()
        out.append({"faixa": f"[{edges[i]:.1f},{edges[i+1]:.1f})", "n": int(m.sum()),
                    "obs": obs, "lo": lo[m].mean(), "hi": hi[m].mean(),
                    "dentro": bool(lo[m].mean() <= obs <= hi[m].mean())})
    return out


# ---------------------------------------------------------------- coleta por fold
def _outcome(hs: int, as_: int) -> int:
    return 0 if hs > as_ else (1 if hs == as_ else 2)


def collect(conn, league: str, burn_in: int = 2, n_strata: Optional[int] = None) -> dict:
    """Roda o walk-forward da liga e devolve arrays pareados (modelo + 4 réguas)."""
    seasons = [r[0] for r in conn.execute(
        "SELECT DISTINCT season FROM matches WHERE league=? ORDER BY season", (league,))]
    test_seasons = seasons[burn_in:]
    P_model, P_elo, P_base, P_mkt, Y = [], [], [], [], []
    LO, HI, OU, BT, y_ou, y_bt, mkt_mask, seas = [], [], [], [], [], [], [], []
    base_p = predictor.PredictParams()
    if n_strata:
        base_p = predictor.PredictParams(n_strata=n_strata)
    for S in test_seasons:
        curve = draw_curve.build(conn, league, max_season=S - 1)      # POR FOLD (anti-leak)
        params = predictor.PredictParams(
            t_base=config.t_base_for(league), n_strata=base_p.n_strata, curve=curve)
        tr = conn.execute(
            """SELECT AVG(home_score>away_score), AVG(home_score=away_score)
               FROM matches WHERE league=? AND season<?""", (league, S)).fetchone()
        base = np.array([tr[0], tr[1], 1.0 - tr[0] - tr[1]])          # taxa-base do TREINO
        rows = conn.execute(
            """SELECT m.match_id, m.home_score hs, m.away_score aws,
                      mf.dr_adj, mf.sigma_dr, mr.dr dr_elo
               FROM matches m JOIN match_features mf USING (match_id)
               JOIN match_ratings mr USING (match_id)
               WHERE m.league=? AND m.season=? ORDER BY m.date, m.match_id""",
            (league, S)).fetchall()
        for r in rows:
            out = predictor.predict(r["dr_adj"], r["sigma_dr"], params)
            P_model.append((out["p_v"], out["p_e"], out["p_d"]))
            e = draw_curve.ved_from_dr(r["dr_elo"], curve, eps=params.draw_eps)
            P_elo.append((e["p_v"], e["p_e"], e["p_d"]))
            P_base.append(base)
            mk = odds.market_read(conn, r["match_id"], "close")
            if mk:
                P_mkt.append((mk["p_v"], mk["p_e"], mk["p_d"]))
                mkt_mask.append(True)
            else:
                P_mkt.append((1 / 3, 1 / 3, 1 / 3))
                mkt_mask.append(False)
            Y.append(_outcome(r["hs"], r["aws"]))
            LO.append(out["band_lo"]); HI.append(out["band_hi"])
            OU.append(out["p_over25"]); BT.append(out["p_btts"])
            y_ou.append(1.0 if r["hs"] + r["aws"] >= 3 else 0.0)
            y_bt.append(1.0 if r["hs"] > 0 and r["aws"] > 0 else 0.0)
            seas.append(S)
    A = lambda x: np.asarray(x, dtype=float)
    return {"league": league, "test_seasons": test_seasons,
            "P_model": A(P_model), "P_elo": A(P_elo), "P_base": A(P_base),
            "P_mkt": A(P_mkt), "mkt_mask": np.asarray(mkt_mask),
            "Y": np.asarray(Y, dtype=int), "lo": A(LO), "hi": A(HI),
            "p_over": A(OU), "p_btts": A(BT), "y_over": A(y_ou), "y_btts": A(y_bt)}


def evaluate(d: dict, B: int = B_BOOT) -> dict:
    """Métricas + portão: ΔBrier pareada (régua − modelo) com IC bootstrap."""
    Y = d["Y"]
    n = len(Y)
    bm = brier(d["P_model"], Y)
    res = {"league": d["league"], "n": n, "test_seasons": len(d["test_seasons"]),
           "brier_model": float(bm.mean()),
           "logloss": float(logloss(d["P_model"], Y).mean()),
           "rps": float(rps(d["P_model"], Y).mean()),
           "ece": ece(d["P_model"], Y),
           "band": band_coverage(d["P_model"][:, 0], d["lo"], d["hi"], Y),
           "brier_over": float(((d["p_over"] - d["y_over"]) ** 2).mean()),
           "brier_btts": float(((d["p_btts"] - d["y_btts"]) ** 2).mean()),
           "reguas": {}}
    uni = np.full((n, 3), 1 / 3)
    for nome, P, mask in (("uniforme", uni, None), ("taxa_base", d["P_base"], None),
                          ("elo_puro", d["P_elo"], None), ("mercado", d["P_mkt"], d["mkt_mask"])):
        br = brier(P, Y)
        dl = br - bm                                   # >0 = modelo MELHOR que a régua
        if mask is not None:
            if mask.sum() < 30:
                res["reguas"][nome] = {"n": int(mask.sum()), "nota": "n insuficiente"}
                continue
            dl = dl[mask]
            br = br[mask]
            bm_m = bm[mask]
        else:
            bm_m = bm
        lo, hi = boot_ci(dl, B=B)
        res["reguas"][nome] = {
            "n": int(len(dl)), "brier_regua": float(br.mean()),
            "brier_modelo_no_recorte": float(bm_m.mean()),
            "delta": float(dl.mean()), "ic95": [lo, hi],
            "passa": bool(lo > 0)}
    return res


def report(res: dict) -> str:
    L = [f"\n===== {res['league']} — walk-forward, {res['test_seasons']} temporadas de teste, "
         f"n={res['n']} =====",
         f"Brier modelo {res['brier_model']:.4f} · LogLoss {res['logloss']:.4f} · "
         f"RPS {res['rps']:.4f} · ECE {res['ece']:.4f}",
         f"Brier over2.5 {res['brier_over']:.4f} · BTTS {res['brier_btts']:.4f}"]
    for nome, r in res["reguas"].items():
        if "nota" in r:
            L.append(f"  vs {nome:10s}: {r['nota']} (n={r['n']})")
            continue
        gate = "PASSA ✅" if r["passa"] else ("—" if nome == "mercado" else "FALHA ❌")
        L.append(f"  vs {nome:10s}: régua {r['brier_regua']:.4f} | Δ {r['delta']:+.4f} "
                 f"IC[{r['ic95'][0]:+.4f},{r['ic95'][1]:+.4f}] n={r['n']} -> {gate}")
    dentro = sum(1 for b in res["band"] if b["dentro"])
    L.append(f"  banda: {dentro}/{len(res['band'])} faixas dentro")
    for b in res["band"]:
        flag = "ok " if b["dentro"] else "FORA"
        L.append(f"    {b['faixa']} n={b['n']:5d} obs {b['obs']:.3f} "
                 f"banda [{b['lo']:.3f},{b['hi']:.3f}] {flag}")
    return "\n".join(L)


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Portão do baseline: walk-forward + 4 réguas.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--league", action="append")
    ap.add_argument("--burn-in", type=int, default=2)
    ap.add_argument("--fast", action="store_true", help="B=2000 e estratos=100 (exploração)")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print("[erro] rode o pipeline (ingest/elo/features) antes.")
        return 1
    B = 2000 if args.fast else B_BOOT
    ns = 100 if args.fast else None
    with db.session(args.db) as conn:
        leagues = args.league or [r[0] for r in conn.execute(
            "SELECT DISTINCT league FROM matches ORDER BY league")]
        gate_ok = True
        for lg in leagues:
            d = collect(conn, lg, burn_in=args.burn_in, n_strata=ns)
            res = evaluate(d, B=B)
            print(report(res))
            gate_ok &= res["reguas"]["uniforme"]["passa"] and res["reguas"]["taxa_base"]["passa"]
        print(f"\nPORTÃO DO BASELINE (uniforme E taxa-base, todas as ligas): "
              f"{'PASSA ✅' if gate_ok else 'FALHA ❌'}")
        print("Regra herdada: mercado é RÉGUA (teto honesto), não meta — Brier ~0,60 não é edge.")
    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
