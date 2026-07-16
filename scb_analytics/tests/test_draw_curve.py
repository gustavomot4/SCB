"""M3.3 — curva de empate por liga: recupera taxas, interpola, cap garante [0,1],
corte por temporada (anti-vazamento), freeze/load, curvas diferem por liga (D-07)."""
import math

from scb import db, draw_curve, elo_engine


def _seed(conn, league, n_games, draw_every, season=2024, elo_gap=0):
    """n_games do mesmo par; empate a cada `draw_every`. elo_gap≈0 mantém |dr| baixo."""
    a = db.get_or_create_team(conn, f"{league} A")
    b = db.get_or_create_team(conn, f"{league} B")
    for i in range(n_games):
        hs, as_ = (1, 1) if (i % draw_every == 0) else (1, 0)
        d = f"{season}-{(i // 28) + 3:02d}-{(i % 28) + 1:02d}"
        conn.execute(
            "INSERT INTO matches(league,season,date,home_team_id,away_team_id,"
            "home_score,away_score,natural_key) VALUES (?,?,?,?,?,?,?,?)",
            (league, season, d, a, b, hs, as_, f"{d}|{i}|{league}"))
    conn.commit()


def test_curva_recupera_taxa_de_empate(conn):
    _seed(conn, "BRA", n_games=300, draw_every=3)      # ~1/3 de empates
    elo_engine.run(conn)
    curve = draw_curve.build(conn, "BRA", min_n=50)
    total_pe = sum(p * n for p, n in zip(curve["pe"], curve["n"])) / sum(curve["n"])
    assert abs(total_pe - 1 / 3) < 0.02                # taxa agregada recuperada
    assert curve["n_total"] == 300


def test_ved_soma_1_e_dentro_de_01_em_todo_dr():
    curve = {"centers": [50.0, 200.0], "pe": [0.30, 0.20], "n": [500, 500]}
    for dr in range(-800, 801, 25):                    # invariante herdado: P∈[0,1] SEM clamp externo
        r = draw_curve.ved_from_dr(float(dr), curve)
        assert abs(r["p_v"] + r["p_e"] + r["p_d"] - 1.0) < 1e-12
        for k in ("p_v", "p_e", "p_d"):
            assert -1e-12 <= r[k] <= 1.0 + 1e-12
    # massacre: cap morde (pe << tabela) e favorito domina
    r = draw_curve.ved_from_dr(700.0, curve)
    assert r["p_e"] < 0.05 and r["p_v"] > 0.9 and r["p_d"] >= 0


def test_interpolacao_entre_centros():
    curve = {"centers": [0.0, 100.0], "pe": [0.30, 0.10], "n": [500, 500]}
    assert abs(draw_curve.pe_raw(50.0, curve) - 0.20) < 1e-12    # ponto médio
    assert draw_curve.pe_raw(0.0, curve) == 0.30                 # clamp esquerda
    assert draw_curve.pe_raw(999.0, curve) == 0.10               # clamp direita


def test_max_season_corta_anti_vazamento(conn):
    _seed(conn, "BRA", n_games=100, draw_every=2, season=2020)   # era empatadora (50%)
    _seed(conn, "BRA", n_games=100, draw_every=10, season=2024)  # era seca (10%)
    elo_engine.run(conn)
    treino = draw_curve.build(conn, "BRA", max_season=2020, min_n=20)
    tudo = draw_curve.build(conn, "BRA", min_n=20)
    assert treino["n_total"] == 100 and tudo["n_total"] == 200
    pe_treino = sum(p * n for p, n in zip(treino["pe"], treino["n"])) / 100
    pe_tudo = sum(p * n for p, n in zip(tudo["pe"], tudo["n"])) / 200
    assert pe_treino > pe_tudo                                    # o corte muda a curva de fato


def test_freeze_load_roundtrip_com_versao(conn):
    _seed(conn, "BRA", n_games=120, draw_every=4)
    elo_engine.run(conn)
    curve = draw_curve.build(conn, "BRA", min_n=30)
    draw_curve.freeze(conn, curve)
    loaded = draw_curve.load(conn, "BRA")
    assert loaded["pe"] == curve["pe"] and loaded["n_total"] == 120
    assert "version" in loaded and loaded["built"] == curve["built"]
    assert draw_curve.load(conn, "XX") is None


def test_curvas_diferem_por_liga(conn):
    """Aceite da M3.3 em miniatura (D-07): regimes diferentes -> curvas diferentes."""
    _seed(conn, "BRA", n_games=200, draw_every=3)      # ~33% empate
    _seed(conn, "E0", n_games=200, draw_every=5)       # ~20% empate
    elo_engine.run(conn)
    bra = draw_curve.build(conn, "BRA", min_n=50)
    e0 = draw_curve.build(conn, "E0", min_n=50)
    pe_bra = sum(p * n for p, n in zip(bra["pe"], bra["n"])) / sum(bra["n"])
    pe_e0 = sum(p * n for p, n in zip(e0["pe"], e0["n"])) / sum(e0["n"])
    assert pe_bra > pe_e0 + 0.05                       # BRA empata mais — e a curva sabe
