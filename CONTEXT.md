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
**MODELO OFICIAL: `scb-v0.3-mando-e0`** (D-17 baseline + adoções D-25 ρ=0,30 no BRA e D-26 mando rolling na E0). M4 walk-forward: **BRA 0,6131 · E0 0,5894 (ECE 0,0224/0,0290)**; mercado ~2pp à frente (régua, não meta). Fila de evolução: 9 gates, 2 adoções, 7 rejeições com números (D-19..D-27); abertas Q-07 (banda E0, números na D-28) e Q-08 (C4 exige coordenadas; C6 pronto-para-rodar). **M0–M7.1 EXECUTADAS** — pipeline dados→Elo→features→curvas→predictor→backtest→simulador→registro + **web estilo EA FC** (3 telas, escudos com override local, imprimir/copiar) + **operação em 1 clique** (`fixtures.csv` 1x/temporada + "Registrar rodada"/`registrar auto` agendável; settle liquida adiados — D-31). Testes: **73**. **Pendências:** registrar toda rodada do BRA 2026 ([[Operacao BRA 2026]]) · escudos manuais do BRA (`dados/escudos-pendentes.md`, 16 arquivos) · **M7.2 empacotamento** (prompts/05 + CHECKLIST) · Q-07/Q-08 na próxima sessão de evolução.

## Mapa (contexto mínimo por sessão)
Regras: [[REGRAS-DE-NEGOCIO]] · Contrato matemático: [[MODELO-MATEMATICO]] · Port/lições: [[HERANCA-SCM]] · Dados/schema: [[DADOS]] · Plano: [[PLANO]] · Decisões: [[DECISIONS]] · Tarefas: [[BACKLOG]] · Aceite: [[CHECKLIST]]
**Ciclo de sessão:** prompt do papel (`prompts/`) + este CONTEXT.md + **só o arquivo do momento** → pedir **delta** → passar no portão → registrar D-NN/QA-NN → atualizar aqui por substituição.
