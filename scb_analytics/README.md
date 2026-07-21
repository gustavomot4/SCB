# scb_analytics — código do SCB

Port evoluído do `scm_analytics` (D-02) para ligas de pontos corridos, multi-liga (D-03).
Contrato: `../contexto/MODELO-MATEMATICO.md` (SCB v1.0, congelado). **Verdade viva: `../CONTEXT.md`.**

**Estado (2026-07-21):** M0–M7.1 executadas — modelo oficial **`scb-v0.4-sot-goals-e0`**
(walk-forward BRA 0,6131 / E0 0,5894). Falta **M7.2** (empacotamento). Detalhe e histórico
no vault (`../DECISIONS.md`, `../CHANGELOG.md`).

## Rodar (Windows/PowerShell, na raiz `scb_analytics`)

```
pip install -r requirements.txt
python -m pytest -q                  # esperado: 90 passed

python -m scb.ingest --download      # 1x, baixa snapshot (BRA + 33 temporadas E0)
python -m scb.ingest                 # dados/*.csv -> dados/scb.sqlite (OFFLINE)

# pipeline do modelo (rebuild completo, na ordem):
python -m scb.elo_engine             # ratings PIT
python -m scb.features_pit           # features anti look-ahead (~20s)
python -m scb.draw_curve             # curva de empate POR LIGA (congelada)
python -m scb.predictor              # 18.200 previsões
python -m scb.backtest_harness       # esperado: BRA 0,6131 / E0 0,5894

python -m scb.simulate_league --season 2026   # P(título/G4/G6/Z4)
```

Web (5 telas, estilo EA FC): dê duplo-clique em **`Abrir SCB.bat`** (ou `python -m scb.web`) e
abra `http://127.0.0.1:5000`. Reinicie o processo + Ctrl+F5 após mudar código (o Flask cacheia).

Aceite de dados (medido na M1/M2): **BRA 5.496 jogos** (5.497 linhas − 1 sem placar; +3 de julho
via API-Futebol, D-36) · **E0 12.704**.

## Módulos

| Módulo | Papel |
|---|---|
| `scb/db.py` | schema SQLite (matches+league/season, odds_hist open/close, seasons, tabelas PIT, match_stats) |
| `scb/ingest.py` | parser determinístico (QA-01/02/03) · idempotente · guarda ±2d (D-82) · `resultados_extra` · **2ª fonte API-Futebol** (stats + resultados do BRA, D-34/36) |
| `scb/odds.py` | de-vig proporcional · blend (peso ≤0,20) · fallback PS→Avg→B365 (D-16) |
| `scb/elo_engine.py` | Elo PIT zero-sum · mando por liga · hook de virada de temporada (ρ, D-25) |
| `scb/features_pit.py` | forma com decay por jogo · σ_dr · mando rolling na E0 (D-26) · anti look-ahead |
| `scb/draw_curve.py` | curva de empate empírica POR LIGA (D-07), congelada por versão |
| `scb/predictor.py` | λ=f/g(dr) · Poisson · ensemble c/ mercado · SoT-total no canal de gols (D-33/35) |
| `scb/backtest_harness.py` | walk-forward por temporada · 4 réguas · IC bootstrap B=10k |
| `scb/simulate_league.py` | Monte Carlo da tabela · desempate CBF (D-18) · real travado |
| `scb/predict_match.py` · `scb/registrar.py` | porta de produção · registro imutável + settle + `registrar auto` (D-31) |
| `scb/web.py` · `scb/badges.py` | Flask local (Prever · Tabela+Classificação real · Calibração · Jogos · Prospectivo) · escudos SVG |
| candidatos OFF | `calibrate` `drift` `descanso` `dixon_coles` `mando_rolling` `season_rho` `sot_edge` — testados no portão, flag por liga |

Dados manuais na rodada (lag da fonte): copie `dados/resultados_extra.csv.example` →
`resultados_extra.csv` e preencha; o ingest carrega sozinho com a guarda anti-duplicata.
Operação da temporada: `../Operacao BRA 2026.md`.

## Próximo

**M7.2 — empacotamento** (`../prompts/05-revisao-entrega.md` + `../CHECKLIST.md`): zip só com
fonte + docs + dados curados (sem `.venv`/`.git`/`__pycache__`/`*.sqlite`/`*.png`), abrir e conferir.
