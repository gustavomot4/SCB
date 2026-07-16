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

- [ ] **[M3.4] ▶ GUSTAVO: `python -m pytest -q` (esperado 42 passed) + `python -m scb.predictor`** (~15-30s; esperado 18200 previsões) — fecha o MOTOR inteiro (M3)
- [x] **[M3.4] Port `predictor`** — f/g(dr) com T_base POR LIGA (config, medido M1), piso conserva T_m (D-22), Poisson-condicional (A1), Elo-direto propagado por estratos determinísticos (D-30) com a curva DA LIGA via núcleo único (D-43), ensemble 0,56/0,44 com clamps, hooks δ_ata e perna AD (w_ad=0 até o portão — D-05), `MODEL_VERSION=scb-v0.1-baseline`; 8 testes. Harness **42/42**; **E2E real: 18.200 previsões/12,4s, 0 violações; 1ª olhada: BRA V 0,482 vs real 0,485; desvios de H/T_base visíveis e esperados (M6)**
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
- [ ] **[M4] ▶ GUSTAVO: `python -m pytest -q` (esperado 47 passed) + `python -m scb.backtest_harness`** (~30-60s) — run oficial que congela `baseline-scb-v0.1` (D-17)
- [x] **[M4] Harness walk-forward + 4 réguas — PORTÃO PASSOU (sandbox)**: BRA 0,6146 bate uniforme +0,0521 / taxa-base +0,0175 / Elo-puro +0,0025, todos IC>0; E0 0,5899 idem (+0,0767/+0,0530/+0,0052); mercado à frente ~2pp (teto declarado); ECE 0,029/0,037; banda sub-cobre extremos (→M6). 5 testes; curva por fold anti-vazamento. Ver [[Backtest baseline (2026-07-16)]]
- [ ] **[M5] ▶ GUSTAVO: `pytest -q` (esperado 50 passed) + `python -m scb.simulate_league --season 2026` + confirmar Q-03 no regulamento CBF** — fecha a M5
- [ ] **[M5] ▶ OPERAÇÃO: registrar a PRÓXIMA rodada do BRA 2026** (runbook: [[Operacao BRA 2026]]) — toda rodada, sem exceção (lição 19/81 do SCM)
- [x] **[M5] `simulate_league`** — fixtures derivadas do turno-returno, real travado, desempate parametrizado (D-18; Q-03 [confirmar]), seed fixa; invariantes testados; **E2E real BRA 2026: Palmeiras 78,8% título / Flamengo 20,7% / Chape 100% Z4, 5000 sims/3s**
- [x] **[M5] `predict_match` (porta da frente, produção=backtest D-34) + `registrar` (imutável, settle ±2d, report power-aware)** — 3 testes; runbook escrito. *Monitor de drift (D-76) → M6/M7: precisa de registro ACUMULADO para ter n*
- [x] **[M6.1] Grid estático H/T_base — REJEITADO pelo portão (D-19)** — `scb/calibrate.py` (era de calibração vs era de validação): candidato piora gols IC<0; regime inverteu entre eras (mando pós-COVID ↓, gols ↑). Baseline v0.1 mantido. *Rodar E0 na máquina do Gustavo p/ completar o registro (`python -m scb.calibrate --league E0`)*
- [x] **[M6.2] C3 drift PIT de gols — REJEITADO (D-20)** — `scb/drift.py` + 3 testes: IC cruza zero nas 2 ligas; kill-switch limpo; flag `USE_MKT_DRIFT=False` permanece. Lista-morta com números. *Q-03 fechada (ordem CBF confirmada — bate com a D-18)*
- [x] **[M6.3] Mando rolling PIT — PASSA na E0 (1º ✅ da fila!), rejeitado no BRA (D-21)** — `scb/mando_rolling.py` + 3 testes (56 no total); E0: 1X2 +0,00180 IC>0, δ vigente −36,8 Elo; **Q-04 aberta: Gustavo decide a adoção (wiring + bump v0.2 + re-run M4)**
- [x] **[M6.4] C1 descanso intra-liga — REJEITADO nas 2 ligas (D-22)** — `scb/descanso.py` + 3 testes (59): rodadas simétricas dentro da liga (\|diff\| ~0,7d); re-teste só com calendário externo grátis
- [ ] **[M6] Fila restante: C2 Dixon-Coles · C4 viagem · C5 regressão de temporada · C6 H por clube · banda/σ_dr (sub-cobre extremos, D-17) · Q-04 (adoção mando rolling E0)** — um por vez, cada um com portão
- [ ] **[M6] Fila do portão C1–C6** (descanso, Dixon-Coles, drift de gols, viagem, regressão de temporada, H por clube) — *aceite:* um por vez; IC>0 + guardas + kill-switch; rejeição vira D-NN
- [ ] **[M7] Web adaptada** (prever jogo, tabela simulada, prospectivo, monitor) + launcher — *aceite:* QA adversarial sem crítico/alto aberto
- [ ] **[M7] Empacotamento** — *aceite:* CHECKLIST.md completo (zip sem deps/segredos, aberto e conferido)
