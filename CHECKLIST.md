---
tags: [scb, checklist, portao]
status: atual
tipo: checklist
data: 2026-07-15
---

# CHECKLIST — o que conferir antes de aceitar um output da IA

> Regra 5 do pipeline: **nada é aceito sem passar no portão** — não o que "parece bom". Usar a seção do tipo de entrega. Falhou um item ⇒ volta com delta, não regenera.

## Qualquer entrega
- [ ] A sessão usou o prompt do papel + CONTEXT.md + só o arquivo do momento (contexto enxuto)?
- [ ] A mudança veio como **delta** (trecho alterado), não documento/módulo regenerado?
- [ ] Decisão nova virou **D-NN**? Bug achado virou **QA-NN** citado no commit?
- [ ] CONTEXT.md atualizado **por substituição** e o datado foi para o CHANGELOG?
- [ ] Nenhum dado/fonte inventado (lacuna continua declarada)?

## Código (módulo)
- [ ] `python -m pytest -q` verde **na máquina do Gustavo** (não confiar só no sandbox — lição D-14/16 SCM)
- [ ] Teste **anti look-ahead / PIT** cobre o módulo (se ele toca features/ratings)
- [ ] Ingest: idempotência + guarda ±2d testadas; contagens batem com a fonte
- [ ] Consistência produção↔backtest preservada (porta da frente = modelo validado)
- [ ] Mudou fórmula? ⇒ bump de `MODEL_VERSION` + rebuild completo documentado
- [ ] Nada lê a internet no cálculo; download é passo à parte

## Modelo (adoção/rejeição de termo)
- [ ] ΔBrier **pareado** com IC bootstrap (B=10k, seed=12345) que **não cruza zero** no canal afetado, no split walk-forward
- [ ] Guardas de não-regressão: 1X2 / over2.5 / BTTS / ECE nas classes não-alvo
- [ ] Kill-switch: corr do termo com `dr` < 0,95 (sinal novo de verdade)
- [ ] Potência declarada (n do teste; recorte sub-powered dito como sub-powered)
- [ ] Resultado registrado como D-NN (adotado OU rejeitado — memória contra re-exploração)
- [ ] Sanity herdado: em dado aleatório o modelo NÃO bate o uniforme

## Backtest / relatório
- [ ] As 4 réguas presentes: uniforme, taxa-base da liga, Elo-puro, mercado (abertura e fechamento)
- [ ] ECE + cobertura de banda por faixa reportados
- [ ] Nenhuma métrica de treino vendida como teste; split e seeds declarados

## Documentos
- [ ] CONTEXT.md continua ≤ 1 página
- [ ] Doc novo diz status (atual/rascunho/histórico) e data
- [ ] Números sobre a liga têm origem (medição da M1+ ou [a medir]/[a calibrar])

## Empacotamento / entrega (Fase 6)
- [ ] Zip só com fonte + docs + dados curados: sem `.venv`/`node_modules`/`.git`/`__pycache__`/`*.sqlite`/`*.bak`
- [ ] Sem segredo/token em nenhum arquivo
- [ ] **Abriu o zip e conferiu** que os arquivos certos estão lá (lição do `.lnk` quebrado — e do zip de 3,5 GB do SCM que veio com .venv e open-data)
- [ ] README diz como rodar do zero (venv → requirements → ingest → pipeline → web)
