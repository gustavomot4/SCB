---
tags: [scb, indice, mapa]
status: atual
tipo: indice
data: 2026-07-15
aliases: ["Home", "Mapa do vault"]
---

# Índice — SCB (Sistema Campeonato Brasileiro)

> Nota-casa do vault. **Fixe esta nota** (pin) e navegue por aqui.

## 🧭 Toda sessão de trabalho começa assim
Prompt do papel (abaixo) + [[CONTEXT]] + só o arquivo do momento → pedir **delta** → conferir [[CHECKLIST]] → registrar D-NN em [[DECISIONS]] → atualizar [[CONTEXT]] por substituição (datado vai pro [[CHANGELOG]]).

## Visão do projeto
- [[Manual do dono]] — **comece aqui, Gustavo**: seu papel, o ciclo de sessão, onde você entra em cada milestone
- [[CONTEXT]] — contexto-fonte (≤1 página, o que se cola em TODA sessão)
- [[PLANO]] — plano congelado v1.0 (arquitetura, milestones M0–M7, riscos)
- [[README]] — guia da pasta e do pipeline em 6 fases
- [[BACKLOG]] — quadro de tarefas (plugin Kanban)
- [[DECISIONS]] — ADRs D-NN + questões abertas Q-NN
- [[CHANGELOG]] — log datado (fora do contexto das sessões)
- [[CHECKLIST]] — portões de aceite por tipo de entrega

## Contexto para agentes (a "memória destilada" do SCM)
- [[REGRAS-DE-NEGOCIO]] — as 7 inegociáveis + regras de trabalho
- [[MODELO-MATEMATICO]] — contrato SCB v1.0 (congelado): o que fica/sai/recalibra/candidatos C1–C7
- [[HERANCA-SCM]] — mapa de port módulo a módulo + lições pagas
- [[DADOS]] — fontes, colunas, schema-alvo, lacunas declaradas, POC M1

## Prompts de papel (colar no início da sessão conforme a fase)
- [[00-bootstrap-contexto]] · Fase 0 — manter o CONTEXT verdadeiro
- [[01-planejador]] · Fase 1 — planejar/defender o plano congelado
- [[02-implementador]] · Fases 2–3 — construir módulo a módulo, por delta
- [[03-qa-adversarial]] · Fase 4 — quebrar o que foi construído
- [[04-auditor-evolucao]] · Fase 5 — busca céptica de melhorias
- [[05-revisao-entrega]] · Fase 6 — empacotar e conferir

## Operação e resultados
- [[Operacao BRA 2026]] — runbook da rodada (1 clique na web)
- [[Backtest baseline (2026-07-16)]] — os números do portão da M4
- [[POC-M1-dados (2026-07-15)]] — inventário da fonte

## Estado (espelho rápido — a verdade mora no [[CONTEXT]])
**M0–M7.1 executadas** (2026-07-17): modelo `scb-v0.3-mando-e0` validado (BRA 0,6131 / E0 0,5894) · web no ar · operação em 1 clique · 73 testes. Falta **M7.2 (empacotamento)**; evolução futura: Q-07/Q-08.
