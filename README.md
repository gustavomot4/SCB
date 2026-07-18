---
tags: [scb, readme, guia]
status: atual
tipo: guia
data: 2026-07-15
---

# SCB — Sistema Campeonato Brasileiro (Série A)

Port evoluído do **SCM** (sistema de análises da Copa 2026) para **ligas de pontos corridos**, com o Brasileirão como entrega e a Premier League como liga de validação. Mesmo motor auditável (Elo → Poisson → ensemble), mesmas regras de negócio, **melhorado onde a liga permite** (odds automáticas com fechamento, simulador de tabela, mando medido, novos candidatos ao portão).

**Estado (2026-07-17):** M0–M7.1 executadas — modelo oficial **`scb-v0.3-mando-e0`** validado por walk-forward (BRA 0,6131 / E0 0,5894), web no ar (`scb_analytics/Abrir SCB.bat`), operação em 1 clique, 73 testes. Falta M7.2 (empacotamento). A verdade viva mora no [[CONTEXT]].

## Este repositório é um vault Obsidian

Abrir no Obsidian: **Open folder as vault** → selecionar esta pasta `SCB`. Nota-casa: [[Indice]] (fixe-a). Plugins recomendados (mesmos do SCM): **Kanban** (obsidian://show-plugin?id=obsidian-kanban — o [[BACKLOG]] usa esse formato) e **Obsidian Git** (commits/push de dentro do app; opcional — o terminal também serve). O `.gitignore` já ignora o workspace volátil do Obsidian.

## Como usar esta pasta (para agentes e para o Gustavo)

Este repositório segue o **pipeline pessoal de projetos com IA** (6 fases, 5 regras). O ciclo de toda sessão de trabalho:

> abrir sessão → colar o **prompt do papel** (`prompts/`) + o **[[CONTEXT]]** + **só o arquivo do momento** → pedir **delta** → passar no **portão** ([[CHECKLIST]]) → registrar **D-NN/QA-NN** → atualizar [[CONTEXT]] **por substituição** e jogar o datado no [[CHANGELOG]].

## Mapa dos arquivos

| Arquivo | Papel | Quem carrega |
|---|---|---|
| [[CONTEXT]] | contexto-fonte, ≤1 página, atualizado por substituição | **toda sessão** |
| [[PLANO]] | plano **congelado**: arquitetura, milestones M0–M7 com portões, riscos | planejador; consulta pontual |
| [[REGRAS-DE-NEGOCIO]] | as 7 regras herdadas do SCM + regras de trabalho | quando a tarefa tocar regra |
| [[MODELO-MATEMATICO]] | **contrato matemático SCB v1.0 (congelado)**: o que fica/sai/recalibra/candidatos | implementador do motor; auditor |
| [[HERANCA-SCM]] | mapa de port módulo a módulo + lições pagas pelo SCM | implementador em port |
| [[DADOS]] | fontes, colunas esperadas, schema-alvo, lacunas declaradas, POC M1 | implementador de dados |
| [[DECISIONS]] | ADRs D-NN + questões abertas Q-NN (append-only) | auditor; consulta pontual |
| [[BACKLOG]] | quadro de cards por milestone (plugin Kanban) | início de sessão de trabalho |
| [[CHANGELOG]] | log datado, fora do contexto | ninguém carrega; só escreve |
| [[CHECKLIST]] | portões de aceite por tipo de entrega | fim de toda entrega |
| `prompts/00..05` | papéis reutilizáveis por fase (ver [[Indice]]) | conforme a fase |

## As 6 fases aplicadas ao SCB

| Fase | No SCB | Portão | Estado |
|---|---|---|---|
| 0 — Bootstrap | este kit | CONTEXT ≤1 pág + aceite escrito | ✅ 2026-07-14 |
| 1 — Planejamento | [[PLANO]] + contrato | **aprovação do Gustavo → congela** | ✅ 2026-07-15 (D-11) |
| 2 — Dados/Schema | M1 (POC) + M2 (ingest/schema) | migration roda; contagens batem | ✅ (D-13..D-16; BRA 5.496/E0 12.704) |
| 3 — Implementação | M3 (motor) + M4 (backtest) | pytest por módulo; **portão do baseline** | ✅ (D-17: BRA 0,6146/E0 0,5899 → v0.3: 0,6131/0,5894) |
| 4 — QA adversarial | contínua (QA-01..QA-10 achados e corrigidos) | crítico/alto corrigidos c/ QA-NN | ✅ em regime |
| 5 — Evolução | M6 (fila do portão, 9 gates) | IC>0 + guardas, um por vez | ✅ 2 adoções (D-25/D-26) · 7 rejeições · Q-07/Q-08 abertas |
| 6 — Entrega | M5 operação + M7.1 web · **M7.2 empacote** | CHECKLIST completo | 🔜 M7.2 |

## Origem e material de referência

Sistema-mãe: zip `666666_SCM_DOCs` (vault Obsidian + `scm_analytics/`, modelo `baseline-v0.5.1-confed`, ~194 testes). A análise que origina este projeto é do próprio vault: *"Viabilidade — modelo para ligas de clubes (Brasileirão e alternativas)"* (2026-06-28). **Não carregar o vault inteiro em sessão** — os docs de `contexto/` já destilam o necessário.
