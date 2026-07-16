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
- [x] **[M0→M1] Congelar PLANO.md + contrato** — ✅ aprovado pelo Gustavo em 2026-07-15 (D-11); vault adaptado ao Obsidian (D-12)

## 🔜 Próximo (M3 — motor, 1 módulo por vez)

- [ ] **[M3.2] ▶ GUSTAVO: `python -m pytest -q` (esperado 28 passed) + `python -m scb.features_pit`** (~20–40s) — *aceite oficial* dos módulos 1+2
- [x] **[M3.1] Port `elo_engine` + `config.py`** — ✅ FECHADA (run oficial: 21 passed; tops conferidos a olho). Observação p/ M6: we_home 0,619 vs real 0,595 → H=100 alto p/ clube [medido]
- [x] **[M3.2] Port `features_pit`** — forma com decay POR JOGO, vol_mult D-28, σ_dr RSS, incremental; sem confed/glicko/amistoso; 7 testes novos incl. **anti look-ahead** e **incremental==full**; **E2E real: 18.200 features em 20,8s, cap ±30 intacto, σ_dr 39,7–283**
- [x] **[M3.3] Curva de empate POR LIGA (D-07)** — `scb/draw_curve.py`: bins de |dr| com fusão por n mínimo, interpolação, cap `2·min(we,1−we)−ε`, decomposição C1; **`max_season` p/ o harness reconstruir por fold (anti-vazamento)**; freeze em meta com versão. 6 testes; harness 34/34; **E2E real: BRA 0,307→0,195 e E0 0,296→0,148 por |dr|, congeladas**. *Nota:* era dentro da liga (E0 anos 90 empatadores) é papel do C3, não da curva
- [ ] **[M3.4] Port `predictor`** (f/g(dr), Poisson, perna AD, ensemble; consistência produção↔backtest) — *aceite:* soma=1, piso conserva T_m, E2E nas 2 ligas

## ✅ M2 — FECHADA em 2026-07-15 (portão passou na máquina do Gustavo)

- [x] **[M2] Run oficial:** `pytest` **14 passed** + ingest **BRA 5.496 ✓ / E0 12.704 ✓** (odds 11.150 + 27.400)

- [x] **[M2] `scb/db.py` + `scb/ingest.py` + `scb/odds.py`** — port do SCM: schema com league/season/odds open-close/seasons; parser QA-01/02/03; idempotência; guarda ±2d; `--dedup`; extra; de-vig + fallback D-16
- [x] **[M2] 14 testes** (parser, datas 2/4 dígitos, idempotência, anti-nulo, guarda, dedup, odds por estágio, fallback, seasons, de-vig, blend) — 14/14 no harness isolado
- [x] **[M2] E2E no snapshot real (sandbox):** BRA **5.496** ✓ · E0 **12.704** ✓ · 2,2s · **BRA-2026 com fechamento em 177/177 via fallback D-16** (CLV da temporada-alvo garantido)

## ✅ M1 — FECHADA em 2026-07-15 (portão passou)

- [x] **[M1] Run do inventário completo (Gustavo)** — BRA 2012–2026 (5.497), E0 93/94+ (12.704), 0 dup/0 alias; achado: Pinnacle 0% em 2026 → D-16 (fallback). 3 QA de parser achados e corrigidos (7/7 harness)

- [x] **[M1] Inventário estrutural BRA + E0** — headers/colunas medidos de amostras reais; achado D-13 (BRA só fechamento); BRA desde 2012; `notes.txt` versionado. Ver [[POC-M1-dados (2026-07-15)]]
- [x] **[M1] `leagues.json` v1** — BRA + E0 com campos [confirmar] explícitos (`scb_analytics/dados/leagues.json`)
- [x] **[M1] Q-02 decidida (D-14)** — sem Kaggle; burn-in interno 2012–13
- [x] **[M1] Script do inventário completo** — `scb_analytics/scripts/poc_m1.py` (download + grades por temporada + duplicatas ±3d + aliases + empate/gols por era)

## 📋 Fila (M2–M7, na ordem)

- [ ] **[M2] Schema SQLite + ingest football-data parametrizado** (idempotente, guarda ±2d, `resultados_extra`, `--dedup`) — *aceite:* migration roda; contagens batem; pytest do módulo verde
- [ ] **[M3] Port elo_engine** (K por liga [a calibrar], PIT, hook de temporada) — *aceite:* testes PIT/zero-sum/idempotência verdes na E0
- [ ] **[M3] Port features_pit** (forma decay por jogo, H_liga, σ_dr; sem confed/altitude) — *aceite:* anti look-ahead verde
- [ ] **[M3] Port predictor + curva de empate DA LIGA + perna AD + ensemble** — *aceite:* soma=1, piso conserva T_m, consistência produção↔backtest; E2E na E0
- [ ] **[M4] Harness walk-forward por temporada + 4 réguas; backtest E0 → BRA** — *aceite:* **portão do baseline** (Brier < uniforme e < taxa-base, IC não cruza zero); congela `baseline-scb-v0.1`
- [ ] **[M5] Simulador de pontos corridos** (P título/G4/G6/Z4; desempate por liga; real trava sim) — *aceite:* invariantes nos testes; Q-03 resolvida
- [ ] **[M5] Registrar/monitor/report adaptados + runbook da rodada** — *aceite:* rodada de teste completa (registrar → settle → report → monitor/CLV)
- [ ] **[M5] ▶ Começar registro prospectivo do BRA 2026** (toda rodada, sem exceção — lição do SCM: 19/81 é auditoria fraca)
- [ ] **[M6] Calibrar H/K/θ/κ/T_base + curvas por liga** — *aceite:* grid no treino, validação walk-forward, congelado por versão. *Insumos já medidos:* T_base BRA ≈ 2,40 ≠ 2,6 da Copa (M1); we_home 0,619 vs real 0,595 com H=100 → H de liga é menor (M3.1)
- [ ] **[M6] Fila do portão C1–C6** (descanso, Dixon-Coles, drift de gols, viagem, regressão de temporada, H por clube) — *aceite:* um por vez; IC>0 + guardas + kill-switch; rejeição vira D-NN
- [ ] **[M7] Web adaptada** (prever jogo, tabela simulada, prospectivo, monitor) + launcher — *aceite:* QA adversarial sem crítico/alto aberto
- [ ] **[M7] Empacotamento** — *aceite:* CHECKLIST.md completo (zip sem deps/segredos, aberto e conferido)
