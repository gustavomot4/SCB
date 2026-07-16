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

MODEL_VERSION = "scb-v0.2-rho-bra"   # v0.2: 1ª adoção (D-25). REBUILD OBRIGATÓRIO:
                                     # elo_engine + features_pit + draw_curve + predictor


def k_for(league: str) -> float:
    return K_LIGA.get(league, K_LIGA["default"])


def h_for(league: str) -> float:
    return H_LIGA.get(league, H_LIGA["default"])


def t_base_for(league: str) -> float:
    return T_BASE_LIGA.get(league, T_BASE_LIGA["default"])


def season_rho_for(league: str) -> float:
    return SEASON_RHO.get(league, SEASON_RHO["default"])
