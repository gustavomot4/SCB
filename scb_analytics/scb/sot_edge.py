"""sot_edge — candidato de evolução: proxy de xG via CHUTES NO GOL (SoT), só onde a
fonte tem stats de jogo (E0/Premier — o football-data não traz p/ o BRA).

Ângulo (gate-0): chutes no gol capturam domínio/qualidade de chance que o placar
(ruidoso) e o Elo não veem por inteiro. Medido: corr(SoT-edge, dr_Elo)=0,75 (não
redundante) e correlação parcial 0,11 com o saldo além do Elo.

    s(t)  = média PIT de (SoT_pró − SoT_contra) de t nos últimos K jogos COM stats
    edge  = s(mandante) − s(visitante)                          (anti look-ahead)
    δ     = clip(θ · edge, ±CAP)     θ em Elo-equivalente; K e θ da ERA DE CALIBRAÇÃO
    dr'   = dr_adj + δ

Onde não há stats (BRA, E0 pré-2000, começo de time) δ=0 — neutro, nada inventado.
Gate idêntico ao mando (D-21/26): ΔBrier 1X2 pareado com IC bootstrap>0 na VALIDAÇÃO
+ gols (over/BTTS) não regride + ECE não regride + kill-switch corr(δ,dr)<0,95.
Adoção (wiring no features_pit + bump de MODEL_VERSION) = decisão SEPARADA, em D-NN.

Uso:  python -m scb.sot_edge [--league E0] [--fast]
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

from . import config, db, draw_curve, predictor
from .ingest import DEFAULT_DB

K_GRID = [5, 10, 20]                    # janela (jogos) do rolling de SoT-diff
THETA_GRID = [10.0, 15.0, 20.0, 25.0, 30.0]   # canal 'dr': Elo-equivalente por unidade de edge
CAP = 60.0                              # teto de |δ| no canal 'dr' (Elo, mesmo do mando)
THETA_GRID_GD = [0.02, 0.04, 0.06, 0.08, 0.12]  # canal 'gd': GOLS por unidade de edge
CAP_GD = 1.5                            # teto de |δ| no canal 'gd' (gols)
THETA_GRID_TM = [0.02, 0.05, 0.08, 0.12]  # canal 'tm': GOLS por unidade de desvio de SoT-total
CAP_TM = 1.0                            # teto de |δ| no canal 'tm' (gols)
MIN_HIST = 3                            # sem histórico mínimo -> edge 0 (neutro)


def _serie(conn, league: str):
    return conn.execute(
        """SELECT m.match_id, m.season, m.home_team_id h, m.away_team_id a,
                  m.home_score hs, m.away_score aws, mf.dr_adj, mf.sigma_dr,
                  ms.sot_home sh, ms.sot_away sa
           FROM matches m JOIN match_features mf USING (match_id)
           LEFT JOIN match_stats ms USING (match_id)
           WHERE m.league=? ORDER BY m.date, m.match_id""", (league,)).fetchall()


def edge_series(rows, K: int) -> np.ndarray:
    """edge[i] = (SoT-diff rolling do mandante) − (do visitante). PIT: histórico do time
    é atualizado DEPOIS de ler a partida (anti look-ahead)."""
    hist: dict = defaultdict(list)
    edge = np.zeros(len(rows))
    for i, r in enumerate(rows):
        h, a = hist[r["h"]], hist[r["a"]]
        fh = sum(h[-K:]) / len(h[-K:]) if len(h) >= MIN_HIST else 0.0
        fa = sum(a[-K:]) / len(a[-K:]) if len(a) >= MIN_HIST else 0.0
        edge[i] = fh - fa
        if r["sh"] is not None and r["sa"] is not None:
            hist[r["h"]].append(r["sh"] - r["sa"])
            hist[r["a"]].append(r["sa"] - r["sh"])
    return edge


def total_series(rows, K: int) -> np.ndarray:
    """Volume PIT de SoT ENVOLVIDO no jogo: média de (SoT casa + SoT fora) dos últimos K
    jogos de cada time, combinada (mandante+visitante)/2. NaN sem histórico. Anti look-ahead.
    A centralização (subtrair a média) é feita no gate com constante do TREINO (sem vazar)."""
    hist: dict = defaultdict(list)
    tot = np.full(len(rows), np.nan)
    for i, r in enumerate(rows):
        h, a = hist[r["h"]], hist[r["a"]]
        if len(h) >= MIN_HIST and len(a) >= MIN_HIST:
            tot[i] = (sum(h[-K:]) / len(h[-K:]) + sum(a[-K:]) / len(a[-K:])) / 2.0
        if r["sh"] is not None and r["sa"] is not None:
            s = float(r["sh"] + r["sa"])          # SoT total do jogo (mesmo p/ os dois times)
            hist[r["h"]].append(s); hist[r["a"]].append(s)
    return tot


def _roll_pit(x: np.ndarray, L: int) -> np.ndarray:
    """Média móvel das últimas L observações VÁLIDAS estritamente ANTES de i (PIT). Serve de
    baseline contemporânea p/ tirar a deriva de era do SoT-total (sem vazar o presente)."""
    out = np.full(len(x), np.nan)
    buf: list = []
    for i, v in enumerate(x):
        if buf:
            out[i] = sum(buf[-L:]) / len(buf[-L:])
        if not np.isnan(v):
            buf.append(float(v))
    return out


def _probs(conn, league, rows, mask, delta, n_strata, channel="dr"):
    """Walk-forward (curva por fold). channel='dr' soma δ ao dr (afeta tudo); 'gd' passa δ
    como gd_extra — só a margem da Poisson, dr e perna Elo-direto intactos."""
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
        if channel == "dr":
            o = predictor.predict(r["dr_adj"] + delta[i], r["sigma_dr"], cache[S])
        elif channel == "gd":
            o = predictor.predict(r["dr_adj"], r["sigma_dr"], cache[S], gd_extra=delta[i])
        else:
            o = predictor.predict(r["dr_adj"], r["sigma_dr"], cache[S], tm_extra=delta[i])
        P.append((o["p_v"], o["p_e"], o["p_d"]))
        OU.append(o["p_over25"]); BT.append(o["p_btts"])
        Y.append(0 if r["hs"] > r["aws"] else (1 if r["hs"] == r["aws"] else 2))
        yo.append(1.0 if r["hs"] + r["aws"] >= 3 else 0.0)
        yb.append(1.0 if r["hs"] > 0 and r["aws"] > 0 else 0.0)
    A = lambda x: np.asarray(x, float)
    return A(P), np.asarray(Y, int), A(OU), A(BT), A(yo), A(yb)


def deltas_by_match(conn, league: str, K: int = 10, theta: float = 20.0) -> dict:
    """{match_id: δ} PIT para o wiring no features_pit se adotado. Neutro sem stats."""
    rows = _serie(conn, league)
    delta = np.clip(theta * edge_series(rows, K), -CAP, CAP)
    return {r["match_id"]: float(delta[i]) for i, r in enumerate(rows)}


def gate(conn, league: str, burn_in: int = 2, n_strata: int = 100, B: int = 10_000,
         channel: str = "dr") -> dict:
    """channel='dr' (D-32, rejeitado) soma δ ao dr (afeta 1X2 e gols); channel='gd'
    desloca SÓ a margem da Poisson — ângulo novo da D-32 (dr e Elo-direto intactos)."""
    from . import backtest_harness as bh
    all_rows = _serie(conn, league)
    stats_seasons = [r["season"] for r in all_rows if r["sh"] is not None]
    if not stats_seasons:
        print(f"\n== {league}: a fonte não tem stats de jogo — candidato não se aplica ==")
        return {"league": league, "passa": False, "nota": "sem stats na fonte"}
    grid, cap, un = ({"dr": (THETA_GRID, CAP, "Elo"), "gd": (THETA_GRID_GD, CAP_GD, "gols"),
                      "tm": (THETA_GRID_TM, CAP_TM, "gols")})[channel]
    target = "gols" if channel == "tm" else "1x2"      # o alvo do gate acompanha o canal
    smin = min(stats_seasons)
    rows = [r for r in all_rows if r["season"] >= smin]     # só a era com stats
    season = np.array([r["season"] for r in rows])
    dr = np.array([r["dr_adj"] for r in rows])
    seasons = sorted(set(season.tolist()))
    test = seasons[burn_in:]
    meio = max(1, len(test) // 2)
    m_cal = np.isin(season, test[:meio])
    m_val = np.isin(season, test[meio:])
    zero = np.zeros(len(rows))

    def feature(K):
        if channel == "tm":
            tot = total_series(rows, K)
            base = _roll_pit(tot, 380)                   # baseline móvel PIT (drift-robusto)
            return np.where(np.isnan(tot) | np.isnan(base), 0.0, tot - base)
        return edge_series(rows, K)

    def gols_brier(OU, BT, yo, yb):
        return ((OU - yo) ** 2 + (BT - yb) ** 2).mean()

    # ---- CALIBRAÇÃO: escolhe (K, θ) pelo ganho de Brier do ALVO no treino ----
    P0c, Yc, OU0c, BT0c, yoc, ybc = _probs(conn, league, rows, m_cal, zero, n_strata, channel)
    base = bh.brier(P0c, Yc).mean() if target == "1x2" else gols_brier(OU0c, BT0c, yoc, ybc)
    best, best_kt = -1e9, (K_GRID[0], grid[0])
    for K in K_GRID:
        feat = feature(K)
        for th in grid:
            delta = np.clip(th * feat, -cap, cap)
            P1c, _, OU1c, BT1c, _, _ = _probs(conn, league, rows, m_cal, delta, n_strata, channel)
            ganho = base - (bh.brier(P1c, Yc).mean() if target == "1x2"
                            else gols_brier(OU1c, BT1c, yoc, ybc))
            if ganho > best:
                best, best_kt = ganho, (K, th)
    K, th = best_kt
    feat = feature(K)
    delta = np.clip(th * feat, -cap, cap)

    # ---- GATE na VALIDAÇÃO (fora da amostra da escolha de K,θ) ----
    P0, Y, OU0, BT0, yo, yb = _probs(conn, league, rows, m_val, zero, n_strata, channel)
    P1, _, OU1, BT1, _, _ = _probs(conn, league, rows, m_val, delta, n_strata, channel)
    d1x2 = bh.brier(P0, Y) - bh.brier(P1, Y)
    lo, hi = bh.boot_ci(d1x2, B=B)
    d_gols = ((OU0 - yo) ** 2 + (BT0 - yb) ** 2) - ((OU1 - yo) ** 2 + (BT1 - yb) ** 2)
    glo, ghi = bh.boot_ci(d_gols, B=B)
    ece0, ece1 = bh.ece(P0, Y), bh.ece(P1, Y)
    dv = delta[m_val]
    ref = np.abs(dr[m_val]) if channel == "tm" else dr[m_val]   # tm depende de |dr| (T_m)
    corr = float(np.corrcoef(dv, ref)[0, 1]) if dv.std() > 0 else 0.0
    if target == "1x2":
        passa = lo > 0 and ghi > 0 and ece1 <= ece0 + 0.01 and abs(corr) < 0.95
    else:
        passa = glo > 0 and hi > 0 and ece1 <= ece0 + 0.01 and abs(corr) < 0.95
    v1 = "PASSA ✅ (alvo)" if (target == "1x2" and lo > 0) else ("guarda ok" if hi > 0 else "REGRIDE ❌")
    vg = "PASSA ✅ (alvo)" if (target == "gols" and glo > 0) else ("guarda ok" if ghi > 0 else "REGRIDE ❌")
    print(f"\n== {league} — proxy xG/SoT [canal={channel}, alvo={target}] "
          f"(K*={K}, θ*={th:g} {un}/feat; validação {test[meio]}..{test[-1]}, n={len(Y)}) ==")
    print(f"  δ na validação: médio {dv.mean():+.2f} {un} [{dv.min():+.2f},{dv.max():+.2f}] "
          f"· não-zero em {(dv != 0).mean():.0%} dos jogos")
    print(f"  1X2 : Δbrier {d1x2.mean():+.5f} IC95[{lo:+.5f},{hi:+.5f}] -> {v1}")
    print(f"  gols: Δbrier {d_gols.mean():+.5f} IC95[{glo:+.5f},{ghi:+.5f}] -> {vg}")
    print(f"  ECE {ece0:.4f} -> {ece1:.4f} ({'ok' if ece1 <= ece0 + 0.01 else 'REGRIDE ❌'}) "
          f"· kill-switch corr {corr:+.3f} ({'ok' if abs(corr) < 0.95 else 'REDUNDANTE ❌'})")
    print(f"  VEREDITO: {'PASSOU — adoção (wiring+bump) é decisão separada, registrar D-NN' if passa else 'REJEITAR — registrar D-NN com os números'}")
    return {"league": league, "channel": channel, "target": target, "K": K, "theta": th,
            "delta_1x2": float(d1x2.mean()), "ic": [lo, hi],
            "delta_gols": float(d_gols.mean()), "ic_gols": [glo, ghi],
            "ece0": float(ece0), "ece1": float(ece1), "corr": corr,
            "n_valid": int(len(Y)), "passa": bool(passa)}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Gate do proxy de xG por chutes no gol (SoT).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--league", action="append")
    ap.add_argument("--fast", action="store_true", help="n_strata=60, B=2000 (exploração)")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print("[erro] rode o pipeline antes.")
        return 1
    ns, B = (60, 2000) if args.fast else (100, 10_000)
    with db.session(args.db) as conn:
        leagues = args.league or ["E0"]
        for lg in leagues:
            gate(conn, lg, n_strata=ns, B=B)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
