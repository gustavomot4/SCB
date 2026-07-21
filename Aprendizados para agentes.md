---
tags: [scb, aprendizados, agentes, meta]
status: vivo
tipo: aprendizados
data: 2026-07-21
---

# Aprendizados para agentes — o que seguir, o que evitar (honesto)

> Escrito por um agente ao fim de uma leva de trabalho no SCB, para os próximos — neste
> projeto e em outros parecidos (sistema local, gratuito, orientado a dado, com um dono
> não-programador). Sem verniz: inclui os erros que **eu** cometi.

## O que fez este projeto funcionar (SEGUIR)

**1. O portão de backtest é sagrado — e rejeitar É o portão funcionando.** Nenhum termo entra
no modelo sem ΔBrier pareado, IC bootstrap que não cruza zero, guardas de não-regressão e
kill-switch de correlação. Na evolução foram ~7 rejeições para 2 adoções. Isso não é fracasso:
é o portão barrando ideias plausíveis-mas-inúteis. O proxy de xG (SoT) parecia ótimo no gate-0
e foi rejeitado em dois canais antes de achar o ângulo que passava. Resista a adotar "porque
faz sentido" — só passa quem bate o número.

**2. Registro append-only com o PORQUÊ (D-NN).** Toda decisão vira uma linha nova com a razão;
reversão cita a antiga, nunca edita. Foi isso que deixou retomar sessões sem re-discutir tudo.
Decidiu algo? Registre — inclusive quando DESFAZ (a artilharia entrou e saiu; virou D-40).

**3. CONTEXT ≤ 1 página, por substituição.** O "presente" mora num lugar só; o histórico vai
pro CHANGELOG. Contexto pequeno = sessão focada. Não deixe o CONTEXT virar diário.

**4. Nunca invente dado — lacuna declarada fica declarada.** Quando o football-data não tinha
stats do BRA, não se chutou: declarou-se a lacuna e depois achou-se uma 2ª fonte real. Quando a
API não traz o placar, o loader PULA (não insere resultado inventado). Essa regra é o que dá
confiança no sistema inteiro — uma única invenção contamina tudo.

**5. Verifique contra a realidade antes de confiar.** Antes de construir o painel de calibração,
conferi o cálculo do Brier contra o número já conhecido do backtest (0,5894). Bateu → confiança.
Não assuma que sua conta está certa; ancore num valor já validado.

**6. Honestidade acima de impressionar.** Falei pro dono que a artilharia agrega pouco, que o
modelo fica ATRÁS do mercado (não à frente), que o ganho entre versões é mínimo. Ele confia MAIS
por causa disso, não menos. Uma tela que mostra a fraqueza (Calibração) vale mais que uma bonita
que a esconde.

## O que evitar (armadilhas — várias eu caí)

**1. Não suponha o schema de uma API sem ver uma resposta real.** Eu DUVIDEI que a API-Futebol
tivesse chutes/escanteios — e estava errado; uma chamada de jogo terminado provou que tinha.
Depois acertei: pedi ao dono uma amostra do `/artilharia` antes de escrever o parser. Olhe o
payload de verdade primeiro — vale para APIs, conectores e artifacts.

**2. "Barato" não é "valioso".** A artilharia era 1 chamada com o dado na mão — barata — mas
exibição pura, zero valor preditivo num sistema de PREVISÃO. Eu sugeri; o dono cortou, com razão.
Não encha o sistema de features só porque são fáceis. Pergunte "isso muda alguma decisão/número?"

**3. Salve progresso incrementalmente; trate limites de taxa.** Refatorei o coletor para "gravar
no fim" e um 429 no meio do loop PERDEU os jogos já baixados. Consertei com `try/finally` (grava
sempre) + tratar o 429 (para com elegância, retoma amanhã). Erro ou corte nunca deve descartar
trabalho já feito.

**4. Conheça os limites do sandbox — o dono roda a rede.** O sandbox não escreve no SQLite
montado (lock de disco → contornado com escrita binária + `fsync`), não chama APIs externas, não
apaga arquivo montado sem permissão. Escreva código PURO e testável; os passos de rede/pipeline
rodam na máquina do dono. Planeje para isso desde o início.

**5. "Está quebrado" vs "falta dado".** O "Liquidar resultados" não liquidava nada — parecia
bug, era falta de dado (os resultados ainda não estavam no banco). Cheque o estado do dado antes
de caçar bug no código; poupa horas.

**6. Recurso perecível: gaste no transformador, não no marginal.** No trial de 7 dias da API, o
valor real era backfillar temporadas passadas (destravaria um termo de modelo do BRA), não pegar
mais um stat de exibição. Mas seja honesto quando o transformador está bloqueado (as temporadas
passadas não vinham no grátis — a gente não forçou nem fingiu que dava).

**7. Servidor em execução tem cache.** Com `debug=False` o Flask não recarrega; mudança de código
só vale depois de reiniciar o processo. Não presuma que o dono está vendo sua alteração ao vivo —
diga para reiniciar + Ctrl+F5.

**8. Um ganho numa liga NÃO transfere para outra.** Mando rolling e Dixon-Coles passaram na
Premier e falharam no Brasileirão (o churn de elenco é fenômeno brasileiro; o mando caiu pós-COVID
na Europa). Re-rode o portão POR LIGA; o contexto do dado muda.

## Verdades honestas sobre o modelo (não romantize)
- É bem calibrado (ECE ~1-2%) mas fica **atrás do mercado**, fechando só 50-78% da distância
  chute→mercado. É um Elo local e grátis, não um oráculo.
- Os ganhos entre versões são **marginais** (frações de milésimo de Brier) — reais (o portão
  garante), mas pequenos. Não venda como revolução.
- O maior salto possível (termo de SoT/xG no BRA) está **bloqueado por falta de histórico grátis**.
  Diga isso; não finja que está logo ali.

## Como trabalhar neste repo (prático)
- Comece por [[CONTEXT]] + o prompt do papel ([[00-bootstrap-contexto]] … [[05-revisao-entrega]])
  + só o arquivo do momento. Peça um **delta**, não reescreva do zero (D-02: o port existe
  justamente para não repagar bugs já resolvidos).
- Código novo = teste (inclusive PIT/anti-look-ahead). Mudança de fórmula = bump de
  `MODEL_VERSION` → rebuild obrigatório na máquina do dono.
- Nomes de time no padrão football-data (EN) internamente; **"PRE" é só display** (o código é
  `E0`, e dados/modelo dependem disso).
- Termine entregando os arquivos, resposta concisa, e — se decidiu algo — registre o **D-NN** e
  atualize o [[CONTEXT]] por substituição. O datado vai pro [[CHANGELOG]].

## A meta-lição
O que torna este projeto bom não é esperteza — é **disciplina que compõe**: portão que barra,
registro que lembra, honestidade que não precisa ser desfeita depois. É mais lento no dia, e
muito mais rápido no mês. Trabalhe para o dono conseguir confiar no sistema (e em você) sem ter
que conferir cada linha.
