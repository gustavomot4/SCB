"""predictor: features -> P(V/E/D)+banda, λ, over2.5, BTTS (baseline SCB) — port do SCM.

Lê `match_features` (dr_adj, σ_dr) -> GD=f(dr), T_m=g(dr) -> matriz Poisson +
leitura Elo-direto PROPAGADA (curva de empate DA LIGA, D-07) -> ensemble.
Grava `predictions` carimbada com `config.MODEL_VERSION`.

Herança intacta (contrato SCB v1.0 §1):
  - f_linear = θ·dr/100 · g_linear = T_base(liga) + κ·|dr|/100   [a calibrar M6]
  - piso de λ CONSERVA T_m (D-22 SCM)
  - propagação DETERMINÍSTICA por estratos de igual probabilidade (sem RNG, reprodutível)
  - over/BTTS são Poisson-condicionais (A1); coerência [0,1] pelo cap C1 por amostra
  - ensemble sem odds: Poisson 0,56 / Elo 0,44; clamp por leitura e final
Fora (D-06): estilo, altitude/calor, knockout/ε. Hooks mantidos: δ_ata (desfalques §3.6),
perna AD (`ad_ved`, w_ad=0 até re-passar o portão na liga — D-05).
NÚCLEO ÚNICO da leitura C1 (D-43): `draw_curve.ved_from_dr` — aqui só se passa o ε.
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from pathlib import Path
from statistics import NormalDist
from typing import Optional

from . import config, db, draw_curve
from .ingest import DEFAULT_DB


@dataclass(frozen=True)
class PredictParams:
    theta_gd: float = 0.45       # GD = θ·dr/100                      [a calibrar M6]
    t_base: float = 2.6          # T_m = T_base + κ·|dr|/100 (por liga via run/config)
    kappa_tm: float = 0.10       #                                    [a calibrar M6]
    lambda_min: float = 0.15     # piso de λ (regularização honesta)  [a calibrar M6]
    max_goals: int = 10
    draw_eps: float = 0.02       # folga do cap C1 (herdado)
    n_strata: int = 200          # propagação determinística
    w_poisson: float = 0.56      # pesos sem odds (backtest histórico) [a calibrar M6]
    w_elo: float = 0.44
    w_ad: float = 0.0            # perna AD: OFF até o portão da liga (D-05; no SCM validou 0,5)
    clamp_lo: float = 0.02
    clamp_hi: float = 0.96
    dc_rho: float = 0.0          # Dixon-Coles τ(ρ) na matriz (D-27; 0 = Poisson puro)
    curve: Optional[dict] = field(default=None)   # curva de empate DA LIGA (D-07)


def gd_of(dr: float, p: PredictParams) -> float:
    return p.theta_gd * dr / 100.0


def tm_of(dr: float, p: PredictParams) -> float:
    return p.t_base + p.kappa_tm * abs(dr) / 100.0


def lambdas(dr: float, p: PredictParams, datk_a: float = 0.0, datk_b: float = 0.0,
            gd_extra: float = 0.0, tm_extra: float = 0.0):
    """λ_A, λ_B com piso que CONSERVA o total (D-22): o desconto sai do favorito.
    `gd_extra` desloca SÓ a margem; `tm_extra` desloca SÓ o TOTAL (over/BTTS) — pontos de
    injeção de candidatos do canal de gols sem tocar a perna Elo-direto. Default 0 = inócuo."""
    gd = gd_of(dr, p) + gd_extra
    tm = tm_of(dr, p) + tm_extra
    la = (tm + gd) / 2.0
    lb = (tm - gd) / 2.0
    lmin = p.lambda_min
    if lb < lmin:
        lb = lmin
        la = max(lmin, tm - lb)
    elif la < lmin:
        la = lmin
        lb = max(lmin, tm - la)
    if datk_a:                                   # desfalque OFENSIVO corta o PRÓPRIO λ
        la = max(lmin, la * (1.0 - datk_a))      # (não infla o rival — contrato §3.6)
    if datk_b:
        lb = max(lmin, lb * (1.0 - datk_b))
    return la, lb


def _pois_vec(lam: float, kmax: int) -> list:
    out = [math.exp(-lam)]
    for k in range(1, kmax + 1):
        out.append(out[-1] * lam / k)
    return out


def poisson_reads(lam_a: float, lam_b: float, max_goals: int = 10,
                  dc_rho: float = 0.0) -> dict:
    """V/E/D, over2.5, BTTS e top-5 da MESMA matriz (A1). Com dc_rho≠0 aplica o
    τ de Dixon-Coles nas células de placar baixo e renormaliza (D-27; ρ=0 ≡ puro)."""
    pa = _pois_vec(lam_a, max_goals)
    pb = _pois_vec(lam_b, max_goals)
    cells = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            cells[(i, j)] = pa[i] * pb[j]
    if dc_rho:
        cells[(0, 0)] *= max(0.0, 1.0 - lam_a * lam_b * dc_rho)
        cells[(0, 1)] *= 1.0 + lam_a * dc_rho
        cells[(1, 0)] *= 1.0 + lam_b * dc_rho
        cells[(1, 1)] *= 1.0 - dc_rho
        s = sum(cells.values())
        cells = {k: v / s for k, v in cells.items()}
    pv = pe = pd = over = 0.0
    for (i, j), pij in cells.items():
        if i > j:
            pv += pij
        elif i == j:
            pe += pij
        else:
            pd += pij
        if i + j >= 3:
            over += pij
    if dc_rho:
        btts = 1.0 - sum(cells[(0, j)] for j in range(max_goals + 1)) \
               - sum(cells[(i, 0)] for i in range(max_goals + 1)) + cells[(0, 0)]
    else:
        btts = (1 - math.exp(-lam_a)) * (1 - math.exp(-lam_b))
    top = sorted(cells.items(), key=lambda c: -c[1])[:5]
    top5 = [(f"{i}x{j}", round(q, 4)) for (i, j), q in top]
    return {"pv": pv, "pe": pe, "pd": pd, "over25": over, "btts": btts, "top5": top5}


_STD_Q: dict = {}


def _std_quantiles(S: int) -> list:
    """Quantis da Normal padrão em (s+0.5)/S, cacheados (D-30: 1 inv_cdf por estrato TOTAL)."""
    q = _STD_Q.get(S)
    if q is None:
        snd = NormalDist(0.0, 1.0)
        q = [snd.inv_cdf((s + 0.5) / S) for s in range(S)]
        _STD_Q[S] = q
    return q


def elo_direct_read(dr: float, sigma_dr: float, p: PredictParams) -> dict:
    """Leitura Elo-direto PROPAGADA inteira (estratos determinísticos; banda 16/84 de P(V)).

    Cada amostra passa pela C1 da LIGA com cap (P∈[0,1] por construção). Jensen: a
    propagação encolhe o favorito rumo a 0,5.
    """
    if p.curve is None:
        raise ValueError("PredictParams.curve ausente — congele a curva da liga (scb.draw_curve)")
    sigma = max(sigma_dr, 1e-6)
    S = p.n_strata
    pvs = []
    spv = spe = spd = 0.0
    for z in _std_quantiles(S):
        r = draw_curve.ved_from_dr(dr + sigma * z, p.curve, eps=p.draw_eps)
        pvs.append(r["p_v"])
        spv += r["p_v"]
        spe += r["p_e"]
        spd += r["p_d"]
    pvs.sort()
    return {"pv": spv / S, "pe": spe / S, "pd": spd / S,
            "band_lo": pvs[int(0.16 * S)], "band_hi": pvs[int(0.84 * S)]}


def _clamp_norm(triple, lo, hi):
    v = [min(hi, max(lo, x)) for x in triple]
    s = sum(v)
    return [x / s for x in v]


def predict(dr: float, sigma_dr: float, p: PredictParams,
            datk_a: float = 0.0, datk_b: float = 0.0, ad_ved=None,
            gd_extra: float = 0.0, tm_extra: float = 0.0) -> dict:
    """Previsão de 1 confronto: Poisson + Elo-direto (+ AD se w_ad>0) -> ensemble.
    `gd_extra`/`tm_extra` afetam só a Poisson (margem/total), não a perna Elo-direto."""
    la, lb = lambdas(dr, p, datk_a=datk_a, datk_b=datk_b, gd_extra=gd_extra, tm_extra=tm_extra)
    pois = poisson_reads(la, lb, p.max_goals, dc_rho=p.dc_rho)
    elo = elo_direct_read(dr, sigma_dr, p)
    cp = _clamp_norm((pois["pv"], pois["pe"], pois["pd"]), p.clamp_lo, p.clamp_hi)
    ce = _clamp_norm((elo["pv"], elo["pe"], elo["pd"]), p.clamp_lo, p.clamp_hi)
    ws = p.w_poisson + p.w_elo
    if ad_ved is not None and p.w_ad > 0:
        ca = _clamp_norm(ad_ved, p.clamp_lo, p.clamp_hi)
        ws += p.w_ad
        mix = [(p.w_poisson * cp[i] + p.w_elo * ce[i] + p.w_ad * ca[i]) / ws for i in range(3)]
    else:
        mix = [(p.w_poisson * cp[i] + p.w_elo * ce[i]) / ws for i in range(3)]
    final = _clamp_norm(mix, p.clamp_lo, p.clamp_hi)
    return {"p_v": final[0], "p_e": final[1], "p_d": final[2],
            "band_lo": elo["band_lo"], "band_hi": elo["band_hi"],
            "lambda_a": la, "lambda_b": lb,
            "p_over25": pois["over25"], "p_btts": pois["btts"], "top5": pois["top5"]}


def params_for(conn, league: str, base: Optional[PredictParams] = None) -> PredictParams:
    """Params da liga: T_base do config + curva de empate congelada (constrói se faltar)."""
    curve = draw_curve.load(conn, league)
    if curve is None:
        curve = draw_curve.build(conn, league)
        draw_curve.freeze(conn, curve)
        print(f"  [aviso] curva de empate de {league} não estava congelada — construída agora")
    b = base or PredictParams()
    return PredictParams(theta_gd=b.theta_gd, t_base=config.t_base_for(league),
                         kappa_tm=b.kappa_tm, lambda_min=b.lambda_min,
                         max_goals=b.max_goals, draw_eps=b.draw_eps,
                         n_strata=b.n_strata, w_poisson=b.w_poisson, w_elo=b.w_elo,
                         w_ad=b.w_ad, clamp_lo=b.clamp_lo, clamp_hi=b.clamp_hi,
                         dc_rho=config.dc_rho_for(league), curve=curve)


def run(conn, incremental: bool = False, base: Optional[PredictParams] = None) -> dict:
    """Previsões para todos os jogos com features. Idempotente por (match_id, versão)."""
    db.init_schema(conn)
    if conn.execute("SELECT COUNT(*) FROM match_features").fetchone()[0] == 0:
        raise RuntimeError("match_features vazio — rode features_pit.run primeiro.")
    ver = config.MODEL_VERSION
    if incremental:
        done = {r[0] for r in conn.execute(
            "SELECT match_id FROM predictions WHERE versao_modelo=?", (ver,))}
    else:
        conn.execute("DELETE FROM predictions WHERE versao_modelo=?", (ver,))
        done = set()
    by_league = {}
    rows = conn.execute(
        """SELECT m.match_id, m.league, mf.dr_adj, mf.sigma_dr
           FROM matches m JOIN match_features mf USING (match_id)
           ORDER BY m.date, m.match_id""").fetchall()
    from . import sot_edge                               # lazy: evita ciclo de import (D-33)
    sot_maps: dict = {}
    n = 0
    for r in rows:
        if r["match_id"] in done:
            continue
        lg = r["league"]
        if lg not in by_league:
            by_league[lg] = params_for(conn, lg, base)
            sot_maps[lg] = sot_edge.tm_extra_map(conn, lg)   # {} se a liga não usa SoT-gols
        out = predict(r["dr_adj"], r["sigma_dr"], by_league[lg])
        p_over, p_btts = out["p_over25"], out["p_btts"]
        tm = sot_maps[lg].get(r["match_id"], 0.0)       # D-33: SoT-total SÓ no over2.5/BTTS
        if tm:
            p_over, p_btts = sot_edge.over_btts_tm(out["lambda_a"], out["lambda_b"], tm,
                                                   by_league[lg].max_goals)
        conn.execute(
            """INSERT OR REPLACE INTO predictions
               (match_id, versao_modelo, p_v, p_e, p_d, band_pv_lo, band_pv_hi,
                lambda_a, lambda_b, p_over25, p_btts)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (r["match_id"], ver, out["p_v"], out["p_e"], out["p_d"],
             out["band_lo"], out["band_hi"], out["lambda_a"], out["lambda_b"],
             p_over, p_btts))
        n += 1
    db.set_meta(conn, "model_version", ver)
    conn.commit()
    return {"predictions": n, "version": ver}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Gera previsões baseline (grava predictions).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--incremental", action="store_true")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] SQLite não encontrado: {args.db}. Rode o pipeline antes.")
        return 1
    with db.session(args.db) as conn:
        stats = run(conn, incremental=args.incremental)
        print(f"previsões: {stats['predictions']} jogos  [{stats['version']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
