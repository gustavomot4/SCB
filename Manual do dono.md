---
tags: [scb, guia, gustavo]
status: atual
tipo: guia
data: 2026-07-15
aliases: ["Papel do Gustavo", "Como trabalhar neste projeto"]
---

# Manual do dono — o papel do Gustavo no SCB

> Espelho da explicação de 2026-07-15. Os agentes produzem; **você decide, aceita e opera o que a IA não alcança**. Este projeto não anda sem você em 6 pontos:

## Suas 6 responsabilidades

1. **Guardião do portão.** Nada é aceito porque "parece bom". Fim de entrega = rodar a seção certa do [[CHECKLIST]]. Falhou item → devolve pedindo **delta** (nunca "refaz tudo").
2. **Decisor de negócio.** Agente não muda regra de negócio nem rumo do projeto. Toda questão Q-NN do [[DECISIONS]] é sua (ex.: Q-01, teto do mercado). Sua resposta vira D-NN.
3. **Operador da máquina real.** `python -m pytest -q` roda na SUA máquina (o sandbox mente — lição D-14/16 do SCM), assim como `git commit/push` e os downloads de snapshot.
4. **Fonte dos dados manuais.** Desfalques (JSON), resultados da rodada quando a fonte atrasa (`resultados_extra`), prior de promovidos. Se você não preencher, fica **lacuna declarada** — nunca inventada.
5. **Disciplina operacional.** Registrar TODA rodada **antes do kickoff** (a partir da M5). A lição mais cara do SCM: só 19 de 81 jogos registrados quase matou a pergunta principal sem resposta.
6. **Higiene de contexto.** Conferir que o [[CONTEXT]] foi atualizado **por substituição** (≤1 página) e o datado foi para o [[CHANGELOG]]. O agente faz; você confere.

## O ciclo de toda sessão de trabalho (90% do dia a dia)

1. Abrir chat novo → colar o **prompt do papel** (`prompts/`) + **[[CONTEXT]]** + **só o arquivo do momento**
2. Pedir a entrega em **delta**
3. Conferir no [[CHECKLIST]] + rodar `pytest` na sua máquina
4. Aceitou → **D-NN/QA-NN** registrado → commit (mensagem vem pronta do agente)
5. [[CONTEXT]] atualizado por substituição; datado no [[CHANGELOG]]

## Onde você entra em cada milestone

| Milestone | Seu papel |
|---|---|
| M1 (POC dados) | aceitar o inventário; decidir Q-02 (Kaggle) |
| M2–M3 (ingest/motor) | rodar pytest; aceitar módulo a módulo |
| M4 (backtest) | **portão do baseline** — a decisão mais importante do projeto |
| M5 (sim/operação) | confirmar Q-03 (desempate CBF); iniciar o ritual de registro por rodada |
| M6 (evolução) | julgar adoções/rejeições da fila C1–C6 (o agente traz os números; o juízo de timing é seu) |
| M7 (entrega) | conferir o CHECKLIST de empacotamento (abrir o zip!) |

## Frases de segurança (quando algo cheirar mal)

"Isso passou no portão? Mostra o IC." · "Cadê o D-NN disso?" · "Me manda só o delta." · "Isso muda fórmula? Então é bump de versão." · "Rodou na minha máquina ou no sandbox?"
