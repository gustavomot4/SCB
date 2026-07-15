---
tags: [contexto, modelo, contrato, congelado]
status: CONGELADO — contrato SCB v1.0 (aprovado em 2026-07-15, D-11)
tipo: especificacao
data: 2026-07-15
---

# Modelo matemático do SCB — contrato v1.0 (CONGELADO)

> Base: contrato **v5.0 do SCM** (`camada1-planejamento-v5` + apêndice de formas) e evolução validada até `baseline-v0.5.1-confed` (D-01..D-85). Este doc diz **o que fica, o que sai, o que recalibra e o que é candidato** ao portar de Copa (seleções, mata-mata) para **liga de clubes em pontos corridos**. Todo número marcado **[a calibrar]** sai do backtest, nunca de decreto; todo valor esperado sobre a liga marcado **[a medir na M1]** é confirmado na POC de dados — **não inventar**.
> **CONGELADO como contrato SCB v1.0 em 2026-07-15 (D-11).** Mudar fórmula daqui em diante = nova versão (`MODEL_VERSION`) + D-NN — nunca edição silenciosa. Preencher um [a calibrar]/[a medir] com valor MEDIDO não é mudança de fórmula (registrar no [[DECISIONS]] mesmo assim).

## 0. Princípio (herdado e reafirmado)

A V1 do SCB é o **motor mínimo que se sustenta sozinho**: Elo → dr → λ → Poisson → ensemble, com incerteza propagada. Sofisticação só entra **medida** (portão: ΔBrier pareado, IC bootstrap que não cruza zero). Lição central do SCM a lembrar sempre: **o núcleo Elo→Poisson chega ao teto rápido (~12 rejeições no portão); os ganhos reais vieram de sinal novo INDEPENDENTE do `dr` e de operar/medir** — em liga, o maior sinal independente novo são as **odds históricas** (que a Copa não tinha de graça).

## 1. Núcleo que TRANSFERE INTACTO (formas fixas; coeficientes recalibram)

| Bloco | Fórmula (inalterada) | O que recalibra p/ liga |
|---|---|---|
| **Elo** | `R_novo = R + K·G·(W − W_e)`; `W_e = 1/(1+10^(−dr/400))` | `K` único por liga **[a calibrar]** (era 60/50/40/30/20 por tipo de torneio de seleção; clube joga ~2×/semana → K menor; grid no backtest). Família `G` por margem mantida, re-gate |
| **dr** | `dr = R'_A − R'_B + H` | `H` = mando da liga (ver §3.1) — agora presente em **todo jogo** |
| **Forma recente** | `ΔE_forma = 15·(PPJ_pond − PPJ_esp)`, cap ±30 | recência: decay **por jogo** (0,9^k na janela de 10) em vez de por mês — calendário de clube é denso; escolher no backtest **[a calibrar]**. `PPJ_esp` usa a curva de empate da liga |
| **Saldo** | `GD = f(dr)`; `f_linear = θ·dr/100` (ou `tanh` saturante) | `θ` **[a calibrar]** (placeholder 0,45 do SCM até o grid). Em liga \|dr\| raramente extrapola — tail menos crítico |
| **Total** | `T_m = g(dr)`; `g_linear = T_base + κ·|dr|/100` | `T_base`, `κ` **[a calibrar por liga]**. T_base da Copa era 2,6; nível de gols do Brasileirão é outro **[a medir na M1]** |
| **λ** | `λ_A = (T_m+GD)/2`; `λ_B = (T_m−GD)/2`; piso λ_min **conserva T_m** (D-22) | intacto |
| **Poisson** | matriz `M[i][j] = Pois(i;λ_A)·Pois(j;λ_B)`, 0..10, resíduo na borda | intacto; mercados = releituras da MESMA matriz (D-21), zero g.l. novos |
| **Curva de empate C1** | forma fixa: cap `2·min(W_e,1−W_e)−ε`; `pv = we − pe/2`; `pd = 1−pv−pe` | a **tabela empírica `P_E(|dr|)` é POR LIGA** — congelada do histórico da própria liga (ver §3.2). Não usar a tabela do martj42 (seleções) |
| **σ_dr e propagação** | `σ_dr = √(σ_R_A² + σ_R_B² + σ_aj_A² + σ_aj_B² + banda_mando²)`; MC `dr ~ N(dr, σ_dr)`; banda = percentis 16/84 | intacto (RSS aproximação declarada); componentes de σ_ajuste re-gateiam (§4) |
| **Perna AD (Maher, não-Elo)** | prior de gols independente do `dr`, peso `w_ad` | transfere; com 38 jogos/time por temporada tende a **melhorar** (mais dado de gols por time); `w_ad` **[a calibrar]** (era 0,50) |
| **Ensemble** | clamp por leitura [0,02, 0,96] → pool ponderado → clamp final | pesos **[a calibrar por liga]** (eram 0,45/0,35/0,20); mercado ≤ 0,20 (D-08 herdada; Q-01 aberta) |
| **Confiança** | `100 · reliab(p_max) · maturidade(σ_R)` (D-20) | curva `reliab` recalibrada no backtest da liga |
| **Validação** | Brier (forma-soma) + LogLoss + RPS + ECE + cobertura de banda; IC bootstrap B=10k seed fixa | split muda: **walk-forward por temporada** (§5) |

