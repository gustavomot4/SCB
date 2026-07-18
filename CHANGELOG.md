---
tags: [scb, changelog, historico]
status: vivo
tipo: log
---

# CHANGELOG — SCB

> Log datado, append-only. **Não é carregado nas sessões** (o presente mora no CONTEXT.md). Uma linha por evento relevante; detalhe fica no commit/D-NN.

## 2026-07-17 (e) — Evolução: proxy de xG REJEITADO (D-32) + base `match_stats` + telas
- **Portão do proxy de xG por CHUTES NO GOL (SoT)** — `scb/sot_edge.py` (δ PIT anti-look-ahead somado ao `dr`; K/θ escolhidos na era de calibração). Gate-0 promissor (corr parcial 0,11 no saldo, além do Elo), mas o **portão completo REJEITOU** (E0 validação 2014-25, n=4560, K\*=5 θ\*=10): 1X2 Δ−0,0005 IC cruza zero; over/BTTS e ECE regridem; kill-switch corr 0,70 (ok). Eco do Dixon-Coles (D-27): sinal marginal dilui no ensemble. **2 canais testados, ambos rejeitados**: (dr) 1X2 −0,0005 IC cruza + gols/ECE regridem; (gd, δ só na margem da Poisson) 1X2 +0,0001 IC cruza + gols regride. Sinal real mas fraco/entrelaçado com o Elo (corr 0,70). **3º ângulo — SoT-TOTAL→T_m**: MELHORA os gols (over/BTTS Δ+0,0013 IC>0) + ECE, independente do Elo (corr 0,07), mas trips a guarda do 1X2 por um fio (−0,00007). Não adotado no λ compartilhado, mas é o 1º sinal ÚTIL — caminho: desacoplar (SoT-total só nas saídas de gols). Módulo OFF; `MODEL_VERSION` inalterada.
- **Base `match_stats` (nova)** — ingest agora guarda escanteios/cartões/chutes/faltas/HT/árbitro da Premier (E0 2000-2025, 11.780 jogos); BRA sem stats (lacuna da fonte). DESCRITIVO — o modelo não lê. +5 testes. Exibida no **Prever Confronto** (perfil estatístico, médias/jogo, barras estilo Globo/Opta) via `/api/matchstats`.
- **Telas/UX** — E0→**PRE** só no display (código interno segue `E0`); `fixtures.csv` com BRA rodada 19 + PL 2026/27 (+coluna `round`); **Tabela Simulada** projeta a temporada a partir do calendário quando ainda não começou (PRE 2026/27) + coluna **V–E–D** + clique no clube (Elo/forma/rank); tela nova **Jogos** por rodada (placar mais provável, estilo Globo). Logos: `object-fit:contain` (fim do esticamento) + Coventry/Hull nas cores curadas.
- **Comparativo de mercado** — SCB vs Opta/538-SPI/ClubElo: SCB é grátis/local/auditável/bem-calibrado; teto ~2pp atrás do mercado (que a Opta parcialmente usa como input); maior lacuna = sem xG e sem dados de jogador.

## 2026-07-17 (d) — Registro da RODADA em 1 clique (D-31)
- Pergunta do Gustavo: "não dá pra apertar um botão e registrar a rodada?" Resposta honesta: a fonte NÃO publica calendário futuro (lacuna declarada) e scraping fura ToS/R$0. Desenho dentro das regras: **`dados/fixtures.csv` colado 1x por temporada** (a CBF publica a tabela completa) + `registrar.auto(dias=4)` — registra tudo que vence na janela, idempotente. Na web: botão **"Registrar rodada"** no Prospectivo; na CLI: `python -m scb.registrar auto` (agendável no Task Scheduler do Windows p/ automação total).
- Bônus de robustez: **settle acha jogo ADIADO** — o par ordenado (casa,fora) é único por temporada no turno-returno, então casar o jogo mais próximo após o registro é seguro (antes: ±2d e ficava em aberto p/ sempre).
- 2 testes novos (janela+idempotência; adiado liquida). 73 no total.

