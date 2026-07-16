---
tags: [dev, m4, backtest, baseline, portao]
status: VALIDADO no sandbox (aguarda run oficial do Gustavo)
tipo: resultados
data: 2026-07-16
---

# Backtest do baseline `scb-v0.1` — PORTÃO PASSOU (walk-forward, 4 réguas)

> Método: walk-forward por temporada (burn-in 2), curva de empate reconstruída POR FOLD
> (`max_season`, sem vazamento), IC 95% bootstrap pareado B=10.000 seed=12345.
> Constantes = placeholders ex-ante [a calibrar M6]. Reproduzir: `python -m scb.backtest_harness`.

## Veredito

| Liga | n (teste) | Brier | vs uniforme (0,667) | vs taxa-base | vs Elo-puro | vs mercado (close) |
|---|---|---|---|---|---|---|
| **BRA** | 4.736 (13 temporadas) | **0,6146** | **+0,0521** IC[+0,0431,+0,0611] ✅ | **+0,0175** IC[+0,0108,+0,0241] ✅ | **+0,0025** IC[+0,0011,+0,0038] ✅ | −0,0195 IC[−0,0240,−0,0151] (régua 0,5951) |
| **E0** | 11.780 (31 temporadas) | **0,5899** | **+0,0767** IC[+0,0698,+0,0835] ✅ | **+0,0530** IC[+0,0475,+0,0587] ✅ | **+0,0052** IC[+0,0041,+0,0063] ✅ | −0,0176 IC[−0,0215,−0,0136] (n=5.320; régua 0,5655) |

- **Baseline VALIDADO:** bate uniforme E taxa-base com IC>0 nas duas ligas (o aceite da M4) — e também o **Elo-puro** (forma+Poisson+ensemble acrescentam skill real; mesma ordem do SCM: +0,0028/+0,0037).
- **Mercado à frente ~2pp de Brier nas duas ligas** — o teto honesto, como previsto na viabilidade ("Brier ~0,60 não é vantagem"). O gap é a régua de evolução da M6, não meta a bater.
- **BRA mais difícil que E0** (0,615 vs 0,590) — confirma o estudo de viabilidade (liga equilibrada). A taxa-base do BRA é forte (0,632) e ainda assim o modelo a supera.

## Calibração e banda

ECE: BRA 0,0288 · E0 0,0365 (bom p/ baseline sem recal). LogLoss 1,025/0,990 · RPS 0,210/0,202. Over2.5/BTTS Brier ~0,245-0,251 (canal de gols — candidato C3 atua aqui).

**Banda sub-cobre nos EXTREMOS** (BRA 5/8, E0 6/10 faixas dentro): favoritos fortes observam MENOS vitória que a banda promete (ex.: E0 [0,8-0,9): obs 0,774 vs banda [0,826-0,921]) e azarões observam MAIS. Mesmo padrão do SCM (D-30/D-47: superconfiança na ponta; encolher σ_dr não resolveu lá). → **Insumo M6**: calibrar banda/σ_dr por faixa; e H alto (M3.1) explica parte da ponta.

## Decisão

**D-17: baseline `scb-v0.1` CONGELADO** (após confirmação oficial). Evolução daqui = fila do portão (C1–C6, M6) sobre este número — cada termo com ΔBrier pareado IC>0 + guardas, como manda o contrato §4.
