"""Parâmetros do modelo SCB — TODOS os [a calibrar] saem do backtest (M6), não de palpite.

Histórico de calibração/portão (detalhe no DECISIONS do vault):
D-19 grid estático H/T_base REJEITADO (2 ligas) · D-20 drift gols REJEITADO (2 ligas) ·
D-21 mando rolling PASSA-E0 (adoção pendente Q-04) · D-22 descanso REJEITADO ·
D-23 Dixon-Coles PASSA-E0/empate (2º gate pendente Q-05) ·
**D-24/D-25 regressão de temporada ADOTADA NO BRA (ρ=0,30)** — 1ª adoção do produto.
"""

# --- Elo (contrato §1) -----------------------------------------------------------
K_LIGA = {"default": 30.0}    # [a calibrar] K único por liga
H_LIGA = {"default": 100.0}   # [a calibrar] mando da liga (estático rejeitado D-19)

# D-25 (Q-06): regressão do Elo à média na virada de temporada, POR LIGA.
# BRA = 0,30 [ADOTADO: valid Δ1X2 +0,00216 IC>0; 0,40 checado e descartado];
# E0 = 0 [rejeitado D-24: elencos estáveis]. Hook em elo_engine (M3.1).
SEASON_RHO = {"BRA": 0.30, "default": 0.0}

# --- Gols (contrato §1) ----------------------------------------------------------
T_BASE_LIGA = {"BRA": 2.40, "E0": 2.70, "default": 2.6}   # placeholder medido M1

# --- Drift do canal de gols (M6.2/C3) — REJEITADO (D-20), flag permanece OFF -------
USE_MKT_DRIFT = False
DRIFT_W_DIAS = 3650.0

# D-26 (Q-04): mando por janela móvel PIT, POR LIGA — ADOTADO na E0 (gate D-21:
# 1X2 +0,00180 IC>0; δ vigente ~−37 Elo). BRA rejeitado (fica 0). W=5a (gate).
MANDO_ROLLING = {"E0": True, "default": False}
MANDO_ROLLING_W = 1825.0

# D-27 (Q-05): Dixon-Coles — 2º GATE REJEITOU o re-blend do 1X2 na E0
# (Δ+0,00005 IC cruza; ganho do canal do empate dilui no ensemble — eco do D-39 SCM).
# Capacidade fica no predictor (dc_rho), TESTADA e OFF. ρ=0 ≡ Poisson puro.
DC_RHO = {"default": 0.0}

# D-33: SoT-total DESACOPLADO no canal de gols (over2.5/BTTS) — ADOTADO na E0.
# Gate: gols Δ+0,00133 IC[+0,00058,+0,00210]; 1X2/placar/ECE INTOCADOS (desacoplado);
# kill-switch corr −0,01 (independente do Elo). BRA = OFF (a fonte não traz chutes).
# δ_gols = clip(θ·(SoT-total PIT − baseline móvel PIT), ±1,0 gol), aplicado SÓ ao over/BTTS.
SOT_GOALS = {"E0": True, "default": False}
SOT_K = 10            # janela (jogos) do rolling de SoT-envolvimento [gate]
SOT_THETA = 0.08      # gols por unidade de desvio de SoT-total [gate]
SOT_BASE_L = 380      # janela (jogos) da baseline móvel PIT anti-deriva [gate]

MODEL_VERSION = "scb-v0.4-sot-goals-e0"  # v0.4: adoção D-33 (SoT-total no canal de gols,
                                         # E0). REBUILD OBRIGATÓRIO (over/BTTS mudam na E0).


def mando_rolling_for(league: str) -> bool:
    return MANDO_ROLLING.get(league, MANDO_ROLLING["default"])


def dc_rho_for(league: str) -> float:
    return DC_RHO.get(league, DC_RHO["default"])


def sot_goals_for(league: str) -> bool:
    return SOT_GOALS.get(league, SOT_GOALS["default"])


def k_for(league: str) -> float:
    return K_LIGA.get(league, K_LIGA["default"])


def h_for(league: str) -> float:
    return H_LIGA.get(league, H_LIGA["default"])


def t_base_for(league: str) -> float:
    return T_BASE_LIGA.get(league, T_BASE_LIGA["default"])


def season_rho_for(league: str) -> float:
    return SEASON_RHO.get(league, SEASON_RHO["default"])
