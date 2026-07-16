"""M6.5 — Dixon-Coles: ρ=0 ≡ baseline, matriz soma 1, sinal do τ com ρ<0."""
import math

import numpy as np

from scb.dixon_coles import dc_reads


def test_rho_zero_equivale_ao_poisson_puro():
    la, lb = 1.5, 1.1
    d = dc_reads(la, lb, 0.0)
    # BTTS fechado do Poisson independente
    btts = (1 - math.exp(-la)) * (1 - math.exp(-lb))
    assert abs(d["btts"] - btts) < 1e-4                 # (resíduo de truncamento só)
    assert 0 < d["pe"] < 1 and 0 < d["over25"] < 1


def test_rho_negativo_sobe_empate_de_placar_baixo():
    la, lb = 1.3, 1.0
    base = dc_reads(la, lb, 0.0)
    dc = dc_reads(la, lb, -0.10)
    assert dc["pe"] > base["pe"]                        # 0-0 e 1-1 sobem com ρ<0
    assert dc["btts"] != base["btts"]                   # canal de gols se move
    # e ρ>0 faz o oposto
    dcp = dc_reads(la, lb, +0.10)
    assert dcp["pe"] < base["pe"]


def test_probabilidades_coerentes_em_grade():
    for la in (0.6, 1.2, 2.4):
        for lb in (0.5, 1.0, 1.9):
            for rho in (-0.15, -0.05, 0.05):
                d = dc_reads(la, lb, rho)
                for k in ("pe", "over25", "btts"):
                    assert 0.0 <= d[k] <= 1.0