## 2. O que SAI (específico de Copa/seleções)

| Bloco | Por que sai | Destino |
|---|---|---|
| Altitude (D-18) | McSharry mede diferencial >1500–2000 m (CONMEBOL andina); diferenciais dentro do Brasil não chegam lá | módulo fica no código, **OFF**; reativável p/ liga andina no futuro |
| Força por confederação (D-79/81) | uma liga = um pool único de Elo; o problema de escala entre pools não existe | remover do pipeline |
| Mando "+40 anfitrião / 0 neutro" | em liga TODO jogo tem mando real | substituído pelo `H` da liga (§3.1) |
| `knockout_advance`, ε de pênaltis (D-75), bracket FIFA, `copa2026.json`, desempates de mata-mata (D-80/83/85) | não há mata-mata em pontos corridos | substituídos pelo simulador de liga (§3.3) |
| Tempo do gol (D-71) | curva veio do StatsBomb de seleções; football-data não traz minuto de gol | **lacuna declarada**; mercado de tempo do gol fica fora até existir dado grátis |
| K por tipo de torneio | uma competição só na V1 | K único **[a calibrar]** |

## 3. O que MUDA / é NOVO em liga

### 3.1 Mando de campo — de juízo declarado a termo central medido
No SCM o mando era quase sempre 0 (sede neutra) e o `+40` do anfitrião era juízo declarado. Em liga o mando é o **termo contextual mais importante**:
```
dr = R'_A − R'_B + H_liga          H_liga [a calibrar] no backtest da própria liga
banda_mando = ±b Elo → σ_dr        b [a calibrar]
```
- Referência herdada: H empírico de seleções ≈ 110–120 Elo (D-47); o da liga sai do fit **[a medir na M1/M3]**.
- **Candidato (portão):** H por clube com shrinkage forte para o H da liga — risco clássico de overfit; só com IC>0.
- **Candidato (portão):** decomposição viagem/distância (§4.3) — Brasil continental é o caso de uso real.

### 3.2 Curva de empate POR LIGA (obrigatório, não candidato)
A tabela `P_E(|dr|)` do SCM foi congelada do martj42 (seleções). Liga de clubes tem regime de empate próprio (Brasileirão é historicamente empatador **[a medir na M1]**). Reconstruir a curva empírica **da própria liga**, point-in-time, congelar com a versão do modelo — mesma receita da D-26. Sem isso o P(E) sai sistematicamente errado.

### 3.3 Simulador de PONTOS CORRIDOS (substitui `simulate.py` de Copa)
Monte Carlo dos jogos restantes da temporada, amostrando placares da Poisson do modelo (λ com blend da perna AD, herdando `SIM_AD_BLEND`), com σ propagado e seed fixa:
```
Saídas por clube: P(título) · P(G4) · P(G6) · P(Z4) · distribuição de pontos e posição · pontos esperados
```
- **Desempate parametrizado por liga** (lição D-52/80: regra de desempate errada = chaveamento errado): Brasileirão = vitórias → saldo → gols pró → confronto direto → … (confirmar regulamento CBF vigente na implementação **[a verificar na M5]**); Premier = saldo → gols pró → …
- **Jogos já disputados travados como verdade** (herda a disciplina D-83/85: a realidade antes da estatística).
- Rodada em andamento com lag de fonte → `resultados_extra.csv` manual idempotente (herda D-80/82).

