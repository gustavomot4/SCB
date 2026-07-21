---
tags: [projeto, contexto, scb]
status: atual
tipo: contexto
data: 2026-07-21
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
**MODELO OFICIAL: `scb-v0.4-sot-goals-e0`** (D-17 baseline + D-25 ρ=0,30 no BRA + D-26 mando rolling na E0 + **D-33/D-35 SoT-total desacoplado no canal de gols da E0** — só over2.5/BTTS; 1X2/placar intocados). **Rebuild FEITO** (run do Gustavo: **85 testes verdes**, backtest confirmado). 1X2 walk-forward: **BRA 0,6131 · E0 0,5894** (ECE 0,0224/0,0290); over/BTTS da E0 melhoram (D-33: Δ+0,00133 IC[+0,00058,+0,00210]). Mercado à frente (régua, não meta): o modelo fecha **78% (E0) / 50% (BRA)** da distância taxa-base→mercado — agora VISÍVEL na aba **Calibração** (D-39). Evolução: D-19..D-35 (2 adoções, SoT-diferencial rejeitado D-32, SoT-total adotado D-33/35); abertas **Q-01** (peso do mercado no ensemble — números na Calibração), Q-07 (banda E0, D-28), Q-08 (C4 coordenadas / C6 pronto). **M0–M7.1 executadas** — pipeline dados→Elo→features→curvas→predictor→backtest→simulador→registro + **web estilo EA FC (5 telas)**: Prever Confronto · Tabela (**Simulada + Classificação real** D-38) · **Calibração** D-39 · Jogos · Prospectivo — + **operação em 1 clique** (`fixtures.csv` com o BRA 2026 inteiro, rodadas 19-38, D-38; "Registrar rodada"/`registrar auto`; settle D-31). **2ª fonte API-Futebol (D-34/D-36)**: traz stats **e resultados** do BRA — como o football-data não publicou julho, a API preenche `matches` e **destrava o settle**; escudos oficiais do BRA via CDN (D-37 — `escudos-pendentes.md` obsoleto). Artilharia foi construída e **cortada** (D-40, exibição sem valor preditivo). **Pendências:** registrar toda rodada do BRA 2026 ([[Operacao BRA 2026]]) · terminar o backfill de placar/posse do BRA nos dias grátis da API (cota baixa → 429; o fetcher é resumível e self-healing) · **M7.2 empacotamento** (prompts/05 + CHECKLIST) · Q-01/Q-07/Q-08 na próxima sessão de evolução.

## Mapa (contexto mínimo por sessão)
Regras: [[REGRAS-DE-NEGOCIO]] · Contrato matemático: [[MODELO-MATEMATICO]] · Port/lições: [[HERANCA-SCM]] · Dados/schema: [[DADOS]] · Plano: [[PLANO]] · Decisões: [[DECISIONS]] · Tarefas: [[BACKLOG]] · Aceite: [[CHECKLIST]]
**Ciclo de sessão:** prompt do papel (`prompts/`) + este CONTEXT.md + **só o arquivo do momento** → pedir **delta** → passar no portão → registrar D-NN/QA-NN → atualizar aqui por substituição.
