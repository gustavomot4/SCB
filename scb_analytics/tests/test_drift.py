"""M6.2 — drift PIT: exclui o presente, zera sem amostra, corrige deriva sintética."""
import numpy as np

from scb.drift import trailing_residual


def test_pit_exclui_o_proprio_dia_e_janela():
    d = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    resid = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
    r = trailing_residual(d, resid, W=10.0, min_n=1)
    assert r[0] == 0.0                                  # sem passado -> 0
    assert r[1] == 1.0 and r[4] == 1.0                  # média SÓ do passado
    r2 = trailing_residual(d, np.array([9, 0, 0, 0, 0.0]), W=2.0, min_n=1)
    assert r2[4] == 0.0                                 # o 9 saiu da janela (W=2)


def test_zera_sem_amostra_minima():
    d = np.arange(100.0)
    resid = np.ones(100)
    r = trailing_residual(d, resid, W=1000.0, min_n=300)
    assert (r == 0.0).all()                             # n<300 -> sem taxa inventada


def test_corrige_deriva_sintetica():
    """Modelo prevê 0,5 fixo; realidade deriva p/ 0,65 na 2ª metade -> correção melhora Brier."""
    rng = np.random.default_rng(5)
    n = 4000
    d = np.arange(float(n))
    taxa = np.where(d < n / 2, 0.5, 0.65)
    y = (rng.random(n) < taxa).astype(float)
    p = np.full(n, 0.5)
    r = trailing_residual(d, y - p, W=600.0, min_n=100)
    p2 = np.clip(p + r, 0.01, 0.99)
    metade2 = d >= n / 2
    antes = ((p - y) ** 2)[metade2].mean()
    depois = ((p2 - y) ** 2)[metade2].mean()
    assert depois < antes - 0.002                       # ganho real na era derivada
