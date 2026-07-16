"""odds — de-vig, armazenamento e leitura de mercado com fallback (D-13/D-16).

Port do `scm/odds.py` (D-44 SCM). Diferenças de liga:
- odds vêm do PRÓPRIO CSV de resultados (ingest grava por fonte e estágio);
- leitura usa a CADEIA DE FALLBACK por estágio (D-16): Pinnacle morreu no
  football-data em 2025/26 (medido na M1: PSC 0% no BRA-2026);
- mercado no ensemble segue peso ≤ 0,20 (D-08 SCM / D-09; Q-01 aberta).

De-vig proporcional: implícita_i = (1/odd_i) / Σ(1/odd_j).
Probabilidade, não certeza; mercado é benchmark, não verdade.
"""
from __future__ import annotations

W_MARKET = 0.20  # contrato §1 / D-09 (Q-01 só reabre com números da M4)

# D-16: prioridade por estágio (medido na M1). 'PS' = Pinnacle; 'Avg' = média do
# mercado; 'B365' = bet365. No estágio 'close' as fontes têm o sufixo C no CSV,
# mas aqui normalizamos o NOME da família (source) — o estágio já distingue.
PRIORITY = {"close": ["PS", "Avg", "B365"], "open": ["PS", "Avg", "B365"]}


def implied_probs(odd_home: float, odd_draw: float, odd_away: float) -> dict:
    """Odds decimais -> probabilidades de-vigged (somam 1). Erro se alguma odd <= 1."""
    odds = (odd_home, odd_draw, odd_away)
    if any((o is None) or (o <= 1.0) for o in odds):
        raise ValueError("odds decimais inválidas (todas devem ser > 1.0)")
    inv = [1.0 / o for o in odds]
    s = sum(inv)
    return {"p_v": inv[0] / s, "p_e": inv[1] / s, "p_d": inv[2] / s}


def blend(model: dict, market: dict, w: float = W_MARKET) -> dict:
    """Mistura 1X2 do modelo com o mercado (peso w) e renormaliza."""
    mix = {k: (1.0 - w) * model[k] + w * market[k] for k in ("p_v", "p_e", "p_d")}
    s = sum(mix.values()) or 1.0
    return {k: v / s for k, v in mix.items()}


def store(conn, natural_key: str, match_id, stage: str, source: str,
          market: dict, asof: str | None = None) -> None:
    """Grava mercado de-vigged por (natural_key, stage, source). Idempotente (upsert)."""
    conn.execute(
        """INSERT INTO odds_hist (natural_key, match_id, stage, source, p_home, p_draw, p_away, asof)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(natural_key, stage, source) DO UPDATE SET
             p_home=excluded.p_home, p_draw=excluded.p_draw, p_away=excluded.p_away,
             match_id=excluded.match_id, asof=excluded.asof""",
        (natural_key, match_id, stage, source,
         market["p_v"], market["p_e"], market["p_d"], asof),
    )


def market_read(conn, match_id: int, stage: str = "close",
                priority: list[str] | None = None) -> dict | None:
    """Mercado de-vigged do jogo no estágio pedido, pela cadeia de fallback (D-16).

    Devolve {'p_v','p_e','p_d','source'} da PRIMEIRA fonte disponível na prioridade,
    ou None se nenhuma existir (jogo sem odds -> ensemble roda sem a perna, contrato §1).
    """
    for src in (priority or PRIORITY[stage]):
        row = conn.execute(
            "SELECT p_home, p_draw, p_away FROM odds_hist "
            "WHERE match_id=? AND stage=? AND source=?", (match_id, stage, src)).fetchone()
        if row and row["p_home"] is not None:
            return {"p_v": row["p_home"], "p_e": row["p_draw"], "p_d": row["p_away"],
                    "source": src}
    return None
