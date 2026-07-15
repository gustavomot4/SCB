---
tags: [scb, decisoes, adr]
status: vivo
tipo: decisoes
data: 2026-07-14
---

# Decisões técnicas do SCB (ADRs)
Registro curto de *por que* cada escolha. **Append-only** — decisão nova = linha nova; decisão revertida = linha nova citando a antiga (nunca editar a antiga). Numeração própria do SCB (as D-NN do SCM são citadas como "D-NN SCM").

| # | Data | Decisão | Por quê |
|---|---|---|---|
| D-01 | 2026-07-14 | **Herdar as 7 regras de negócio do SCM inalteradas** (R$0, local/offline no cálculo, probabilidades, registro imutável, não inventar dados, sem ML, portão de backtest) | são agnósticas ao campeonato (viabilidade 2026-06-28); mudá-las = decisão do Gustavo, não de agente |
| D-02 | 2026-07-14 | **Port do `scm_analytics`** (fork → `scb_analytics`, pacote `scb/`), não reescrita | ~70% entra sem mexer; reescrever re-introduz bugs já pagos (D-22/34/80/82/83/85 SCM). Decisão do Gustavo nesta data |
| D-03 | 2026-07-14 | **Multi-liga desde o dia 1**: ingest/config parametrizados (`leagues.json`); **E0 valida o port, BRA é a entrega** | isola "bug de port" de "dificuldade da liga"; football-data entrega tudo no mesmo formato; custo marginal baixo. Decisão do Gustavo nesta data |
| D-04 | 2026-07-14 | **football-data.co.uk = fonte primária** (BRA extra + E0 main; `notes.txt` versionado); martj42 sai | única fonte grátis com resultados + odds de abertura E fechamento; resolve a lacuna nº 1 do SCM (CLV manual). Verificada online em 2026-07-14 |
| D-05 | 2026-07-14 | **A lista-morta do SCM NÃO transfere**: todo termo rejeitado lá re-passa pelo portão aqui (e vice-versa: os adotados também) | o dado e o contexto mudaram (ex.: descanso era ~0 em seleção e é candidato real em clube; altitude era real na Copa e é ~0 no Brasil) |
| D-06 | 2026-07-14 | **Termos de Copa ficam OFF/fora do pipeline**: altitude, confederação, knockout/ε-pênaltis, bracket, tempo do gol | ver contrato §2; código permanece no repo como candidato OFF documentado (custo zero, reativável) |
| D-07 | 2026-07-14 | **Curva de empate C1 reconstruída POR LIGA** (tabela `P_E(\|dr\|)` empírica da própria liga, PIT, congelada com a versão) | regime de empate de liga ≠ seleções; usar a curva do martj42 seria erro sistemático de P(E). Família da D-26 SCM |
| D-08 | 2026-07-14 | **Validação = walk-forward por temporada** (rolling origin), IC bootstrap pareado B=10k seed=12345; **4 réguas**: uniforme, taxa-base da liga, Elo-puro, mercado de-vigged (abertura e fechamento) | mais honesto p/ liga (churn entre temporadas) que o corte fixo <2015/≥2015 do SCM; taxa-base é a régua que liga equilibrada exige; mercado agora tem série histórica grátis |
| D-09 | 2026-07-14 | **Teto do peso de mercado no ensemble mantido em 0,20** (D-08 SCM) | regra de negócio herdada; ver Q-01 abaixo |
| D-10 | 2026-07-14 | **Alvo de operação: temporada 2026 em andamento** — registro prospectivo começa na M5, sempre DEPOIS do baseline validado (M4) | decisão do Gustavo nesta data; "baseline primeiro" preservado |

## Questões abertas (não são decisões ainda)

| # | Questão | Dono | Quando decidir |
|---|---|---|---|
| Q-01 | Com série histórica de odds, o backtest pode medir o peso ótimo do mercado no ensemble. Se der > 0,20: sobe o teto? | Gustavo | após M4 (com os números na mesa) |
| Q-02 | Aquecer o Elo do BRA com o dataset Kaggle 2003+ (sem odds)? | M1 decide com evidência de qualidade | M1 |
| Q-03 | Regulamento CBF vigente de desempate da Série A (vitórias→saldo→…): confirmar na fonte oficial antes de codificar | implementador | M5 |
