---
tags: [scb, changelog, historico]
status: vivo
tipo: log
---

# CHANGELOG — SCB

> Log datado, append-only. **Não é carregado nas sessões** (o presente mora no CONTEXT.md). Uma linha por evento relevante; detalhe fica no commit/D-NN.

## 2026-07-16 (h) — M6.4: C1 descanso intra-liga rejeitado (D-22)
- `scb/descanso.py` + 3 testes (59): rest diferencial PIT com clip [2,8], β em grade. BRA e E0: IC cruza zero; kill-switch ok. Diagnóstico: rodadas simétricas INTRA-liga (\|diff\| ~0,7d) — a congestão real exige calendário externo (lacuna declarada). Placar da fila: 4 testados, 1 aprovado (mando rolling E0), 3 rejeitados com números.

## 2026-07-16 (g) — M6.3: PRIMEIRO TERMO A PASSAR UM PORTÃO NO SCB (D-21)
- `scb/mando_rolling.py` (ângulo novo da D-19): δ do mando por janela móvel PIT, inversão exata da curva Elo, cap ±60, zero parâmetro além de W. +3 testes (56).
- **E0 PASSA:** 1X2 +0,00180 IC[+0,00059,+0,00302] (n=6.080), gols +0,00066 IC>0, kill-switch −0,004; δ vigente −36,8 Elo (mando pós-COVID). **BRA rejeitado** (IC cruza; δ −12). Q-04: adoção na E0 = decisão do Gustavo (flag OFF até lá).
- Método validado ponta a ponta: rejeição da M6.1 apontou o ângulo; o portão separou liga com sinal (E0) de liga sem (BRA).

## 2026-07-16 (f) — M6.2 rejeitada · Q-03 fechada · M6.1-E0 rejeitada
- **D-20:** drift PIT do canal de gols (C3, família D-84 SCM) REJEITADO nas 2 ligas (IC cruza zero; kill-switch ok). `scb/drift.py` + `config.USE_MKT_DRIFT=False` + 3 testes (53 no total). Interpretação: o ganho do SCM vinha da estrutura por classe; liga única não tem.
- M6.1 na E0 (run do Gustavo): também rejeitada (T_base do treino regride gols) — D-19 completa nas 2 ligas.
- **Q-03 FECHADA por verificação web:** ordem CBF 2026 (vitórias→saldo→gols pró→confronto direto→cartões→sorteio) = a implementada; simplificações da D-18 seguem declaradas.
- Estado honesto da evolução: 2 candidatos testados, 2 rejeitados com números — baseline v0.1 segue o melhor modelo. Fila: M6.3 (mando rolling PIT), C1/C2/C4/C5/C6, banda.

## 2026-07-16 (e) — M5 FECHADA (oficial) + M6.1 rodada e REJEITADA (o portão protegeu)
- M5 oficial: 50 passed; tabela BRA 2026 na tela do Gustavo (Palmeiras 78,8%). Operação liberada ([[Operacao BRA 2026]]).
- M6.1 (`scb/calibrate.py`): grid estático de H_pred/T_base com era de validação separada → **REJEITADO (D-19)**: candidato do treino (H=120, T_base=2,20) piora gols na validação (IC<0). Causa: não-estacionariedade (mando ↓ pós-COVID, gols ↑ recentes) — regime inverte entre eras, calibração estática corrige ao contrário. Mesmo padrão D-25/D-40 SCM.
- Rota da M6: C3 (janela móvel PIT de gols — família aprovada no SCM D-84) e candidato novo "mando rolling PIT". Baseline v0.1 intacto.

## 2026-07-16 (d) — M4 FECHADA (oficial, números idênticos) + M5 pronta
- Run oficial da M4 reproduziu o sandbox dígito a dígito (47 passed; pipeline determinístico) → **`baseline-scb-v0.1` CONGELADO (D-17)**.
- M5: `simulate_league` (MC da temporada, fixtures derivadas, real travado, desempate D-18/Q-03), `predict_match` (porta da frente = backtest, D-34), `registrar` (imutável + settle ±2d + report power-aware), runbook [[Operacao BRA 2026]]. 3 testes (50 no total).
- E2E real BRA 2026 (rodada ~18): **Palmeiras 78,8% título · Flamengo 20,7% · Fluminense 0,4%; Chapecoense 100% Z4** — 5.000 sims em 3s, seed fixa.
- Q-02 fechada formalmente; Q-03 → Gustavo confirma ordem CBF; monitor de drift movido p/ M6/M7 (sem registros acumulados ainda, não há o que monitorar).

