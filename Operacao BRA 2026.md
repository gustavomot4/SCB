---
tags: [scb, operacao, runbook, bra2026]
status: atual
tipo: runbook
data: 2026-07-16
---

# Operação do BRA 2026 — runbook da rodada

> Princípio herdado do SCM: durante a temporada, o maior retorno é **medir** (registro
> imutável + settle + report), não mexer em fórmula. Evolução = fila do portão (M6).
> **Registrar TODA rodada antes do kickoff** — 19/81 no SCM quase matou a auditoria.

## Antes dos jogos da rodada (5 min)

```
cd scb_analytics
python -m scb.registrar register BRA "Time Casa" "Time Fora" --date 2026-07-19
```
(um por jogo da rodada; nomes no padrão football-data — se errar, ele sugere.
Prévia de um confronto: `python -m scb.predict_match BRA "Casa" "Fora"`.)

## Depois dos jogos (quando o football-data atualizar — 1×/semana)

```
python -m scb.ingest --download          # novo snapshot (BRA + E0)
python -m scb.ingest                     # -> scb.sqlite
python -m scb.elo_engine                 # rebuild (rápido)
python -m scb.features_pit --incremental
python -m scb.predictor --incremental
python -m scb.registrar settle           # preenche resultados do registro
python -m scb.registrar report           # Brier prospectivo acumulado
```
Jogo que a fonte ainda não tem e você precisa AGORA: `dados/resultados_extra.csv`
(formato no `.example`; guarda anti-duplicata ±2d ativa — D-82).

## Tabela simulada (quando quiser)

```
python -m scb.simulate_league --season 2026            # P(título/G4/G6/Z4), 5000 sims
```

## O que NÃO fazer
Editar linha do registro (imutável) · mexer em constante do modelo fora da M6 (portão)
· re-registrar depois do kickoff (autoengano — a linha nova não substitui nada).
