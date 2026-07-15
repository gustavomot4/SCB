---
tags: [contexto, port, heranca, scm]
status: atual
tipo: especificacao
data: 2026-07-14
---

# Herança do SCM — mapa de port e lições que não podem se perder

> Fonte da verdade do sistema-mãe: zip `666666_SCM_DOCs` (vault Obsidian + código `scm_analytics/`, modelo `baseline-v0.5.1-confed`, 35 arquivos de teste / ~194 casos). Este doc orienta o agente implementador: **o que copiar, o que trocar, o que jogar fora — e as armadilhas que o SCM já pagou para descobrir.**

## 1. Mapa de port módulo a módulo (pacote `scm/` → `scb/`)

| Módulo SCM | Destino no SCB | Ação |
|---|---|---|
| `db.py` | ✅ porta | schema ganha `season`, `round`, odds abertura+fechamento (ver `contexto/DADOS.md`) |
| `ingest.py` | 🔁 troca o parser | novo `ingest` do football-data **parametrizado por liga** (E0, BRA…); manter: idempotência por `natural_key`, guarda ±2d (D-82), `--dedup`, `resultados_extra.csv` (D-80), pular jogo sem placar (D-12) |
| `elo_engine.py` | ✅ porta | K único por liga [a calibrar]; point-in-time (`match_ratings`) intacto; **novo:** hook de virada de temporada (regressão ρ, candidato C5) |
| `features_pit.py` | ✅ porta | forma com decay por jogo [a calibrar]; mando todo jogo; remover confed/altitude do dr |
| `predictor.py` | ✅ porta quase intacto | trocar `DRAW_CURVE` pela curva DA LIGA (obrigatório, §3.2 do contrato); remover `knockout_advance` do fluxo |
| `attack_defense.py` (perna AD) | ✅ porta | prior de gols da liga; `w_ad` [a calibrar] |
| `odds.py` | ✅ porta e SOBE de papel | de-vig proporcional intacto; agora alimentado automaticamente pelo CSV (abertura+fechamento) — vira série histórica p/ backtest |
| `odds_close.py` | 🔽 rebaixa | captura manual vira **fallback** (fechamento vem no CSV pós-jogo); manter watch p/ registro pré-jogo se quiser CLV intra-rodada |
| `backtest_harness.py` | ✅ porta | + walk-forward por temporada; + baselines taxa-base e mercado |
| `calibrate*.py` (família de portões) | ✅ porta | são a infraestrutura do portão; re-apontar métricas/splits |
| `registrar.py` | ✅ porta intacto | imutabilidade + settle tolerante a data/mando invertido (D-80c) |
| `monitor.py` | ✅ porta intacto | drift por mercado power-aware (D-76); CLV automático via fechamento do CSV |
| `report.py` | ✅ porta | `--copa` vira `--liga/--temporada` |
| `simulate.py` | 🔁 REESCREVE | de bracket FIFA → **pontos corridos** (MC da temporada, desempate por liga, jogos disputados travados — disciplina D-83/85) |
| `desfalques.py` | ✅ porta intacto | JSON manual, direcional |
| `confed.py`, `altitude.py`, `timing.py`, `setpiece.py`, `xg.py`, `heat.py`, `estilo.py` | ⛔ OFF/fora | ficam no repo como candidatos OFF documentados; não entram no pipeline default |
| `web.py` + templates | 🔁 adapta (fase final) | telas: prever jogo, tabela simulada (substitui bracket), prospectivo, monitor; launcher `.bat`; "Atualizar tudo" com rebuild full na troca de versão |
| `dixon_coles.py`, `drift.py` | ✅ porta como candidatos | C2 e C3 da fila do portão — no SCM já existem prontos p/ re-gate |
| `tests/` | ✅ porta e adapta | manter invariantes: anti look-ahead, idempotência, soma=1, piso conserva T_m, skill-regression trava o backtest |

**Estimativa do estudo de viabilidade: ~70% do código entra sem mexer.** O trabalho real: (a) ingest football-data, (b) simulador de liga, (c) recalibrar K/H/T_base/curva de empate, (d) re-rodar portão nos candidatos.

## 2. Lições pagas pelo SCM (NÃO reaprender do zero)

| Lição | Origem | Regra prática no SCB |
|---|---|---|
| Duplicata fura a `natural_key` quando a data diverge | D-82 (Elo contou NED×MAR 2×) | guarda ±2d no ingest + `--dedup`; teste dedicado |
| A realidade antes da estatística: resultado real trava a simulação | D-83/85 (eliminado "vivo" no MC) | jogos disputados são verdade no simulador de liga; invariantes nos testes |
| Produção deve entregar o MESMO modelo do backtest | D-34/35 (forma descartada na porta da frente) | teste de consistência produção↔backtest |
| Piso de λ conserva o total | D-22 (over/BTTS inflado em massacre) | manter o teste |
| Correção estática de nível de gols falha; deriva é por ERA | D-25/40 vs D-84 | não re-propor T_base estático; o caminho é o C3 (janela móvel PIT) |
| Termo novo precisa ser INDEPENDENTE do dr | kill-switch corr<0,95 (D-79 passou com 0,06) | medir corr antes do portão |
| Troca de versão ⇒ rebuild completo (incremental deixaria jogos na fórmula velha) | atualização 06-27 | `MODEL_VERSION` + detecção no botão/CLI |
| Bootstrap vetorizado; sanity: em dado aleatório o modelo NÃO bate o uniforme | D-15 | manter teste de "sem skill inventado" |
| Clone reprodutível: versionar snapshot + dados curados; ignorar só `*.sqlite`/`*.png` | D-78 | `.gitignore` desde o dia 1 |
| Curvas empíricas congeladas carimbam a versão | D-24/26 | curva de empate e reliab da confiança gravadas em `meta` com a versão |
| Monitor power-aware: n<10 não alarma | D-76 | herdar como está |
| Registro imutável usado POUCO vira auditoria fraca | busca v3 (19/81 jogos) | no SCB: registrar TODA rodada é passo do runbook, não opcional |
| Sandbox: mount trunca arquivo recém-editado; git index corrompe; pytest/flask rodam na máquina do usuário | D-14/16 | validar em harness isolado + rodar `pytest` na máquina; git do usuário |

## 3. Onde buscar detalhe no vault SCM (quando precisar)

`00 - Projeto/MODELO_FINAL.md` (o que a V1 calcula) · `01 - Planejamento/camada1-planejamento-v5.md` + apêndice (contrato e formas f/g/C1) · `04 - Desenvolvimento/Decisoes tecnicas.md` (D-01..D-85) · `04 - Desenvolvimento/Viabilidade — modelo para ligas de clubes (2026-06-28).md` (a análise que origina o SCB) · `04 - Desenvolvimento/Busca de melhorias — analise PIT (v3).md` (método de busca céptica com STEP 0 medido — reutilizar o formato na Fase 5).

> **Contexto enxuto:** NÃO carregar o vault SCM inteiro em sessão. Este arquivo + o contrato SCB bastam para 90% das tarefas; abrir o doc específico do vault só quando a tarefa tocar aquele ponto.