## 2026-07-16 (c) — M4: PORTÃO DO BASELINE PASSOU (sandbox; aguarda run oficial)
- `scb/backtest_harness.py`: walk-forward por temporada (burn-in 2), curva de empate POR FOLD (anti-vazamento), previsões on-the-fly, 4 réguas, Brier/LogLoss/RPS/ECE/banda, bootstrap pareado B=10k seed=12345 vetorizado. +5 testes (47 no total).
- **Resultados** ([[Backtest baseline (2026-07-16)]]): BRA n=4.736 Brier **0,6146** — bate uniforme (+0,0521), taxa-base (+0,0175) e Elo-puro (+0,0025), IC>0 em todos; E0 n=11.780 **0,5899** (+0,0767/+0,0530/+0,0052). Mercado (fechamento) à frente ~2pp nas duas — teto honesto. BRA > E0 em dificuldade, como a viabilidade previa. Banda sub-cobre extremos (padrão D-30 SCM) → M6. D-17 registrada.

## 2026-07-16 (b) — M3.4 (predictor) pronto: MOTOR COMPLETO aguardando run oficial
- `scb/predictor.py`: port fiel (piso conserva T_m D-22; propagação determinística por estratos D-30; A1; clamps; ensemble 0,56/0,44) com T_base POR LIGA (placeholder = medição M1) e leitura C1 via `draw_curve.ved_from_dr` (núcleo único D-43, ε do predictor). Fora: estilo/altitude/KO (D-06). Hooks: δ_ata (desfalques), perna AD com w_ad=0 (re-gate na liga, D-05). `MODEL_VERSION=scb-v0.1-baseline`.
- +8 testes (D-22, simetria, A1/btts matriz≡fechado, Jensen, determinismo, hook AD inerte, pipeline por liga com P(E) BRA>E0, idempotência/incremental). Harness **42/42**.
- E2E real: **18.200 previsões em 12,4s; soma=1 e bandas ok em 100%**; in-sample: BRA V 0,482/real 0,485 · E0 V 0,484/real 0,456 (H alto, já registrado) · over sobreprevisto +3-4pp (T_base, M6).
- Staleness do mount atrapalhou o harness (config.py velho) — contornado com injeção canônica; lição D-16 SCM reconfirmada.

## 2026-07-16 — M3.3 (curva de empate por liga) pronta
- `scb/draw_curve.py` (D-07): P_E(|dr|) empírica por liga do `match_ratings.dr` (PIT), bins com fusão por n≥200, interpolação linear, cap C1 e decomposição — P(V/E/D)∈[0,1] por construção; `--max-season` p/ o backtest reconstruir só com treino (anti-vazamento); freeze rastreável em `meta`.
- 6 testes novos (recupera taxa, soma=1 em dr∈[−800,800], interpolação, corte por temporada, roundtrip, **curvas diferem por liga**). Harness **34/34**.
- E2E real congelado: BRA n=5.496 (0,307→0,195) · E0 n=12.704 (0,296→0,148, cauda até |dr|~450). Nota honesta: diferença de ERA dentro da liga fica p/ o candidato C3.

## 2026-07-15 (g) — M3.1 FECHADA + M3.2 (features_pit) pronta
- M3.1 fechou no run oficial (21 passed; tops por liga conferidos).
- `scb/features_pit.py`: port com decay POR JOGO (liga é calendário denso), residual vs we (ajuste a adversário+mando), vol_mult (D-28), σ_ajuste=c·desvio, σ_dr RSS, modo incremental. Removidos: confed (D-06), glicko (D-05: re-propor só com ângulo novo), peso de amistoso (liga não tem).
- 7 testes novos — o portão do módulo é o **anti look-ahead** (jogo futuro não muda feature passada) + **incremental==full**. Harness 28/28.
- E2E real: 18.200 features em 20,8s; |forma| média 6,1 Elo; cap nunca furado; σ_dr méd 84 [40–283].

## 2026-07-15 (f) — M3.1 (elo_engine) pronto, aguarda run oficial
- `scb/config.py` (K/H por liga [a calibrar], SEASON_RHO=0 OFF) + `scb/elo_engine.py` (port: PIT em match_ratings, zero-sum, mando em todo jogo, hook C5 de virada de temporada no lugar do _revert de seleções) + 7 testes.
- Harness 21/21 (14 M2 + 7 novos). E2E real: 18.200 snapshots PIT, média 1500,00 exata por liga, 0,1s; tops fazem sentido (Palmeiras 1805/Flamengo 1765 · Arsenal 1893/City 1862).
- [medido p/ M6]: we_home médio 0,6191 vs pontuação real do mandante 0,5948 → H=100 sobreestima o mando de clube (calibrar no grid, não agora — baseline primeiro).