### 3.4 Temporadas: virada de ano e promovidos (NOVO — seleções não têm isso)
1. **Regressão entre temporadas [candidato ao portão]:** clube brasileiro troca elenco/técnico em massa na virada; prática padrão de club-Elo é regredir x% ao meio da tabela no início da temporada. `R_inicial = (1−ρ)·R_final + ρ·R̄_liga`, ρ **[a calibrar, portão]**; σ_R sobe na virada (isso é ajuste de σ, entra sem portão de Brier se melhorar cobertura de banda).
2. **Promovidos (cold start):** 4 sobem da Série B (E0: 3 da Championship) sem histórico na base. Inicialização: Elo regredido ao piso da liga **[a calibrar]** + σ_R alto (provisório, como estreante no SCM). **Candidato:** prior manual pela posição final na divisão de baixo (tabela pública, R$ 0, entrada manual — não inventar).
3. **Troca de técnico → σ_R bump, não bounce** (Ter Weel, herdado do contrato v5 E7): entrada manual JSON (Brasileirão troca técnico o tempo todo); candidato C3, mesma família dos desfalques.

### 3.5 Odds automáticas — a maior melhoria estrutural vs SCM
O football-data traz **1X2 de abertura E fechamento** por jogo, grátis, no mesmo CSV de resultados. Isso resolve a lacuna nº 1 do SCM (3 buscas de melhoria seguidas apontaram CLV em zero por captura manual):
- **3ª perna do ensemble com série histórica** → o peso do mercado pode ser **calibrado no backtest pela 1ª vez** (no SCM era 0,20 declarado). Teto 0,20 mantido (D-08) até decisão consciente (Q-01).
- **CLV automático:** `monitor` compara modelo × linha de fechamento sem captura manual. A pergunta "há edge vs fechamento?" — que a Copa deixou morrer sem resposta — aqui **nasce respondível**.
- **Benchmark honesto do backtest:** mercado de-vigged (de-vig proporcional herdado de `odds.py`) de abertura e fechamento entram como réguas fixas do harness, ao lado do uniforme e da taxa-base da liga.
- Pinnacle instável no football-data desde 07/2025 → usar bet365/média das casas **[a confirmar colunas na M1]**.

> **Nota M1 (2026-07-15, D-13 — correção de FATO, não de fórmula; sem bump):** o `BRA.csv` traz **só a linha de FECHAMENTO** (PSC/MaxC/AvgC/BFEC/B365C [medido]); abertura não existe na família extra. Portanto: CLV e régua de mercado do backtest seguem automáticos (até mais fortes — fechamento é o teto); a **perna de mercado do ensemble em produção pré-jogo do BRA é manual/opcional** (herda `odds_close`), e no backtest usa o fechamento rotulado como teto. Na E0 há abertura E fechamento [medido] — ela mede o gap abertura×fechamento e calibra o juízo. O ensemble em si não muda (pesos com/sem odds já previstos, §1).

### 3.6 Desfalques direcionais — transfere + melhora possível
Mecânica intacta (tier −35/−15/−5 por setor; ataque corta λ_pró, defesa/goleiro via dr; dúvida → σ_ajuste; JSON manual). Em liga, **suspensões por cartão são previsíveis** (3 amarelos/vermelho) — mas o BRA.csv não traz cartões (formato extra) → segue entrada manual; nas ligas main (E0) há cartões por jogo, o que abre o candidato "suspensão projetada" **atrás do portão** quando chegarmos lá.

## 4. CANDIDATOS ao portão (fila inicial, com prior honesto herdado do SCM)

> Regra D-05: a lista-morta do SCM **não transfere** — cada termo re-passa pelo portão na liga. Prior informa a ordem da fila, não o veredito.