## 2026-07-17 (c) — Escudos: estado final + REGISTRO PELA WEB
- Escudos: Premier 100%; BRA = 4 automáticos (tudo que o FCLOGO/CBF tem) + **lista manual digna** p/ os 16 da temporada (`dados/escudos-pendentes.md`, slugs exatos) — 5 repositórios varridos, fontes públicas esgotadas com honestidade.
- **Prospectivo ganhou operação pela web** (pedido do Gustavo): formulário "Registrar jogo" (liga/casa/fora/data → `/api/registrar`, imutável e idempotente — mostra o V/E/D gravado) + botão "Liquidar resultados" (`/api/settle`). O ritual da rodada agora é 100% sem terminal. Exige reiniciar o `.bat` (código novo).

## 2026-07-17 (b) — QA-10: cache-busting fecha a saga dos escudos
- Verificado contra o disco real: **a v5 baixou o BRA** (palmeiras.svg, flamengo-rj.svg via /CBF/) e a rota serve os arquivos certos p/ TODOS os testados. O que segurava era o **cache do navegador** (max-age=86400 da 1ª versão sobrevive a reiniciar a máquina — o browser nem consulta o servidor até expirar). Fix independente do navegador: **URLs com `?v=2`** nos templates (cache key nova) — F5 normal resolve.