## 2026-07-15 (e) — M2 FECHADA (portão oficial passou)
- Run do Gustavo: `pytest -q` **14 passed em 0,19s** · `python -m scb.ingest` → **BRA 5.496 / E0 12.704** (aceite exato) · odds gravadas 11.150 (BRA, só close) + 27.400 (E0, open+close) · `dados/scb.sqlite` criado.
- M3 aberta: elo_engine → features_pit (+ curva de empate por liga) → predictor.

## 2026-07-15 (d) — M2 código pronto (aguarda run oficial do Gustavo)
- `scb/db.py` (schema liga: matches+league/season, odds_hist open/close, seasons, PIT pré-declaradas), `scb/ingest.py` (parser QA-01/02/03, idempotente, guarda ±2d, --dedup, extra), `scb/odds.py` (de-vig, blend ≤0,20, market_read com fallback D-16).
- 14/14 testes no harness isolado (sandbox sem PyPI → shim de pytest, mesma prática do SCM).
- E2E no snapshot real: **BRA 5.496 ✓ / E0 12.704 ✓** (bate o poc_m1_report), 2,2s; **BRA-2026: 177/177 jogos com fechamento via fallback** — Pinnacle morto não custa o CLV da temporada-alvo.
- Portão oficial da M2 = pytest + ingest na máquina do Gustavo.

## 2026-07-15 (c) — M1 FECHADA (portão passou)
- Run completo do Gustavo: BRA 5.497 jogos (2012–2026; 2016=379, interpretação Chapecoense a confirmar; 1 placar nulo em 2026), E0 12.704 (93/94+), **0 duplicatas / 0 aliases nas duas ligas**.
- Números-chave: BRA empate 26,8% / gols 2,40 · E0 moderno empate 18,7–24,5% / gols até 3,28 → curvas por liga confirmadas.
- **D-16:** Pinnacle closing 88% (2025) e 0% (2026) → benchmark de mercado por fallback PSC→AvgC→B365C. E0: fechamento completo desde 19/20; Pinnacle pré/close desde 12/13.
- M2 aberta (schema + ingest herdando parser + fixtures dos QA).

## 2026-07-15 (b) — M1 executada (em fechamento)
- Inventário estrutural do football-data com amostras reais: BRA desde 2012; **D-13: BRA.csv só traz FECHAMENTO** (corrige suposição do plano; nota no contrato §3.5, sem bump); E0 com abertura+fechamento+stats [medido].
- Criados: `scb_analytics/dados/notes.txt` (dicionário oficial versionado), `dados/leagues.json` v1, `scripts/poc_m1.py`, `dev/POC-M1-dados (2026-07-15).md`.
- D-14: Q-02 fechada (sem Kaggle; burn-in interno). D-15: layout `scb_analytics/` + dados versionados.
- Pendência única da M1: Gustavo rodar `poc_m1.py` (grades por temporada, duplicatas, aliases, empate/gols por era).
- 1º run do Gustavo achou **QA-01** (encoding latin-1 na E0 antiga) e **QA-02** (linhas de jogo descartadas em silêncio pelo parser); 2º run achou **QA-03** (header com colunas vazias/duplicadas → to_numeric quebrava). Corrigidos com parser determinístico via módulo `csv` (posição + descarte de coluna sem nome + sufixo em duplicata); **7/7 no harness isolado**. Re-run: `python scripts/poc_m1.py --offline`. Lição registrada: o ingest da M2 herda esse parser + os 7 casos como fixtures de teste.

## 2026-07-15
- **PLANO v1.0 e contrato SCB v1.0 CONGELADOS** — aprovação do Gustavo (D-11). Portão da Fase 1 passado.
- Vault adaptado ao Obsidian (D-12): wikilinks, frontmatter em todos os .md, `Indice.md` como nota-casa, `.obsidian/` mínimo, BACKLOG no formato do plugin Kanban.
- CONTEXT.md atualizado por substituição (estado: Fase 1 concluída → próximo M1).

## 2026-07-14
- Bootstrap do projeto (Fase 0–1). Kit criado a partir do estudo do zip `666666_SCM_DOCs` (contrato v5.0, D-01..D-85 SCM, viabilidade Brasileirão de 2026-06-28, busca de melhorias v3).
- Fonte football-data.co.uk verificada online (BRA.csv disponível, atualizado 2026-06-02 na página; página de 2026-07-06).
- Decisões de partida do Gustavo: port do scm_analytics (D-02), multi-liga E0+BRA (D-03), operar na temporada 2026 (D-10).
- D-01..D-10 registradas; Q-01..Q-03 abertas. PLANO.md escrito, **aguardando congelamento**.
