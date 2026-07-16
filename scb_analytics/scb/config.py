"""Parâmetros do modelo SCB — TODOS os [a calibrar] saem do backtest (M6), não de palpite.

Placeholders herdados do SCM/contrato até o grid; mudar valor calibrado = D-NN;
mudar FÓRMULA = bump de MODEL_VERSION (regra D-01/D-11).
M6.1 (D-19): grid ESTÁTICO de H/T_base REJEITADO pelo portão nas 2 ligas
(não-estacionariedade) — valores abaixo seguem os do baseline validado.
"""

# --- Elo (contrato §1) -----------------------------------------------------------
K_LIGA = {"default": 30.0}    # [a calibrar] K único por liga
H_LIGA = {"default": 100.0}   # [a calibrar] mando da liga (estático rejeitado D-19;
                              #   candidato M6.3: mando por janela móvel PIT)
SEASON_RHO = 0.0              # candidato C5 (0.0 = OFF até o portão)

# --- Gols (contrato §1) ----------------------------------------------------------
T_BASE_LIGA = {"BRA": 2.40, "E0": 2.70, "default": 2.6}   # placeholder medido M1

# --- Drift do canal de gols (M6.2 / C3, família D-84 SCM) -------------------------
USE_MKT_DRIFT = False         # ligar SÓ se o gate (python -m scb.drift) passar E a
                              # decisão de timing for tomada (D-NN); corrige over/BTTS
                              # na LEITURA (predict_match); 1X2 intocado por construção
DRIFT_W_DIAS = 3650.0

MODEL_VERSION = "scb-v0.1-baseline"


def k_for(league: str) -> float:
    return K_LIGA.get(league, K_LIGA["default"])


def h_for(league: str) -> float:
    return H_LIGA.get(league, H_LIGA["default"])


def t_base_for(league: str) -> float:
    return T_BASE_LIGA.get(league, T_BASE_LIGA["default"])
