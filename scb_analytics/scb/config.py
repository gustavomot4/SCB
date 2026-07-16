"""Parâmetros do modelo SCB — TODOS os [a calibrar] saem do backtest (M6), não de palpite.

Placeholders herdados do SCM/contrato até o grid: mudar valor calibrado = registrar no
DECISIONS; mudar FÓRMULA = bump de MODEL_VERSION (regra D-01/D-11).
"""

# --- Elo (contrato §1; port do scm/config) -------------------------------------
K_LIGA = {"default": 30.0}    # [a calibrar M6] K único por liga (clube joga ~2x/semana;
                              # o K por tipo-de-torneio era coisa de seleção — contrato §2)
H_LIGA = {"default": 100.0}   # [a calibrar M6] mando da liga, presente em TODO jogo
                              # (referência herdada: empírico de seleções ~110-120, D-47 SCM)

# Candidato C5 (contrato §3.4) — regressão do Elo à média na VIRADA de temporada.
# OFF até passar o portão (0.0 = no-op). Substitui o `_revert` do SCM (rejeitado lá
# p/ seleções; em liga a variante certa é por TEMPORADA, não por meses parado — D-05).
SEASON_RHO = 0.0              # [candidato ao portão M6] fração puxada rumo a 1500


# --- Gols (contrato §1: T_base/θ/κ [a calibrar M6]) ------------------------------
# T_base por liga: placeholder = gols/jogo MEDIDO na M1 (melhor que o 2,6 da Copa);
# o grid da M6 refina (o κ·E|dr| embutido na média é absorvido lá).
T_BASE_LIGA = {"BRA": 2.40, "E0": 2.70, "default": 2.6}

MODEL_VERSION = "scb-v0.1-baseline"   # bump SÓ com mudança de fórmula (D-01/D-11)


def k_for(league: str) -> float:
    return K_LIGA.get(league, K_LIGA["default"])


def h_for(league: str) -> float:
    return H_LIGA.get(league, H_LIGA["default"])


def t_base_for(league: str) -> float:
    return T_BASE_LIGA.get(league, T_BASE_LIGA["default"])