## 2026-07-17 — QA-09: escudos v5 — resolvido COM DADO (modo --investigar)
- `--investigar` (novo) imprimiu a estrutura REAL: FCLOGO organiza por FEDERAÇÃO (Brasil = `/CBF/`, nunca "brazil" no caminho) e nomeia por extenso com sufixo de versão (`Clube-de-Regatas-do-Flamengo-v0000`). Três consertos medidos: (a) hint `/cbf/`+`br-brazil`; (b) matching por SUBCONJUNTO DE PALAVRAS (apelido ⊆ nome oficial) com desempate por similaridade; (c) **bug das chaves do ALIAS sem normalização** (Nott'm/Ipswich regrediram na v3 por isso). Sufixos v0000 e bandeiras 1200x630 filtrados. Harness com os caminhos reais: **12/12 + guarda de bandeira**.
- Confirmado no disco via mount: 28 PNGs da E0 presentes; BRA aguardando o run da v5.

## 2026-07-16 (r) — QA-08: escudos v4 (fonte BRA de verdade) + causa do "não aparece nada"
- Run do Gustavo: hugomiura tinha SÓ 4 arquivos (fonte furada → BRA 0/38) e a web seguia genérica porque **o servidor antigo continuava no ar** (a correção QA-06 do cache é código → exige reiniciar o `.bat` + Ctrl+F5; os 28 PNGs da E0 JÁ estavam no disco).
- **v4:** repo Leo4815162342/football-logos (3.400+ escudos SVG+PNG mundiais) em modo "auto" — cada arquivo classificado pela pasta do país (brazil→BRA, england→E0); hugomiura removido.

## 2026-07-16 (q) — QA-06/QA-07: escudos v3 + cache do badge
- **QA-06 [corrigido]:** a rota `/badge` mandava `max-age=86400` → o navegador segurava o SVG antigo por 24h e os PNGs baixados "não apareciam". Agora `no-cache` (app local) e o override aceita **.png OU .svg**.
- **QA-07 [corrigido]:** matching v2 com cutoff frouxo criou falsos positivos (Juventude←Juventus, Mirassol←Sassuolo, Portsmouth←Bournemouth, Barnsley←Burnley…) e o repo mundial não tinha Brasil. **v3:** fonte BRA dedicada (hugomiura/escudos-times-brasil-svg, Séries A+B em SVG), **afinidade por repositório** (repo BR só alimenta BRA; europeu só E0), cutoff 0,82 e fora-do-pool só match EXATO; `--limpar` refaz do zero. Harness: 11/11 (falsos da v2 mortos; Atlético-MG→Mineiro via alias confirmado).

## 2026-07-16 (p) — QA-05: baixar_escudos v2 (árvore completa, sem chute de pasta)
- 1º run do Gustavo: v1 chutava nomes de pasta (repo tinha `logos/` na raiz e ligas dentro) → 0 escudos, aviso gracioso. **v2: API git/trees baixa a árvore INTEIRA (1 chamada/repo) e casa clube×PNG por similaridade** com mapa de apelidos (Man City→Manchester City, Bragantino→Red Bull, Atlético-MG→Mineiro…) e filtro de liga (sem vazamento cruzado). 2 fontes: luukhopman (Europa/E0, temporadas 21/22–25/26) + klunn91/team-logos (mundial, tentativa BRA). Matching 5/5 no harness. Sem match = badge SVG (fallback intacto).

## 2026-07-16 (o) — Feedback do Gustavo na web: QA-04 + escudos PNG + compartilhar (D-30)
- **QA-04 [corrigido]:** chips de probabilidade tinham glow verde-sobre-verde ilegível (achado do usuário, com print) → chips SÓLIDOS de alto contraste (≥50% = volt com texto escuro; faixas médias em roxo/cinza; Z4 vermelho sólido).
- **D-30 — escudos PNG (projeto pessoal/estudo):** `scripts/baixar_escudos.py` — VOCÊ roda (padrão `--download`): lista repo público de logos via API do GitHub, casa nomes por similaridade com os slugs e preenche `static/logos/`; a web usa os PNGs automaticamente (override já existente); sem match = badge SVG. Uso pessoal, nunca publicar.
- **Compartilhar/imprimir:** CSS de impressão (tema claro p/ papel/PDF, esconde navegação) + botões "Imprimir/PDF" e "Copiar resumo" (texto formatado p/ clipboard) nas telas de confronto e tabela, com cabeçalho carimbado (versão, data, "probabilidade nunca certeza").
- Templates re-renderizados no Jinja do sandbox; teste visual = navegador do Gustavo.

## 2026-07-16 (n) — M7.1: WEB estilo EA FC entregue (D-29)
- `scb/web.py` (Flask lazy) + `scb/badges.py` + 3 templates (layout com design system dark/condensado; prever com arena VS + barras animadas + top-5 em tiles; tabela com trilho de temporada + chips coloridos por probabilidade; prospectivo com painel de auditoria) + `Abrir SCB.bat`.
- Escudos: SVG gerado com cores REAIS por clube (~50 curados + fallback hash) + override `static/logos/<slug>.png` (uso pessoal). Sem Node (TECH_STACK); fontes CDN com fallback (offline ok).
- 5 testes de badges/import (71); 3 telas renderizam no Jinja do sandbox; Flask ao vivo = navegador do Gustavo (precedente SCM).

## 2026-07-16 (m) — Fila da E0 fechada: `scb-v0.3-mando-e0` (D-26/27/28)
- **Q-04 executada (D-26):** mando rolling adotado na E0 (features_pit soma δ PIT no dr_adj; predict_match usa delta_today; harness lê dc_rho/config). Oficial: **E0 0,5899→0,5894 · ECE 0,0365→0,0290 · gap mercado −0,0156; BRA 0,6131 intacto.** δ embutido: E0 −41,5 Elo / BRA 0,0. Fix: default min_n congelava no def.
- **Q-05 fechada (D-27):** DC rejeitado no 2º gate (re-blend 1X2: +0,00005 IC cruza) — ganho do empate dilui no ensemble; capacidade dc_rho testada e OFF.
- **Banda medida (D-28):** σ×1,3 → E0 8/10 (+29% largura), BRA neutro → Q-07 (2ª propagação só-banda, M7+).
- +3 testes (66). C4 precisa de curadoria de coordenadas (Q-08); C6 pronto-para-rodar. **M7 liberada.**

## 2026-07-16 (l) — M6.7 FECHADA no run oficial (números idênticos)
- Rebuild do Gustavo: 63 passed · BRA 0,6131 (todas as réguas internas PASSAM, incl. elo_puro +0,0014 IC>0) · E0 idêntica · sim 2026 Palmeiras 79,6%. `scb-v0.2-rho-bra` é o modelo OFICIAL.
- Observação de exibição (não-bug): clube que saiu da liga há anos (ex.: Portuguesa, 2013) não sofre as regressões anuais → rating congelado aparece alto no top-10 de `ratings_current`. Não toca previsão/sim (só joga quem está na temporada). Cosmético p/ M7 (filtrar ranking por clubes da temporada corrente).

## 2026-07-16 (k) — M6.7: 1ª ADOÇÃO — `scb-v0.2-rho-bra` (D-25)
- ρ=0,40 checado (pior na calib; IC cruza na valid) → ρ=0,30 confirmado. Wiring POR LIGA (config dict + EloParams None→config) + 1 teste novo (63).
- **M4 v0.2: BRA 0,6146→0,6131 · ECE 0,0288→0,0224 · gap mercado −0,0195→−0,0180 · E0 idêntica dígito a dígito.** Sim 2026: Palmeiras 78,8→79,6%, Fla 20,7→19,6%.
- Rebuild obrigatório na máquina do Gustavo. Q-04/Q-05 (adoções E0) abertas.

## 2026-07-16 (j) — M6.6: regressão de temporada PASSA NO BRA (D-24) — 1º da liga-produto
- `scb/season_rho.py` (gate com rebuild por ρ, em etapas): BRA ρ*=0,30 → validação Δ1X2 +0,00216 IC[+0,00028,+0,00418], gols +0,00107 IC>0; E0 rejeitada (elencos estáveis). Caveats: IC inferior baixo; ρ na borda da grade (checar 0,4 na adoção).
- Q-06 aberta e RECOMENDADA como 1ª adoção (melhora o produto). Placar da fila: 6 testados — BRA 1 ✅ / E0 2 ✅ / 6 rejeições registradas.

## 2026-07-16 (i) — M6.5: Dixon-Coles passa na E0, rejeitado no BRA (D-23)
- `scb/dixon_coles.py` + 3 testes (62): τ(ρ) nas células de placar baixo, ρ na era de calibração, gate no canal de gols/empate. **E0: ρ=−0,05 (literatura), empate +0,00039 IC>0, sem regressão — 2º termo aprovado na E0.** BRA: ρ do treino (+0,05) regride na validação — instabilidade entre eras, rejeitado.
- Q-05 aberta (adoção DC-E0 exige 2º gate: re-blend do 1X2). Placar da fila: 5 testados; E0 com 2 aprovados; BRA com baseline limpo (0 aprovados, 5 rejeições honestas).

## 2026-07-16 (h) — M6.4: C1 descanso intra-liga rejeitado (D-22)
- `scb/descanso.py` + 3 testes (59): rest diferencial PIT com clip [2,8], β em grade. BRA e E0: IC cruza zero; kill-switch ok. Diagnóstico: rodadas simétricas INTRA-liga (\|diff\| ~0,7d) — a congestão real exige calendário externo (lacuna declarada). Placar da fila: 4 testados, 1 aprovado (mando rolling E0), 3 rejeitados com números.

## 2026-07-16 (g) — M6.3: PRIMEIRO TERMO A PASSAR UM PORTÃO NO SCB (D-21)
- `scb/mando_rolling.py` (ângulo novo da D-19): δ do mando por janela móvel PIT, inversão exata da curva Elo, cap ±60, zero parâmetro além de W. +3 testes (56).
- **E0 PASSA:** 1X2 +0,00180 IC[+0,00059,+0,00302] (n=6.080), gols +0,00066 IC>0, kill-switch −0,004; δ vigente −36,8 Elo (mando pós-COVID). **BRA rejeitado** (IC cruza; δ −12). Q-04: adoção na E0 = decisão do Gustavo (flag OFF até lá).
- Método validado ponta a ponta: rejeição da M6.1 apontou o ângulo; o portão separou liga com sinal (E0) de liga sem (BRA).

## 2026-07-16 (f) — M6.2 rejeitada · Q-03 fechada · M6.1-E0 rejeitada
- **D-20:** drift PIT do canal de gols (C3, família D-84 SCM) REJEITADO nas 2 ligas (IC cruza zero; kill-switch ok). `scb/drift.py` + `config.USE_MKT_DRIFT=False` + 3 testes (53 no total). Interpretação: o ganho do SCM vinha da estrutura por classe; liga única não tem.
- M6.1 na E0 (run do Gustavo): também rejeitada (T_base do treino regride gols) — D-19 completa nas 2 ligas.
- **Q-03 FECHADA por verificação web:** ordem CBF 2026 (vitórias→saldo→gols pró→confronto direto→cartões→sorteio) = a implementada; simplificações da D-18 seguem declaradas.
- Estado honesto da evolução: 2 candidatos testados, 2 rejeitados com números — baseline v0.1 segue o melhor modelo. Fila: M6.3 (mando rolling PIT), C1/C2/C4/C5/C6, banda.

## 2026-07-16 (e) — M5 FECHADA (oficial) + M6.1 rodada e REJEITADA (o portão protegeu)
- M5 oficial: 50 passed; tabela BRA 2026 na tela do Gustavo (Palmeiras 78,8%). Operação liberada ([[Operacao BRA 2026]]).
- M6.1 (`scb/calibrate.py`): grid estático de H_pred/T_base com era de validação separada → **REJEITADO (D-19)**: candidato do treino (H=120, T_base=2,20) piora gols na validação (IC<0). Causa: não-estacionariedade (mando ↓ pós-COVID, gols ↑ recentes) — regime inverte entre eras, calibração estática corrige ao contrário. Mesmo padrão D-25/D-40 SCM.
- Rota da M6: C3 (janela móvel PIT de gols — família aprovada no SCM D-84) e candidato novo "mando rolling PIT". Baseline v0.1 intacto.

## 2026-07-16 (d) — M4 FECHADA (oficial, números idênticos) + M5 pronta
- Run oficial da M4 reproduziu o sandbox dígito a dígito (47 passed; pipeline determinístico) → **`baseline-scb-v0.1` CONGELADO (D-17)**.
- M5: `simulate_league` (MC da temporada, fixtures derivadas, real travado, desempate D-18/Q-03), `predict_match` (porta da frente = backtest, D-34), `registrar` (imutável + settle ±2d + report power-aware), runbook [[Operacao BRA 2026]]. 3 testes (50 no total).
- E2E real BRA 2026 (rodada ~18): **Palmeiras 78,8% título · Flamengo 20,7% · Fluminense 0,4%; Chapecoense 100% Z4** — 5.000 sims em 3s, seed fixa.
- Q-02 fechada formalmente; Q-03 → Gustavo confirma ordem CBF; monitor de drift movido p/ M6/M7 (sem registros acumulados ainda, não há o que monitorar).

## 2026-07-16 (c) — M4: PORTÃO DO BASELINE PASSOU (sandbox; aguarda run oficial)
- `scb/backtest_harness.py`: walk-forward por temporada (burn-in 2), curva de empate POR FOLD (anti-vazamento), previsões on-the-fly, 4 réguas, Brier/LogLoss/RPS/ECE/banda, bootstrap pareado B=10k seed=12345 vetorizado. +5 testes (47 no total).
- **Resultados** ([[Backtest baseline (2026-07-16)]]): BRA n=4.736 Brier **0,6146** — bate uniforme (+0,0521), taxa-base (+0,0175) e Elo-puro (+0,0025), IC>0 em todos; E0 n=11.780 **0,5899** (+0,0767/+0,0530/+0,0052). Mercado (fechamento) à frente ~2pp nas duas — teto honesto. BRA > E0 em dificuldade, como a viabilidade previa. Banda sub-cobre extremos (padrão D-30 SCM) → M6. D-17 registrada.

## 2026-07-16 (b) — M3.4 (predictor) pronto: MOTOR COMPLETO aguardando run oficial
- `scb/predictor.py`: port fiel (piso conserva T_m D-22; propagação determinística por estratos D-30; A1; clamps; ensemble 0,56/0,44) com T_base POR LIGA (placeholder = medição M1) e leitura C1 via `draw_curve.ved_from_dr` (núcleo único D-43, ε do predictor). Fora: estilo/altitude/KO (D-06). Hooks: δ_ata (desfalques), perna AD com w_ad=0 (re-gate na liga, D-05). `MODEL_VERSION=scb-v0.1-baseline`.
- +8 testes (D-22, simetria, A1/btts matriz≡fechado, Jensen, determinismo, hook AD inerte, pipeline por liga com P(E) BRA>E0, idempotência/incremental). Harness **42/42**.
- E2E real: **18.200 previsões em 12,4s; soma=1 e bandas ok em 100%**; in-sample: BRA V 0,482/real 0,485 · E0 V 0,484/real 0,456 (H alto, já registrado) · over sobreprevisto +3-4pp (T_base, M6).
- Staleness do mount atrapalhou o harness (config.py velho) — contornado com injeção canônica; lição D-16 SCM reconfirmada.

## 2026-07-16 — M3.3 (curva de empate por liga) pronta
- `scb/draw_curve.py` (D-07): P_E(|dr|) empírica por liga do `match_ratings.dr` (PIT), bins com fusão por n≥200, interpolação linear, cap C1 e decomposição — P(V/E/D)∈[0,1] por construção; `--max-season` p/ o backtest reconstruir só com treino (anti-vazamento); freeze rastreável em `meta`.
- 6 testes novos (recupera taxa, soma=1 em dr∈[−800,800], interpolação, corte por temporada, roundtrip, **curvas diferem por liga**). Harness **34/34**.
- E2E real congelado: BRA n=5.496 (0,307→0,195) · E0 n=12.704 (0,296→0,148, cauda até |dr|~450). Nota honesta: diferença de ERA dentro da liga fica p/ o candidato C3.

## 2026-07-15 (g) — M3.1 FECHADA + M3.2 (features_pit) pronta
- M3.1 fechou no run oficial (21 passed; tops por liga conferidos).
- `scb/features_pit.py`: port com decay POR JOGO (liga é calendário denso), residual vs we (ajuste a adversário+mando), vol_mult (D-28), σ_ajuste=c·desvio, σ_dr RSS, modo incremental. Removidos: confed (D-06), glicko (D-05: re-propor só com ângulo novo), peso de amistoso (liga não tem).
- 7 testes novos — o portão do módulo é o **anti look-ahead** (jogo futuro não muda feature passada) + **incremental==full**. Harness 28/28.
- E2E real: 18.200 features em 20,8s; |forma| média 6,1 Elo; cap nunca furado; σ_dr méd 84 [40–283].

## 2026-07-15 (f) — M3.1 (elo_engine) pronto, aguarda run oficial
- `scb/config.py` (K/H por liga [a calibrar], SEASON_RHO=0 OFF) + `scb/elo_engine.py` (port: PIT em match_ratings, zero-sum, mando em todo jogo, hook C5 de virada de temporada no lugar do _revert de seleções) + 7 testes.
- Harness 21/21 (14 M2 + 7 novos). E2E real: 18.200 snapshots PIT, média 1500,00 exata por liga, 0,1s; tops fazem sentido (Palmeiras 1805/Flamengo 1765 · Arsenal 1893/City 1862).
- [medido p/ M6]: we_home médio 0,6191 vs pontuação real do mandante 0,5948 → H=100 sobreestima o mando de clube (calibrar no grid, não agora — baseline primeiro).

## 2026-07-15 (e) — M2 FECHADA (portão oficial passou)
- Run do Gustavo: `pytest -q` **14 passed em 0,19s** · `python -m scb.ingest` → **BRA 5.496 / E0 12.704** (aceite exato) · odds gravadas 11.150 (BRA, só close) + 27.400 (E0, open+close) · `dados/scb.sqlite` criado.
- M3 aberta: elo_engine → features_pit (+ curva de empate por liga) → predictor.

## 2026-07-15 (d) — M2 código pronto (aguarda run oficial do Gustavo)
- `scb/db.py` (schema liga: matches+league/season, odds_hist open/close, seasons, PIT pré-declaradas), `scb/ingest.py` (parser QA-01/02/03, idempotente, guarda ±2d, --dedup, extra), `scb/odds.py` (de-vig, blend ≤0,20, market_read com fallback D-16).
- 14/14 testes no harness isolado (sandbox sem PyPI → shim de pytest, mesma prática do SCM).
- E2E no snapshot real: **BRA 5.496 ✓ / E0 12.704 ✓** (bate o poc_m1_report), 2,2s; **BRA-2026: 177/177 jogos com fechamento via fallback** — Pinnacle morto não custa o CLV da temporada-alvo.
- Portão oficial da M2 = pytest + ingest na máquina do Gustavo.

## 2026-07-15 (c) — M1 FECHADA (portão passou)
- Run completo do Gustavo: BRA 5.497 jogos (2012–2026; 2016=379, interpretação Chapecoense a confirmar; 1 placar nulo em 2026), E0 12.704 (93/94+), **0 duplicatas / 0 aliases nas duas ligas**.
- Números-chave: BRA empate 26,8% / gols 2,40 · E0 moderno empate 18,7–24,5% / gols até 3,28 → curvas por liga confirmadas.
- **D-16:** Pinnacle closing 88% (2025) e 0% (2026) → benchmark de mercado por fallback PSC→AvgC→B365C. E0: fechamento completo desde 19/20; Pinnacle pré/close desde 12/13.
- M2 aberta (schema + ingest herdando parser + fixtures dos QA).

## 2026-07-15 (b) — M1 executada (em fechamento)
- Inventário estrutural do football-data com amostras reais: BRA desde 2012; **D-13: BRA.csv só traz FECHAMENTO** (corrige suposição do plano; nota no contrato §3.5, sem bump); E0 com abertura+fechamento+stats [medido].
- Criados: `scb_analytics/dados/notes.txt` (dicionário oficial versionado), `dados/leagues.json` v1, `scripts/poc_m1.py`, `dev/POC-M1-dados (2026-07-15).md`.
- D-14: Q-02 fechada (sem Kaggle; burn-in interno). D-15: layout `scb_analytics/` + dados versionados.
- Pendência única da M1: Gustavo rodar `poc_m1.py` (grades por temporada, duplicatas, aliases, empate/gols por era).
- 1º run do Gustavo achou **QA-01** (encoding latin-1 na E0 antiga) e **QA-02** (linhas de jogo descartadas em silêncio pelo parser); 2º run achou **QA-03** (header com colunas vazias/duplicadas → to_numeric quebrava). Corrigidos com parser determinístico via módulo `csv` (posição + descarte de coluna sem nome + sufixo em duplicata); **7/7 no harness isolado**. Re-run: `python scripts/poc_m1.py --offline`. Lição registrada: o ingest da M2 herda esse parser + os 7 casos como fixtures de teste.

## 2026-07-15
- **PLANO v1.0 e contrato SCB v1.0 CONGELADOS** — aprovação do Gustavo (D-11). Portão da Fase 1 passado.
- Vault adaptado ao Obsidian (D-12): wikilinks, frontmatter em todos os .md, `Indice.md` como nota-casa, `.obsidian/` mínimo, BACKLOG no formato do plugin Kanban.
- CONTEXT.md atualizado por substituição (estado: Fase 1 concluída → próximo M1).

## 2026-07-14
- Bootstrap do projeto (Fase 0–1). Kit criado a partir do estudo do zip `666666_SCM_DOCs` (contrato v5.0, D-01..D-85 SCM, viabilidade Brasileirão de 2026-06-28, busca de melhorias v3).
- Fonte football-data.co.uk verificada online (BRA.csv disponível, atualizado 2026-06-02 na página; página de 2026-07-06).
- Decisões de partida do Gustavo: port do scm_analytics (D-02), multi-liga E0+BRA (D-03), operar na temporada 2026 (D-10).
- D-01..D-10 registradas; Q-01..Q-03 abertas. PLANO.md escrito, **aguardando congelamento**.
