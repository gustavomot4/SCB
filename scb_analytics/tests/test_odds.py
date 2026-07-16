"""M2 — de-vig proporcional, blend e validações (port do scm/odds)."""
import pytest

from scb import odds


def test_devig_soma_1_e_proporcional():
    mk = odds.implied_probs(2.0, 3.5, 4.0)
    assert abs(mk["p_v"] + mk["p_e"] + mk["p_d"] - 1.0) < 1e-12
    # proporcional: razões preservadas (p_v/p_e == (1/2)/(1/3.5))
    assert abs(mk["p_v"] / mk["p_e"] - 3.5 / 2.0) < 1e-12
    assert mk["p_v"] > mk["p_e"] and mk["p_v"] > mk["p_d"]


def test_devig_rejeita_odd_invalida():
    for bad in [(1.0, 3.5, 4.0), (0, 3.5, 4.0), (None, 3.5, 4.0), (-2, 3.5, 4.0)]:
        with pytest.raises(ValueError):
            odds.implied_probs(*bad)


def test_blend_renormaliza_e_peso():
    model = {"p_v": 0.5, "p_e": 0.3, "p_d": 0.2}
    market = {"p_v": 0.7, "p_e": 0.2, "p_d": 0.1}
    out = odds.blend(model, market, w=0.20)
    assert abs(sum(out.values()) - 1.0) < 1e-12
    assert abs(out["p_v"] - (0.8 * 0.5 + 0.2 * 0.7)) < 1e-12
    same = odds.blend(model, market, w=0.0)              # w=0: modelo intacto
    assert abs(same["p_v"] - 0.5) < 1e-12
