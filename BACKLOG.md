---
kanban-plugin: board
tags: [scb, backlog]
status: vivo
data: 2026-07-16
---

# BACKLOG — SCB

> Recriado em 2026-07-16 (o arquivo sumiu do vault — possivelmente plugin/limpeza; conteúdo reconstituído do estado corrente). Um card por entrega, com portão.

## ▶ Ações do Gustavo (agora)

- [ ] **[M6.7] Rebuild da v0.2 na SUA máquina** — `python -m pytest -q` (esperado **63**) → `python -m scb.elo_engine` → `python -m scb.features_pit` → `python -m scb.draw_curve` → `python -m scb.predictor` → `python -m scb.backtest_harness` (esperado **BRA 0,6131** / E0 0,5899) → `python -m scb.simulate_league --season 2026`
- [ ] **[OPERAÇÃO] Registrar a próxima rodada do BRA 2026 antes do kickoff** ([[Operacao BRA 2026]]) — toda rodada, sem exceção

## 🔜 Próximo

- [x] **[v0.4+M7] GUSTAVO: rebuild FEITO** — `scb-v0.4-sot-goals-e0` confirmado (85 testes; predictor 18200; backtest **BRA 0,6131 / E0 0,5894**). ▶ Pendente agora: registrar cada rodada · terminar o backfill de placar/posse do BRA (`baixar_stats_bra.py`, resumível — cota baixa/429) · `baixar_escudos_bra.py` (escudos oficiais)
- [ ] **[M7.2] Empacotamento final** — CHECKLIST de entrega (prompts/05): zip sem deps/segredos, README sincronizado, abrir e conferir
- [ ] **[evolução futura] Q-07 banda E0 (números na D-28) · Q-08: C4 viagem (curadoria de coordenadas) · C6 H por clube (pronto-para-rodar)**
- [x] **[M7.1] WEB ENTREGUE (D-29)** — estilo EA FC (nav lateral condensada, dark+vinheta, cards, trilho de temporada, barras animadas, placares em tiles); escudos SVG por cores reais + override local `static/logos/`; 3 telas + launcher; badges com 5 testes (71); Flask lazy (roda sem Flask nos testes)
- [x] **[M7.1b] Feedback do usuário aplicado** — QA-04 contraste dos chips (sólidos, texto escuro no volt); `scripts/baixar_escudos.py` (PNGs reais, uso pessoal — VOCÊ roda); Imprimir/PDF + Copiar resumo nas telas de confronto e tabela (D-30)

## ✅ Fila da E0 fechada em 2026-07-16

- [x] **Q-04 EXECUTADA (D-26): mando rolling na E0 → `scb-v0.3-mando-e0`** — E0 0,5894 (ECE 0,0290, gap mercado −0,0156); BRA intacto; δ −41,5 Elo embutido (2023+); +3 testes (66)
- [x] **Q-05 FECHADA (D-27): DC rejeitado no 2º gate** — ganho do empate dilui no ensemble (eco D-39 SCM); `dc_rho` fica OFF no predictor
- [x] **Banda MEDIDA (D-28)**: σ×1,3 → E0 8/10 faixas (+29% largura), BRA neutro → Q-07

## ✅ Feito (resumo — detalhe no CHANGELOG e DECISIONS)

- [x] **M0–M1**: kit + vault Obsidian; POC de dados (D-13 BRA só fechamento; D-14 sem Kaggle; D-16 fallback odds; QA-01/02/03 do parser)
- [x] **M2**: schema + ingest + odds — oficial: BRA 5.496 / E0 12.704 (14 testes)
- [x] **M3**: motor completo — elo (PIT, zero-sum), features (anti look-ahead), curva de empate POR LIGA (D-07), predictor (D-22, propagação determinística) — 42 testes
- [x] **M4**: PORTÃO DO BASELINE PASSOU (D-17): BRA 0,6146 / E0 0,5899 vs 4 réguas, walk-forward com curva por fold
- [x] **M5**: simulate_league (D-18) + predict_match (D-34) + registrar imutável + runbook; Q-03 fechada (ordem CBF confirmada)
- [x] **M6.1–M6.6 (fila do portão)**: estático H/T_base ✗✗ (D-19) · drift gols ✗✗ (D-20) · mando rolling ✓E0/✗BRA (D-21) · descanso ✗✗ (D-22) · Dixon-Coles ✓E0-empate/✗BRA (D-23) · **regressão de temporada ✓BRA/✗E0 (D-24)**
- [x] **M6.7: 1ª ADOÇÃO — `scb-v0.2-rho-bra` (D-25)**: BRA 0,6146→0,6131, ECE 0,0224, gap mercado −0,0180; E0 idêntica (isolamento por liga); sim 2026 antes/depois registrada
