"""Curva de empate C1 POR LIGA (D-07) — tabela empírica P_E(|dr|), interpolada e capada.

Papel (contrato SCB v1.0 §1, herdado do apêndice de formas v5 §3 / D-26 SCM):
transforma `dr` na leitura V/E/D "Elo-direto" com P(V), P(D) ∈ [0,1] POR CONSTRUÇÃO:

    we(dr)   = 1/(1+10^(−dr/400))                      # logística (forma FIXA)
    pe(dr)   = min( P_E(|dr|),  2·min(we, 1−we) − ε )  # tabela empírica + cap (FIXO)
    pv       = we − pe/2 ;  pd = 1 − pv − pe           # decomposição (FIXA)

O que é DA LIGA (por isso D-07): a tabela `P_E(|dr|)` — construída do histórico da
PRÓPRIA liga (regimes de empate são muito diferentes: BRA ~27% vs E0 moderno ~22%,
medidos na M1). A do martj42 (seleções) NÃO serve.

Anti-vazamento (para a M4): `build(..., max_season=N)` constrói a curva SÓ com
temporadas ≤ N — o harness walk-forward reconstrói por fold, só com o treino.
A curva de PRODUÇÃO congela com todo o histórico e carimba versão+escopo em `meta`
(família D-24/D-26: curva empírica congelada é rastreável).

Uso:
    python -m scb.draw_curve            # constrói e congela p/ todas as ligas da base
"""
from __future__ import annotations

import argparse
import json
from datetime import date as _date
from pathlib import Path
from typing import Optional

from . import db
from .elo_engine import we
from .ingest import DEFAULT_DB

EPS_CAP = 0.01                            # folga do cap [herdado do contrato]
DEFAULT_BINS = [0, 25, 50, 75, 100, 150, 200, 300, 400]   # bordas de |dr|; última é aberta
MIN_N_BIN = 200                           # bin com n < MIN_N_BIN funde com o vizinho anterior


def build(conn, league: str, max_season: Optional[int] = None,
          bins: Optional[list] = None, min_n: int = MIN_N_BIN) -> dict:
    """Constrói a tabela empírica P_E por faixa de |dr| para a liga.

    Usa `match_ratings.dr` (PRÉ-jogo, Elo+mando — PIT por construção do elo_engine).
    `max_season`: só temporadas ≤ N (anti-vazamento no backtest). Bins com pouca
    amostra são fundidos com o anterior (sem taxa inventada em bin vazio).
    """
    bins = list(bins or DEFAULT_BINS)
    q = """SELECT ABS(mr.dr) adr, (m.home_score = m.away_score) is_draw
           FROM matches m JOIN match_ratings mr USING (match_id)
           WHERE m.league = ?"""
    args: list = [league]
    if max_season is not None:
        q += " AND m.season <= ?"
        args.append(max_season)
    rows = conn.execute(q, args).fetchall()
    if not rows:
        raise ValueError(f"sem jogos p/ curva: liga={league} max_season={max_season} "
                         f"(rode elo_engine antes)")
    counts = [[0, 0] for _ in bins]                    # [n, n_draw] por bin (última aberta)
    for adr, is_draw in rows:
        i = 0
        for j in range(len(bins) - 1, -1, -1):
            if adr >= bins[j]:
                i = j
                break
        counts[i][0] += 1
        counts[i][1] += int(is_draw)
    # funde bins raros com o ANTERIOR (mantém a borda esquerda do bloco fundido)
    merged_edges, merged_counts = [bins[0]], [counts[0][:]]
    for edge, cnt in zip(bins[1:], counts[1:]):
        if merged_counts[-1][0] < min_n or cnt[0] < min_n:
            merged_counts[-1][0] += cnt[0]
            merged_counts[-1][1] += cnt[1]
        else:
            merged_edges.append(edge)
            merged_counts.append(cnt[:])
    centers, pe, ns = [], [], []
    for k, (edge, cnt) in enumerate(zip(merged_edges, merged_counts)):
        right = merged_edges[k + 1] if k + 1 < len(merged_edges) else edge + 100
        centers.append((edge + right) / 2.0)
        pe.append(cnt[1] / cnt[0] if cnt[0] else 0.0)
        ns.append(cnt[0])
    return {"league": league, "centers": centers, "pe": pe, "n": ns,
            "n_total": len(rows), "max_season": max_season,
            "built": _date.today().isoformat()}


def pe_raw(adr: float, curve: dict) -> float:
    """P_E interpolada linearmente nos centros dos bins; clampa nas pontas."""
    cs, ps = curve["centers"], curve["pe"]
    if adr <= cs[0]:
        return ps[0]
    if adr >= cs[-1]:
        return ps[-1]
    for i in range(1, len(cs)):
        if adr <= cs[i]:
            t = (adr - cs[i - 1]) / (cs[i] - cs[i - 1])
            return ps[i - 1] + t * (ps[i] - ps[i - 1])
    return ps[-1]


def ved_from_dr(dr: float, curve: dict, eps: float = EPS_CAP) -> dict:
    """Leitura C1: V/E/D do dr com P ∈ [0,1] por construção (cap + decomposição)."""
    w = we(dr)
    pe = min(pe_raw(abs(dr), curve), max(0.0, 2.0 * min(w, 1.0 - w) - eps))
    pv = w - pe / 2.0
    pd = 1.0 - pv - pe
    return {"p_v": pv, "p_e": pe, "p_d": pd}


def freeze(conn, curve: dict) -> None:
    """Congela a curva em meta (rastreável: liga, escopo, data, versão do pacote)."""
    from . import __version__
    payload = dict(curve, version=__version__)
    db.set_meta(conn, f"draw_curve_{curve['league']}", json.dumps(payload))


def load(conn, league: str) -> Optional[dict]:
    row = conn.execute("SELECT value FROM meta WHERE key = ?",
                       (f"draw_curve_{league}",)).fetchone()
    return json.loads(row["value"]) if row else None


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Constrói e congela a curva de empate por liga (D-07).")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--league", action="append", help="default: todas as ligas da base")
    p.add_argument("--max-season", type=int, default=None,
                   help="corta em temporada <= N (uso do backtest; produção = sem corte)")
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] SQLite não encontrado: {args.db}. Rode ingest + elo_engine antes.")
        return 1
    with db.session(args.db) as conn:
        leagues = args.league or [r[0] for r in conn.execute(
            "SELECT DISTINCT league FROM matches ORDER BY league")]
        for lg in leagues:
            curve = build(conn, lg, max_season=args.max_season)
            freeze(conn, curve)
            print(f"\n{lg} — P_E(|dr|), n={curve['n_total']}"
                  + (f" (temporadas <= {args.max_season})" if args.max_season else "")
                  + ":")
            for c, pe, n in zip(curve["centers"], curve["pe"], curve["n"]):
                print(f"  |dr|~{c:5.0f}: {pe:.3f}  [n={n}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
