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
Copie `dados/fixtures.csv.example` → `dados/fixtures.csv` e cole o **calendário da
temporada** (a CBF publica a tabela completa; formato `league,date,home,away`, data
ISO ou dd/mm/aaaa). A fonte de resultados não traz futuro — o calendário é seu.

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
Depois, na web (Prospectivo): **"Liquidar resultados (settle)"** — preenche placares e
Brier (acha até jogo ADIADO: par ordenado é único por temporada — D-31). O painel da
tela é o report (Brier acumulado vs uniforme 0,667; avisa quando n é baixo).
- Jogo que a fonte ainda não tem: `dados/resultados_extra.csv` (guarda ±2d ativa, D-82).

## Tabela simulada (quando quiser)
Tela **Tabela Simulada** (P título/G4/G6/Z4, trilho da temporada, Imprimir/Copiar) —
ou `python -m scb.simulate_league --season 2026`. Seed fixa: só jogo novo muda o futuro.

## O que NÃO fazer
Editar linha do registro (imutável) · re-registrar após o kickoff · mexer em constante
do modelo fora de sessão de evolução com portão · scraping de sites (ToS/R$0).
