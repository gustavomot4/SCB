---
tags: [projeto, contexto, scb]
status: atual
tipo: contexto
data: 2026-07-15
---

# CONTEXT.md — SCB (Sistema Campeonato Brasileiro)

> **Teto: 1 página.** Atualizar **por substituição** (reescrever "Estado atual"); o datado vai para o [[CHANGELOG]]. Histórico NÃO mora aqui.

## Objetivo (3 linhas)
Sistema **local e gratuito** que prevê partidas do **Brasileirão Série A** (e ligas configuráveis) entregando **P(V/E/D), gols esperados, mercados derivados, confiança e simulação da tabela** (título/G4/G6/Z4) — nunca certezas.
É o **port evoluído do SCM** (Copa 2026): mesmo motor auditável Elo → Poisson → ensemble, **validado por backtest antes de qualquer uso**.
**Não é ferramenta de aposta**; o mercado é benchmark, não alvo de lucro.

## Regras de negócio inegociáveis (herdadas do SCM — detalhe: [[REGRAS-DE-NEGOCIO]])
1. **R$ 0** — sem API/base/hospedagem paga. 2. **Roda local** — nada lê a internet no cálculo (snapshot em disco). 3. **Probabilidades, nunca certezas**. 4. **Registro pré-jogo imutável**. 5. **Não inventar dados** — lacuna declarada fica declarada. 6. **Sem ML/boosting/bayes hierárquico**. 7. **Portão de backtest** — nenhum termo entra em λ/dr sem ΔBrier pareado com IC que não cruza zero.

## Restrições da stack (perfil dados-python)
Python 3.11+ · NumPy/pandas · **SQLite** (sem enum nativo; `natural_key` + guarda anti-duplicata ±2 dias) · pytest (**teste anti look-ahead obrigatório**) · Flask local · argparse · venv com `requirements.txt` de teto de major · bootstrap vetorizado (numpy) · nomes de time no padrão **football-data (EN)** · Monte Carlo com seed fixa.

## Critério de aceite (portões — definidos no dia 1)
- **Código:** `pytest -q` verde + teste PIT/anti look-ahead do módulo + ingest idempotente.
- **Modelo:** backtest **walk-forward por temporada**, Brier < uniforme **e** < taxa-base da liga, com IC bootstrap (B=10k, seed fixa) que não cruza zero; ECE e cobertura de banda reportados; comparação honesta vs mercado de-vigged (abertura **e fechamento**).
- **Termo novo:** ΔBrier pareado IC>0 no canal afetado + guardas de não-regressão (1X2/over/BTTS/ECE) + kill-switch de correlação com `dr` (corr < 0,95).
- **Docs:** este arquivo ≤ 1 página; decisão nova = **D-NN** no [[DECISIONS]]; bug = **QA-NN** citado no commit.

## Estado atual
Plano e contrato **congelados** (D-11). M1 e **M2 FECHADAS** (2026-07-15; portão oficial na máquina do Gustavo: pytest 14 passed; ingest BRA 5.496 / E0 12.704; `dados/scb.sqlite` pronto com odds open/close e fallback D-16 — BRA-2026 com fechamento 177/177). Fatos da liga [medidos]: BRA empate 26,8% / gols 2,40; E0 regime distinto → curvas por liga (D-07). Baseline `scb-v0.1` (D-17: BRA 0,6146 / E0 0,5899). **Fila do portão: 3 testados** — M6.1 estático (D-19 ✗) · M6.2 drift gols/C3 (D-20 ✗) · **M6.3 mando rolling: PASSA na E0 (D-21 — 1º ✅ do projeto: 1X2 +0,0018 IC>0, δ −36,8 Elo), rejeitado no BRA**. **Q-04 aberta (Gustavo): adotar na E0?** (wiring + bump v0.2 + re-run M4; BRA não muda). Q-03 fechada. Testes: 56. **Operação = prioridade nº 1:** registrar toda rodada do BRA 2026 ([[Operacao BRA 2026]]). M6.4 C1 descanso intra-liga: **rejeitado nas 2 ligas (D-22** — rodadas simétricas; re-teste exige calendário externo). Testes: 59. Fila restante: C2 Dixon-Coles · C4 viagem · C5 regressão de temporada · C6 H por clube · banda/σ_dr · Q-04. Depois M7 (web + empacotamento).

## Mapa (contexto mínimo por sessão)
Regras: [[REGRAS-DE-NEGOCIO]] · Contrato matemático: [[MODELO-MATEMATICO]] · Port/lições: [[HERANCA-SCM]] · Dados/schema: [[DADOS]] · Plano: [[PLANO]] · Decisões: [[DECISIONS]] · Tarefas: [[BACKLOG]] · Aceite: [[CHECKLIST]]
**Ciclo de sessão:** prompt do papel (`prompts/`) + este CONTEXT.md + **só o arquivo do momento** → pedir **delta** → passar no portão → registrar D-NN/QA-NN → atualizar aqui por substituição.
