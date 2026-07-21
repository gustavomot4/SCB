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


def test_over_btts_tm_desacoplado():
    # D-33: tm_extra=0 -> idêntico ao Poisson base; +total -> mais over2.5; -total -> menos
    from scb import predictor
    la, lb = 1.6, 1.0
    base = predictor.poisson_reads(la, lb)
    o0, b0 = sot_edge.over_btts_tm(la, lb, 0.0)
    assert abs(o0 - base["over25"]) < 1e-9 and abs(b0 - base["btts"]) < 1e-9
    assert sot_edge.over_btts_tm(la, lb, 0.6)[0] > base["over25"]     # mais gols -> mais over
    assert sot_edge.over_btts_tm(la, lb, -0.6)[0] < base["over25"]    # menos gols -> menos over


def test_roll_pit_anti_lookahead():
    # baseline móvel PIT: usa só o passado (posição 0 = NaN; depois a média das anteriores)
    x = np.array([2.0, 4.0, 6.0])
    out = sot_edge._roll_pit(x, L=10)
    assert np.isnan(out[0])                 # nada antes -> NaN
    assert abs(out[1] - 2.0) < 1e-9         # média de [2]
    assert abs(out[2] - 3.0) < 1e-9         # média de [2,4] (NÃO inclui o 6 do próprio i)


def test_adocao_flag_e_neutralidade(conn):
    # D-33 adotado: flag por liga + neutralidade onde a liga não usa SoT-gols
    from scb import config, db
    assert config.sot_goals_for("E0") is True
    assert config.sot_goals_for("BRA") is False and config.sot_goals_for("XX") is False
    db.get_or_create_team(conn, "A"); db.get_or_create_team(conn, "B")
    assert sot_edge.tm_extra_map(conn, "BRA") == {}                 # liga OFF -> mapa vazio
    assert sot_edge.tm_extra_today(conn, "BRA", "A", "B") == 0.0    # e δ 0 na porta da frente
