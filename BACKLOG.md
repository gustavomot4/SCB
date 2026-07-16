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

## 🔜 Fila de evolução (1 por sessão, cada um com portão)

- [ ] **Q-04: adoção do mando rolling na E0** (D-21) — wiring por liga + gate de confirmação
- [ ] **Q-05: adoção do Dixon-Coles na E0** (D-23) — exige 2º gate (re-blend do 1X2)
- [ ] **C4 viagem/distância** (coordenadas estáticas R$0; σ primeiro) — portão
- [ ] **C6 H por clube** (shrinkage forte obrigatório) — portão
- [ ] **Banda/σ_dr** (sub-cobre extremos — D-17) — portão de cobertura
- [ ] **[M7] Web + empacotamento** (telas: prever/tabela/prospectivo; CHECKLIST de entrega; prompts/05)

## ✅ Feito (resumo — detalhe no CHANGELOG e DECISIONS)

- [x] **M0–M1**: kit + vault Obsidian; POC de dados (D-13 BRA só fechamento; D-14 sem Kaggle; D-16 fallback odds; QA-01/02/03 do parser)
- [x] **M2**: schema + ingest + odds — oficial: BRA 5.496 / E0 12.704 (14 testes)
- [x] **M3**: motor completo — elo (PIT, zero-sum), features (anti look-ahead), curva de empate POR LIGA (D-07), predictor (D-22, propagação determinística) — 42 testes
- [x] **M4**: PORTÃO DO BASELINE PASSOU (D-17): BRA 0,6146 / E0 0,5899 vs 4 réguas, walk-forward com curva por fold
- [x] **M5**: simulate_league (D-18) + predict_match (D-34) + registrar imutável + runbook; Q-03 fechada (ordem CBF confirmada)
- [x] **M6.1–M6.6 (fila do portão)**: estático H/T_base ✗✗ (D-19) · drift gols ✗✗ (D-20) · mando rolling ✓E0/✗BRA (D-21) · descanso ✗✗ (D-22) · Dixon-Coles ✓E0-empate/✗BRA (D-23) · **regressão de temporada ✓BRA/✗E0 (D-24)**
- [x] **M6.7: 1ª ADOÇÃO — `scb-v0.2-rho-bra` (D-25)**: BRA 0,6146→0,6131, ECE 0,0224, gap mercado −0,0180; E0 idêntica (isolamento por liga); sim 2026 antes/depois registrada
