---
tags: [scb, plano, fase1, congelado]
status: CONGELADO (aprovado pelo Gustavo em 2026-07-15 — D-11)
tipo: planejamento
data: 2026-07-15
---

# PLANO.md — SCB v1.0

> Fase 1 do pipeline. **Este plano está CONGELADO** (D-11): mudança de rumo vira D-NN novo, não replanejamento do zero. Contexto: [[CONTEXT]]. Contrato matemático detalhado: [[MODELO-MATEMATICO]] (congelado junto, como contrato SCB v1.0).

## 1. Resumo executivo (5 linhas)
Port evoluído do SCM para ligas de pontos corridos, **multi-liga por configuração**: a Premier League (E0, dado rico/longo) valida o port; o **Brasileirão (BRA) é a entrega**. O núcleo Elo→Poisson→ensemble transfere intacto (formas fixas, coeficientes recalibrados por liga); sai o que é de Copa (altitude, confederação, mata-mata); entra o que é de liga (mando central, curva de empate por liga, simulador de tabela, temporadas/promovidos, **odds automáticas com fechamento** — a maior melhoria estrutural, que torna CLV e benchmark de mercado automáticos). Meta de operação: registro prospectivo imutável ainda na temporada 2026 do Brasileirão, **depois** do baseline validado por backtest.

## 2. Arquitetura (módulos e contratos entre eles)

```
leagues.json (config por liga)
      │
ingest (football-data, parametrizado; idempotente + guarda ±2d + resultados_extra)
      │           → SQLite: matches(league, season), odds_hist(open/close)
elo_engine (K por liga; PIT em match_ratings; hook de virada de temporada)
      │
features_pit (dr_adj = elo + forma + H_liga; σ_dr; anti look-ahead)
      │
predictor (λ = f/g(dr); Poisson; curva de empate DA LIGA; perna AD; ensemble c/ mercado ≤0,20)
      │           → predictions (versionado por MODEL_VERSION)
      ├─ backtest_harness (walk-forward por temporada; 4 réguas: uniforme, taxa-base, Elo-puro, mercado)
      ├─ simulate_league (MC da temporada → P(título/G4/G6/Z4); desempate por liga; real trava simulação)
      ├─ registrar (imutável) + monitor (drift power-aware + CLV vs fechamento) + report (por rodada/temporada)
      └─ web (prever jogo · tabela simulada · prospectivo · monitor)
```
Contratos-chave: `predictions` é a interface única entre motor e consumidores (harness/sim/web); `match_ratings`/`match_features` são point-in-time e ninguém escreve nelas fora do pipeline; toda curva empírica congelada (empate, reliab) carimba `MODEL_VERSION` em `meta`.

## 3. Milestones e portões (cada M só abre com o portão da anterior)

| M | Entrega | Portão de aceite |
|---|---|---|
| **M0** | Kit de contexto (este) | CONTEXT.md ≤1 pág; critério de aceite escrito ✅ |
| **M1** | **POC de dados**: download E0+BRA, inventário (temporadas, colunas, odds de fechamento, qualidade), `leagues.json`, decisão do aquecimento Kaggle | inventário respondendo às 5 perguntas de [[DADOS]]; D-NNs registrados |
| **M2** | **Schema + ingest** parametrizado por liga (com dedup, extra, idempotência) | migration roda; contagens batem com a fonte; `pytest` do módulo verde (idempotência + guarda ±2d + anti-nulos) |
| **M3** | **Port do motor**: elo_engine → features_pit → predictor (curva de empate da liga, perna AD, ensemble) — 1 módulo por vez, por delta | testes por módulo (PIT/anti look-ahead, soma=1, piso conserva T_m, consistência produção↔backtest); pipeline E2E roda na E0 |
| **M4** | **Backtest baseline**: harness walk-forward, 4 réguas, primeiro na **E0**, depois **BRA** | **Brier < uniforme E < taxa-base com IC que não cruza zero (por liga)**; ECE e cobertura de banda reportados; distância ao mercado reportada. Congela `baseline-scb-v0.1` |
| **M5** | **Simulador de liga** + registrar/monitor/report adaptados | invariantes (Σposições=1 por clube, Σtítulo=1, real travado); runbook da rodada escrito; registro prospectivo do BRA 2026 **começa aqui** |
| **M6** | **Calibração + fila do portão**: H, K, θ/κ/T_base, curva de empate; depois candidatos C1–C6 um a um | cada adoção com IC>0 + guardas + kill-switch; rejeição registrada como D-NN (memória) |
| **M7** | **Web + entrega**: telas adaptadas, launcher, CHECKLIST de empacotamento | QA adversarial (prompts/03) sem achado crítico/alto aberto; zip sem deps/segredos; `pytest` completo verde na máquina do Gustavo |

Ordem M4→M5 é deliberada: operar o BRA 2026 (M5) só depois do baseline validado (regra "baseline primeiro"). M6 corre em paralelo à operação — evolução gateada enquanto o registro prospectivo acumula.

## 4. Decisões já tomadas (resumo — detalhe em [[DECISIONS]])
Port do `scm_analytics` (D-02) · multi-liga desde o dia 1, E0 valida/BRA entrega (D-03) · football-data como fonte primária (D-04) · lista-morta re-gateia (D-05) · termos de Copa OFF (D-06) · curva de empate por liga (D-07) · walk-forward por temporada (D-08) · teto de mercado 0,20 mantido, Q-01 aberta (D-09) · alvo temporada 2026 em andamento (D-10).

## 5. Riscos e mitigações (top 6)
1. **Bug de port silencioso** → validar na E0 antes do BRA (isola port de dificuldade da liga); teste de skill-regression herdado.
2. **Histórico curto do BRA.csv** → M1 mede; mitigação candidata: aquecer Elo com Kaggle (decisão D-NN com evidência).
3. **Liga equilibrada, edge pequeno** → expectativa declarada no contrato §5; as 4 réguas mantêm a honestidade (bater uniforme/taxa-base é o portão; mercado é régua, não meta).
4. **Cold start de promovidos** distorce começo de temporada → σ_R alto + prior manual; medir Brier das primeiras rodadas separadamente (portão do C5).
5. **Lag semanal da fonte na rodada** → `resultados_extra.csv` manual (D-80) + guarda anti-duplicata (D-82) herdados.
6. **Escopo crescer (mercados de cartão/escanteio, xG, outras ligas)** → lacunas declaradas no contrato; nada entra sem dado grátis + portão.

## 6. Fora de escopo da V1 (declarado)
Cartões/escanteios e tempo do gol (sem dado no BRA) · xG (sem fonte grátis) · Série B/estaduais/Libertadores como ligas previstas (só calendário-contexto futuro, C1 fase 2) · apostas/staking (não é ferramenta de lucro) · qualquer API paga.
