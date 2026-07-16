"""M6.3 — mando rolling: PIT, sinal certo quando o mando some, cap e n mínimo."""
import numpy as np

from scb.mando_rolling import delta_series, elo_inv


def test_elo_inv_valores():
    assert abs(elo_inv(0.5)) < 1e-9
    assert abs(elo_inv(0.640) - 100.0) < 2.0          # inverso do we(100)≈0,640
    assert elo_inv(0.3) < 0 < elo_inv(0.7)


def test_delta_pit_e_sinal_quando_mando_some():
    """Modelo espera we=0,64 sempre; na 2ª metade o mandante vira moeda (0,5) -> δ<0."""
    n = 2000
    d = np.arange(float(n))
    we = np.full(n, 0.64)
    rng = np.random.default_rng(9)
    pts = np.where(d < n / 2, (rng.random(n) < 0.64), (rng.random(n) < 0.50)).astype(float)
    delta = delta_series(d, pts, we, W=400.0, min_n=100)
    assert delta[150] == 0.0 or abs(delta[300]) < 30.0     # início: pouco/nenhum desvio
    assert delta[-1] < -50.0                               # fim: mando sumiu -> δ bem negativo
    # PIT: δ de um ponto não muda se o FUTURO mudar
    pts2 = pts.copy(); pts2[-1] = 1.0 - pts2[-1]
    delta2 = delta_series(d, pts2, we, W=400.0, min_n=100)
    assert delta[1000] == delta2[1000]


def test_cap_e_min_n():
    d = np.arange(500.0)
    we = np.full(500, 0.64)
    pts = np.zeros(500)                                    # mandante nunca pontua (absurdo)
    delta = delta_series(d, pts, we, W=1000.0, min_n=300)
    assert (delta[:300] == 0.0).all()                      # sem amostra -> 0
    assert delta[-1] == -60.0                              # cap ±60 segura o absurdo
