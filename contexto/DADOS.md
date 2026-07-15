---
tags: [contexto, dados, fontes, schema]
status: atual
tipo: dados
data: 2026-07-14
---

# Dados do SCB — fontes, esquema-alvo e lacunas declaradas

> Regra herdada: tudo público/gratuito, snapshot local, **nada lê a internet no momento do cálculo**. Download é passo à parte. Tudo marcado **[a medir na M1]** é confirmado na POC de dados — inventário real de colunas/temporadas antes de qualquer schema definitivo.

## 1. Fontes (R$ 0)

| Fonte | Dado | Papel | Limite honesto |
|---|---|---|---|
| **football-data.co.uk — família EXTRA** (`new/BRA.csv`) | resultados Série A + odds 1X2 (abertura e fechamento), over/under, AH | **fonte primária do Brasileirão**: base do Elo, V/E/D realizado, mercado do ensemble, CLV | formato reduzido: **sem** chutes/escanteios/cartões; histórico mais curto que as ligas main [a medir na M1]; atualização semanal (lag na rodada); Pinnacle instável desde 07/2025 → bet365/média [confirmar na M1]; arquivo único multi-temporada (coluna Season) |
| **football-data.co.uk — família MAIN** (`E0.csv` por temporada) | Premier League: resultados + odds ~10 casas + chutes/escanteios/cartões/faltas, desde 1993 | **liga de validação do port** (dado rico e longo); candidatos extras (suspensão projetada) | páginas por temporada (1 CSV/ano) |
| `notes.txt` do football-data | dicionário oficial das colunas | contrato do parser | ler na M1 e versionar no repo |
| **Kaggle — Campeonato Brasileiro** (adaoduque) / openfootball | resultados históricos longos, sem odds | **candidato** p/ aquecer o Elo pré-odds [decidir na M1 → D-NN] | qualidade/dedup a auditar; sem odds |
| Tabelas públicas da Série B (posição final) | prior manual de promovido | cold start (contrato §3.4) | entrada manual, 4 linhas/ano |
| Coordenadas das cidades-sede (estático) | distância de viagem | candidato C4 | tabela curada 1× no repo |
| Calendário de outras competições (Libertadores/Copa do Brasil/estaduais) | congestão total | candidato C1 (fase 2) | **lacuna declarada**: não vem no football-data; fonte grátis estruturada a definir — até lá, congestão = intra-liga |

**Lacunas declaradas (não inventar):** escalações/lesões estruturadas grátis (desfalques seguem JSON manual) · xG do Brasileirão (FBref é ToS-restrito → consulta manual apenas; StatsBomb não cobre) · minuto do gol (mercados de tempo ficam fora) · cartões/escanteios do BRA (mercados ficam fora — lição D-72).

## 2. Colunas esperadas do football-data (validar contra `notes.txt` na M1)

```
Country, League, Season, Date, Time, Home, Away, HG, AG, Res        # família EXTRA (BRA)
Div, Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR, HTHG, HTAG, ...     # família MAIN (E0)
Odds: PSH/PSD/PSA (Pinnacle), B365H/D/A, MaxH/D/A, AvgH/D/A ...     # abertura
      PSCH/PSCD/PSCA, B365CH/CD/CA, MaxCH..., AvgCH...              # fechamento (C = closing)
```
O parser é **um por família** (extra/main), parametrizado por liga num `leagues.json` (nome, arquivo/URL, nº de clubes, vagas G4/G6/Z4, regra de desempate, janelas da temporada).

## 3. Esquema SQLite alvo (delta sobre o schema do SCM)

```
teams(team_id, name, city, country)                                  -- sem confederation/altitude
matches(match_id, league, season, round?, date, home_team_id, away_team_id,
        home_score, away_score, natural_key)                         -- + league, season
odds_hist(match_id, source, stage,                                   -- stage: 'open' | 'close'
          p_home, p_draw, p_away)                                    -- de-vigged; brutas ficam no snapshot
ratings_current / match_ratings / match_features / predictions / meta -- iguais ao SCM (PIT preservado)
seasons(league, season, start_date, end_date)                        -- virada de temporada (regressão ρ)
```
Restrições da stack declaradas no schema (lição SPO): SQLite sem enum → `stage`/`league` são TEXT com CHECK; datas ISO-8601 TEXT; probabilidade REAL em [0,1].

## 4. POC de dados (M1) — o que ela precisa responder

1. Inventário real: temporadas cobertas, nº de jogos, colunas presentes por temporada (odds de fechamento existem desde quando?) — BRA e E0.
2. Qualidade: duplicatas (rodar o detector ±2d), placares nulos, times renomeados entre temporadas (mapa de aliases).
3. Taxa de empate e gols/jogo por liga e por era (alimenta curva de empate e T_base [a calibrar]).
4. Decisão D-NN: aquecer Elo do BRA com Kaggle (sim/não, com evidência de qualidade).
5. Snapshot versionado no repo (D-78): CSVs curados + `notes.txt`; `.gitignore` ignora só `*.sqlite`/`*.png`.
