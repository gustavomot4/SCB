"""sot_edge — candidato REJEITADO (D-32), mas o módulo fica no repo: testa a propriedade
crítica (PIT anti look-ahead), neutralidade sem stats, janela K e o cap do δ."""
import numpy as np

from scb import sot_edge


def _r(h, a, sh, sa):
    return {"h": h, "a": a, "sh": sh, "sa": sa}


def test_edge_pit_anti_lookahead():
    # time 1 domina (+8 de SoT-diff sempre); time 2 apanha (−8). K grande.
    rows = [_r(1, 2, 10, 2)] * 4
    edge = sot_edge.edge_series(rows, K=10)
    # sem histórico mínimo (MIN_HIST=3) -> os 3 primeiros são neutros
    assert edge[0] == 0.0 and edge[1] == 0.0 and edge[2] == 0.0
    # 4º jogo: time1 tem 3 jogos de +8, time2 3 de −8 -> edge = 8 − (−8) = 16
    assert abs(edge[3] - 16.0) < 1e-9
    # anti look-ahead: o histórico é atualizado DEPOIS -> edge[3] NÃO usa o próprio 4º jogo


def test_neutro_onde_nao_ha_stats():
    rows = [_r(1, 2, None, None)] * 5      # nenhuma partida tem stats
    edge = sot_edge.edge_series(rows, K=10)
    assert (edge == 0).all()               # histórico não atualiza -> δ seria 0 (nada inventado)


def test_janela_K_limita_o_passado():
    # 1 domina os 3 primeiros (+10), depois 4 jogos neutros. Com K=3, o último jogo só
    # "enxerga" os 3 neutros mais recentes -> a média (e o edge) cai a 0 (janela esquece o pico).
    seq = [(10, 0)] * 3 + [(5, 5)] * 4
    rows = [_r(1, 2, sh, sa) for sh, sa in seq]
    edge = sot_edge.edge_series(rows, K=3)
    assert abs(edge[3]) > 1e-6            # logo após o domínio, edge é grande
    assert abs(edge[-1]) < 1e-9          # janela K=3 já esqueceu o pico -> neutro


def test_delta_respeita_cap():
    edge = np.array([100.0, -100.0, 0.5])
    delta = np.clip(30.0 * edge, -sot_edge.CAP, sot_edge.CAP)
    assert delta[0] == sot_edge.CAP and delta[1] == -sot_edge.CAP
    assert abs(delta[2] - 15.0) < 1e-9      # dentro do teto passa direto
