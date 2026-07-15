---
tags: [projeto, contexto, scb]
status: atual
tipo: contexto
data: 2026-07-14
---

# CONTEXT.md — SCB (Sistema Campeonato Brasileiro)

> **Teto: 1 página.** Atualizar **por substituição** (reescrever "Estado atual"); o datado vai para o `CHANGELOG.md`. Histórico NÃO mora aqui.

## Objetivo (3 linhas)
Sistema **local e gratuito** que prevê partidas do **Brasileirão Série A** (e ligas configuráveis) entregando **P(V/E/D), gols esperados, mercados derivados, confiança e simulação da tabela** (título/G4/G6/Z4) — nunca certezas.
É o **port evoluído do SCM** (Copa 2026): mesmo motor auditável Elo → Poisson → ensemble, **validado por backtest antes de qualquer uso**.
**Não é ferramenta de aposta**; o mercado é benchmark, não alvo de lucro.

## Regras de negócio inegociáveis (herdadas do SCM — detalhe: `contexto/REGRAS-DE-NEGOCIO.md`)
1. **R$ 0** — sem API/base/hospedagem paga. 2. **Roda local** — nada lê a internet no cálculo (snapshot em disco). 3. **Probabilidades, nunca certezas**. 4. **Registro pré-jogo imutável**. 5. **Não inventar dados** — lacuna declarada fica declarada. 6. **Sem ML/boosting/bayes hierárquico**. 7. **Portão de backtest** — nenhum termo entra em λ/dr sem ΔBrier pareado com IC que não cruza zero.

## Restrições da stack (perfil dados-python)
Python 3.11+ · NumPy/pandas · **SQLite** (sem enum nativo; `natural_key` + guarda anti-duplicata ±2 dias) · pytest (**teste anti look-ahead obrigatório**) · Flask local · argparse · venv com `requirements.txt` de teto de major · bootstrap vetorizado (numpy) · nomes de time no padrão **football-data (EN)** · Monte Carlo com seed fixa.

## Critério de aceite (portões — definidos no dia 1)
- **Código:** `pytest -q` verde + teste PIT/anti look-ahead do módulo + ingest idempotente.
- **Modelo:** backtest **walk-forward por temporada**, Brier < uniforme **e** < taxa-base da liga, com IC bootstrap (B=10k, seed fixa) que não cruza zero; ECE e cobertura de banda reportados; comparação honesta vs mercado de-vigged (abertura **e fechamento**).
- **Termo novo:** ΔBrier pareado IC>0 no canal afetado + guardas de não-regressão (1X2/over/BTTS/ECE) + kill-switch de correlação com `dr` (corr < 0,95).
- **Docs:** este arquivo ≤ 1 página; decisão nova = **D-NN** no `DECISIONS.md`; bug = **QA-NN** citado no commit.

## Estado atual
**Fase 0–1 (bootstrap + planejamento).** Kit criado em 2026-07-14 a partir do estudo do vault SCM (contrato v5.0, D-01..D-85, viabilidade Brasileirão 2026-06-28). `PLANO.md` **aguardando congelamento** pelo Gustavo. Nenhum código ainda. Decisões de partida (D-02/03/10): **port do `scm_analytics`**; **multi-liga desde o dia 1** (Premier E0 valida o port, BRA entrega); alvo = **operar na temporada 2026 em andamento** após validação. Próximo passo: aprovar o `PLANO.md` → M1 (POC de dados football-data).

## Mapa (contexto mínimo por sessão)
Regras: `contexto/REGRAS-DE-NEGOCIO.md` · Contrato matemático: `contexto/MODELO-MATEMATICO.md` · Port/lições: `contexto/HERANCA-SCM.md` · Dados/schema: `contexto/DADOS.md` · Plano: `PLANO.md` · Decisões: `DECISIONS.md` · Tarefas: `BACKLOG.md` · Aceite: `CHECKLIST.md`
**Ciclo de sessão:** prompt do papel (`prompts/`) + este CONTEXT.md + **só o arquivo do momento** → pedir **delta** → passar no portão → registrar D-NN/QA-NN → atualizar aqui por substituição.
