---
kanban-plugin: board
tags: [scb, backlog]
status: vivo
data: 2026-07-14
---

# BACKLOG — SCB

> Um card por entrega, com portão de aceite. Mover entre lanes; não apagar histórico (concluído fica em ✅).

## ✅ Concluído

- [x] **[M0] Bootstrap do kit de contexto** — CONTEXT/PLANO/DECISIONS/contexto/* criados a partir do estudo do vault SCM (2026-07-14)

## 🔴 Bloqueado (aguardando Gustavo)

- [ ] **[M0→M1] Congelar PLANO.md + contrato** — *aceite:* Gustavo aprova; ajustes viram delta no próprio doc; a partir daí mudança de rumo = D-NN

## 🔜 Próximo (M1 — POC de dados)

- [ ] **[M1] Baixar e inventariar `new/BRA.csv` + `E0.csv` (últimas ~10 temporadas) + `notes.txt`** — *aceite:* responde as 5 perguntas de `contexto/DADOS.md` (temporadas, colunas, fechamento desde quando, qualidade, empate/gols por era)
- [ ] **[M1] `leagues.json` v1** (BRA + E0: arquivo/URL, nº clubes, vagas, desempate, janela da temporada) — *aceite:* schema do config validado
- [ ] **[M1] Decidir Q-02 (aquecimento Kaggle)** — *aceite:* D-NN com evidência

## 📋 Fila (M2–M7, na ordem)

- [ ] **[M2] Schema SQLite + ingest football-data parametrizado** (idempotente, guarda ±2d, `resultados_extra`, `--dedup`) — *aceite:* migration roda; contagens batem; pytest do módulo verde
- [ ] **[M3] Port elo_engine** (K por liga [a calibrar], PIT, hook de temporada) — *aceite:* testes PIT/zero-sum/idempotência verdes na E0
- [ ] **[M3] Port features_pit** (forma decay por jogo, H_liga, σ_dr; sem confed/altitude) — *aceite:* anti look-ahead verde
- [ ] **[M3] Port predictor + curva de empate DA LIGA + perna AD + ensemble** — *aceite:* soma=1, piso conserva T_m, consistência produção↔backtest; E2E na E0
- [ ] **[M4] Harness walk-forward por temporada + 4 réguas; backtest E0 → BRA** — *aceite:* **portão do baseline** (Brier < uniforme e < taxa-base, IC não cruza zero); congela `baseline-scb-v0.1`
- [ ] **[M5] Simulador de pontos corridos** (P título/G4/G6/Z4; desempate por liga; real trava sim) — *aceite:* invariantes nos testes; Q-03 resolvida
- [ ] **[M5] Registrar/monitor/report adaptados + runbook da rodada** — *aceite:* rodada de teste completa (registrar → settle → report → monitor/CLV)
- [ ] **[M5] ▶ Começar registro prospectivo do BRA 2026** (toda rodada, sem exceção — lição do SCM: 19/81 é auditoria fraca)
- [ ] **[M6] Calibrar H/K/θ/κ/T_base + curvas por liga** — *aceite:* grid no treino, validação walk-forward, congelado por versão
- [ ] **[M6] Fila do portão C1–C6** (descanso, Dixon-Coles, drift de gols, viagem, regressão de temporada, H por clube) — *aceite:* um por vez; IC>0 + guardas + kill-switch; rejeição vira D-NN
- [ ] **[M7] Web adaptada** (prever jogo, tabela simulada, prospectivo, monitor) + launcher — *aceite:* QA adversarial sem crítico/alto aberto
- [ ] **[M7] Empacotamento** — *aceite:* CHECKLIST.md completo (zip sem deps/segredos, aberto e conferido)
