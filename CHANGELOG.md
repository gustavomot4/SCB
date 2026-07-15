---
tags: [scb, changelog, historico]
status: vivo
tipo: log
---

# CHANGELOG — SCB

> Log datado, append-only. **Não é carregado nas sessões** (o presente mora no CONTEXT.md). Uma linha por evento relevante; detalhe fica no commit/D-NN.

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