| # | Candidato | Prior (evidência SCM) | Por que pode passar em liga | Canal do portão |
|---|---|---|---|---|
| C1 | **Descanso/congestão diferencial** | morto p/ seleções (corr resíduo 0,0005 — calendário simétrico) | clube joga qua/dom + Libertadores/Copa do Brasil; congestão REAL. Fase 1 só com descanso intra-liga (datas no próprio CSV); calendário externo é lacuna declarada | σ_ajuste primeiro (evidência é fadiga); λ só com IC>0 |
| C2 | **Dixon-Coles (τ placares baixos)** | rejeitado em seleções (D-39, ρ=−0,06 piorava BTTS) | habitat original do DC é liga de clubes; placares baixos mais frequentes e correlacionados | Brier de BTTS/placar exato + guarda 1X2 |
| C3 | **Drift PIT do canal de gols (janela móvel)** | família APROVADA no SCM (D-84: over +0,0025, BTTS +0,0021 IC>0) | nível de gols da liga também deriva por era; em liga a "classe" colapsa → correção por liga-temporada, mesma receita | Brier over2.5+BTTS; 1X2 intocado por construção |
| C4 | **Viagem/distância** (não fuso: Brasil é ~1 fuso útil) | fuso morto p/ seleções; km era métrica errada (E5) | distâncias continentais reais (POA→FOR ~3.000 km); coordenadas estáticas R$ 0 | σ_ajuste; λ só com IC>0 |
| C5 | **Regressão entre temporadas (ρ)** | inexistente no SCM (sem temporadas) | churn de elenco brasileiro é dos maiores do mundo | Brier 1X2 nas primeiras N rodadas da temporada + cobertura de banda |
| C6 | **H por clube (shrinkage)** | não testado (mando era ~0 na Copa) | mandos notoriamente heterogêneos no Brasil | Brier 1X2 + guarda de ECE; shrinkage forte obrigatório |
| C7 | **xG como prior da perna AD** | marginal/rejeitado no SCM (D-50: redundante com AD) | sem fonte grátis estruturada p/ BRA (FBref é ToS-restrito; StatsBomb não cobre) → **lacuna declarada**; reavaliar só se surgir fonte | — |

**Proibido re-propor sem ângulo novo** (herdado da busca v3): recalibração estática de T/λ (o sinal inverte entre eras — é exatamente o que o C3 resolve), σ-Glicko, σ_dr-scaling, calor, estilo shrinkage.

## 5. Validação e portão (adaptados a liga)

- **Split: walk-forward por temporada** (rolling origin): treina temporadas 1..k, testa k+1; repete. Substitui o corte fixo <2015/≥2015 do SCM — mais honesto com churn de elenco e não-estacionariedade de liga. IC bootstrap pareado B=10.000, seed=12345, vetorizado (D-15).
- **Baselines do harness (4 réguas):** uniforme (Brier 0,667) · **taxa-base da liga** (frequências históricas 1X2 — régua "climatológica" que a liga equilibrada exige) · Elo-puro interno (D-27) · **mercado de-vigged** (abertura e fechamento).
- **Milestone de aceite do baseline (portão da M4):** Brier < uniforme E < taxa-base com IC que não cruza zero; ECE reportado; banda com cobertura nominal por faixa; P(V/E/D) ∈ [0,1] por construção; confiança não-crescente com σ_dr; distância ao mercado **reportada honestamente** (não é meta batê-lo).
- **Expectativa honesta (do estudo de viabilidade):** Brasileirão é equilibrado → Brier mais alto e edge menor que na Europa. O modelo vai rodar e ser honesto; o juiz é o mercado que agora vem de graça. Validar o port primeiro na **E0** (dado rico/longo) isola "bug de port" de "dificuldade da liga".

## 6. Outputs da V1 (produto)

P(V/E/D) + banda 16/84 · λ_A/λ_B · mercados derivados (D-21: over/under 0,5–4,5, BTTS, totais por time, clean sheet, dupla chance, handicap, quem marca 1º, placares top-5 + "chance de NÃO ser o modal") · confiança (0–100 + rótulo) · **simulação da tabela** (P(título/G4/G6/Z4), pontos esperados, distribuição de posição) · explicador do dr (Elo/forma/mando/desfalque) · registro prospectivo + report por rodada + monitor de drift + CLV vs fechamento.

## 7. Riscos declarados (honestos, herdados + novos)

Amostra por temporada é pequena (380 jogos) → portões por temporada são sub-powered; agregue temporadas e diga quando o IC cruza. Formato "extra" do BRA.csv não tem chutes/escanteios/cartões → mercados de cartão/escanteio ficam fora (lição D-72: sem dado, sem sinal). Histórico do BRA.csv é mais curto que o das ligas main **[a medir na M1]** → Elo demora a convergir; mitigação candidata: aquecer o Elo com dataset Kaggle 2003+ (sem odds, só resultados) **[decidir na M1, D-NN]**. Liga equilibrada = teto de skill baixo — Brier ~0,60 não é vantagem (herdado). Fonte atualiza semanalmente → na rodada em andamento, resultados manuais (D-80) + guarda anti-duplicata (D-82). Calendário externo (Libertadores/Copa do Brasil) não vem no CSV → congestão parcialmente observada, declarado no C1.
