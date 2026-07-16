# scb_analytics — código do SCB

Port evoluído do `scm_analytics` (D-02) para ligas de pontos corridos, multi-liga (D-03).
Contrato: `../contexto/MODELO-MATEMATICO.md` (SCB v1.0, congelado). Estado: **M2 (schema + ingest)**.

## Rodar (Windows/PowerShell, na raiz `scb_analytics`)

```
pip install -r requirements.txt
python -m pytest -q                  # esperado: 14 passed
python -m scb.ingest --download      # 1x, baixa snapshot (BRA + 33 temporadas E0)
python -m scb.ingest                 # dados/*.csv -> dados/scb.sqlite (OFFLINE)
```

Aceite M2 (contagens da fonte, medidas na M1): **BRA 5.496 jogos** (5.497 linhas − 1 sem placar) · **E0 12.704**.

## Módulos (M2)

| Módulo | Papel |
|---|---|
| `scb/db.py` | schema SQLite (teams, matches+league/season, odds_hist open/close, seasons, meta + tabelas PIT p/ M3) |
| `scb/ingest.py` | parser determinístico (QA-01/02/03) · idempotente por natural_key · guarda ±2d (D-82) · `--dedup` · `resultados_extra.csv` · seasons |
| `scb/odds.py` | de-vig proporcional · blend (peso ≤0,20) · `market_read` com fallback PS→Avg→B365 (D-16) |

Dados manuais na rodada (lag da fonte): copie `dados/resultados_extra.csv.example` → `resultados_extra.csv` e preencha; o ingest carrega sozinho com a guarda anti-duplicata.

Próximo (M3): `elo_engine` → `features_pit` → `predictor` (curva de empate POR LIGA), 1 módulo por vez.
