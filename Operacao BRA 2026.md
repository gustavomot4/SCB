---
tags: [scb, operacao, runbook, bra2026]
status: atual
tipo: runbook
data: 2026-07-17
---

# Operação do BRA 2026 — runbook da rodada (agora em 1 clique)

> Princípio herdado do SCM: durante a temporada, o maior retorno é **medir** (registro
> imutável + settle + report), não mexer em fórmula. **Registrar TODA rodada antes do
> kickoff** — 19/81 no SCM quase matou a auditoria. Evolução = fila do portão.

## Setup (1x por temporada)
- **Calendário:** o `dados/fixtures.csv` já vem com o BRA 2026 inteiro (rodadas 19-38) + a
  Premier (D-38). Em temporada nova, cole o calendário (formato `league,round,date,home,away`,
  data ISO ou dd/mm/aaaa). A fonte de resultados não traz futuro — o calendário é seu.
- **Escudos do BRA (1x):** `python scripts/baixar_escudos_bra.py` — os 20 oficiais do CDN da
  API-Futebol, sem chave e sem gastar cota (D-37). Premier: `python scripts/baixar_escudos.py`.
- **Chave da API-Futebol (grátis):** exponha `APIFUTEBOL_KEY` (`$env:APIFUTEBOL_KEY="live_..."`)
  — habilita os stats e os RESULTADOS do BRA (ver "Depois dos jogos").

## Antes dos jogos (1 clique)
Abrir a web (`Abrir SCB.bat`) → **Prospectivo** → **"Registrar rodada (calendário, ≤4 dias)"**.
Pronto: todos os jogos da janela registrados, imutáveis, com o V/E/D carimbado.
- Alternativa CLI/agendável: `python -m scb.registrar auto --dias 4`
  (agende no Task Scheduler do Windows p/ rodar toda manhã = automação total).
- Jogo avulso: formulário "Registrar jogo" na mesma tela (ou `registrar register`).
- Prévia de um confronto: tela **Prever Confronto** (com Imprimir/PDF e Copiar resumo).

## Depois dos jogos (quando o football-data atualizar — 1x/semana)
```
python -m scb.ingest --download
python -m scb.ingest
python -m scb.elo_engine
python -m scb.features_pit --incremental
python -m scb.predictor --incremental
```
- **BRA — a fonte primária ATRASA semanas.** Para liquidar as rodadas recém-jogadas sem
  esperar o football-data, rode `python scripts/baixar_stats_bra.py` (busca os recentes
  primeiro; se a API cortar com **429**, é só a cota do dia — rode de novo amanhã que ele
  retoma de onde parou, é resumível e self-healing) e depois `python -m scb.ingest`: a
  API-Futebol preenche em `matches` os placares que faltam (D-36) → o settle fecha os jogos.
Depois, na web (Prospectivo): **"Liquidar resultados (settle)"** — preenche placares e
Brier (acha até jogo ADIADO: par ordenado é único por temporada — D-31). O painel da
tela é o report (Brier acumulado vs uniforme 0,667; avisa quando n é baixo).
- Jogo que a fonte ainda não tem: `dados/resultados_extra.csv` (guarda ±2d ativa, D-82).

## Telas de acompanhamento (quando quiser)
- **Tabela** → aba **Projeção** (Monte Carlo: título/G4/G6/Z4, trilho da temporada) ou
  **Classificação** (a tabela REAL dos jogos disputados, D-38). `python -m scb.simulate_league
  --season 2026` faz a projeção pela CLI. Seed fixa: só jogo novo muda o futuro.
- **Calibração** (D-39) → o modelo acerta? Brier + ECE + curva de confiabilidade + comparação
  com o mercado (o modelo fecha 78% na E0 / 50% no BRA da distância chute→mercado). É a
  resposta honesta de "dá pra confiar nas %".

## O que NÃO fazer
Editar linha do registro (imutável) · re-registrar após o kickoff · mexer em constante
do modelo fora de sessão de evolução com portão · scraping de sites (ToS/R$0).
