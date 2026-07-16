---
tags: [scb, changelog, historico]
status: vivo
tipo: log
---

# CHANGELOG — SCB

> Log datado, append-only. **Não é carregado nas sessões** (o presente mora no CONTEXT.md). Uma linha por evento relevante; detalhe fica no commit/D-NN.

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
