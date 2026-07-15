---
tags: [contexto, regras, herdado-scm]
status: atual
tipo: especificacao
data: 2026-07-14
---

# Regras de negócio do SCB — herdadas do SCM, inalteradas

> Fonte: `CLAUDE.md` e `Decisoes tecnicas.md` do vault SCM (zip `666666_SCM_DOCs`). Estas regras são **agnósticas ao campeonato** (confirmado pelo estudo de viabilidade de 2026-06-28) e transferem 100%. Mudar qualquer uma = decisão explícita do Gustavo registrada como D-NN, nunca decisão de agente.

## As 7 inegociáveis

| # | Regra | Consequência prática no SCB |
|---|---|---|
| 1 | **Custo R$ 0** | sem API paga (Sportmonks, API-Football…), sem hospedagem; football-data.co.uk é grátis |
| 2 | **Roda local; nada lê a internet no cálculo** | download de snapshot é passo à parte (`ingest --download`); previsão/backtest 100% offline |
| 3 | **Probabilidades, nunca certezas** | inclusive sobre o próprio modelo; comunicar banda e confiança sempre |
| 4 | **Registro pré-jogo imutável** | registrar ANTES do kickoff; linha gravada nunca é editada; sem isso a validação é autoengano |
| 5 | **Não inventar dados/fontes** | lacuna declarada fica declarada (ex.: escalações estruturadas grátis não existem → desfalques por JSON manual) |
| 6 | **Sem ML/boosting/bayes hierárquico** | matam auditabilidade ou garantem overfit; motor é Elo→Poisson→ensemble em fórmulas fechadas |
| 7 | **Portão de backtest** | nenhum termo entra em λ/dr "porque a literatura diz"; só com ΔBrier pareado, IC bootstrap que não cruza zero |

## Regras de trabalho derivadas (também herdadas)

- **Contrato congelado com versão** (D-01 SCM): mudar fórmula = bump de `MODEL_VERSION`; rebuild completo quando a versão muda.
- **Baseline primeiro** (D-06 SCM): medir o motor mínimo antes de adicionar graus de liberdade.
- **Mercados são releituras, não modelos novos** (D-21 SCM): over/under, BTTS, dupla chance, handicap etc. saem da MESMA matriz Poisson — zero graus de liberdade novos, não passam por portão.
- **Mercado no ensemble com peso ≤ 0,20** (D-08 SCM): pode ecoar o Elo público, não é onisciente. *Questão aberta Q-01 (ver [[DECISIONS]]): com odds históricas reais, o teto pode ser revisto — mas por decisão do Gustavo, não do portão sozinho.*
- **Point-in-time em tudo**: features/ratings usam só o passado do jogo; teste anti look-ahead no pytest é obrigatório.
- **Ingest idempotente** (D-11 SCM) + **guarda anti-duplicata ±2 dias** (D-82 SCM): rodar N vezes não duplica; confronto igual com data divergente é barrado.
- **Instrumentação power-aware** (D-76 SCM): monitor com n baixo marca `n baixo` e não alarma — não confundir ruído com deriva.
- **A lista-morta NÃO transfere** (regra nova D-05 SCB, derivada do estudo de viabilidade): termo rejeitado pelo portão no SCM (Dixon-Coles, descanso, calor…) **re-passa pelo portão** na liga — o dado e o contexto mudaram; nem adotar nem descartar por herança.
- **Decisão rastreável**: toda escolha vira D-NN; todo bug vira QA-NN citado no commit (`fix: QA-03 …`).

## O que o sistema NÃO é
Não é ferramenta de lucro em aposta (Brier ~0,60 não é vantagem); não promete bater o mercado de fechamento (ele é o teto honesto, usado como régua); não automatiza scraping de sites com ToS restritivo (FBref, Transfermarkt, oddsportal → consulta manual apenas).
