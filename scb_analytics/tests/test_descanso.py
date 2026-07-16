"""M6.4 — descanso: PIT, neutro na estreia, clip, sinal do diferencial."""
import numpy as np

from scb.descanso import rest_series, CLIP_HI, CLIP_LO, NEUTRO


class R(dict):
    def __getitem__(self, k):
        return dict.__getitem__(self, k)


def _rows(spec):
    """spec: lista (dia, season, h, a). Vira rows ordenadas."""
    return [R(d=float(d), season=s, h=h, a=a) for d, s, h, a in spec]


def test_estreia_neutra_e_pit():
    rows = _rows([(10, 2026, 1, 2), (13, 2026, 1, 3), (20, 2026, 2, 3)])
    diff = rest_series(rows)
    assert diff[0] == 0.0                              # estreia dos dois -> neutro − neutro
    # jogo 2: time 1 descansou 3d (clip->3); time 3 estreia (NEUTRO=6) -> diff = 3−6
    assert diff[1] == 3.0 - NEUTRO
    # jogo 3: time 2 descansou 10d (clip->8); time 3 descansou 7d -> 8−7 = +1
    assert diff[2] == CLIP_HI - 7.0


def test_clip_curto():
    rows = _rows([(10, 2026, 1, 2), (11, 2026, 1, 3), (30, 2026, 1, 2)])
    diff = rest_series(rows)
    assert diff[1] == CLIP_LO - NEUTRO                 # 1 dia de descanso -> clip 2
    # jogo 3: time 1 com 19d (clip 8); time 2 com 20d (clip 8) -> 0
    assert diff[2] == 0.0


def test_temporada_reinicia_o_relogio():
    rows = _rows([(300, 2025, 1, 2), (400, 2026, 1, 2)])
    diff = rest_series(rows)
    assert diff[1] == 0.0                              # temporada nova: ambos estreiam (neutro)
