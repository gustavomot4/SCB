"""M3.4 — predictor: piso conserva T_m (D-22), Poisson-condicional, propagação encolhe
favorito, ensemble soma 1, curva DA LIGA no pipeline, idempotência e incremental."""
import math

from scb import config, db, draw_curve, elo_engine, features_pit, predictor
from scb.predictor import PredictParams, lambdas, poisson_reads

CURVA = {"centers": [50.0, 200.0, 400.0], "pe": [0.29, 0.24, 0.15], "n": [500, 500, 500]}
P = PredictParams(curve=CURVA)


# ---------------------------------------------------------------- λ (D-22)
def test_piso_conserva_tm():
    la, lb = lambdas(900.0, P)                       # massacre: piso morde
    tm = predictor.tm_of(900.0, P)
    assert lb == P.lambda_min                        # azarão no piso
    assert abs((la + lb) - tm) < 1e-9                # total CONSERVADO (D-22)


def test_lambdas_simetria_e_neutro():
    la, lb = lambdas(150.0, P)
    lb2, la2 = lambdas(-150.0, P)
    assert abs(la - la2) < 1e-12 and abs(lb - lb2) < 1e-12
    la0, lb0 = lambdas(0.0, P)
    assert abs(la0 - lb0) < 1e-12 and abs(la0 + lb0 - P.t_base) < 1e-12


def test_desfalque_ofensivo_corta_proprio_lado():
    la, lb = lambdas(100.0, P)
    la2, lb2 = lambdas(100.0, P, datk_a=0.2)
    assert la2 < la and abs(lb2 - lb) < 1e-12        # não infla o rival (contrato §3.6)


# ---------------------------------------------------------------- Poisson (A1)
def test_poisson_soma_e_btts_consistente():
    r = poisson_reads(1.5, 1.1)
    assert abs(r["pv"] + r["pe"] + r["pd"] - 1.0) < 1e-6      # resíduo de truncamento ~0
    # BTTS fechado == BTTS da matriz (1 - linha0 - col0 + celula00)
    p0a, p0b = math.exp(-1.5), math.exp(-1.1)
    btts_matriz = 1 - p0a - p0b + p0a * p0b
    assert abs(r["btts"] - btts_matriz) < 1e-9
    assert 0 < r["over25"] < 1 and len(r["top5"]) == 5


# ---------------------------------------------------------------- propagação (Jensen)
def test_propagacao_encolhe_favorito_e_banda():
    seco = predictor.elo_direct_read(200.0, 1e-6, P)
    largo = predictor.elo_direct_read(200.0, 150.0, P)
    assert largo["pv"] < seco["pv"]                  # Jensen: favorito encolhe
    assert largo["band_lo"] <= largo["band_hi"]
    assert largo["band_lo"] < seco["pv"] < largo["band_hi"] + 1e-9
    de_novo = predictor.elo_direct_read(200.0, 150.0, P)
    assert de_novo == largo                          # determinístico (sem RNG)


# ---------------------------------------------------------------- ensemble
def test_predict_soma_1_e_campos():
    out = predictor.predict(120.0, 80.0, P)
    assert abs(out["p_v"] + out["p_e"] + out["p_d"] - 1.0) < 1e-9
    for k in ("p_v", "p_e", "p_d", "p_over25", "p_btts"):
        assert 0.0 < out[k] < 1.0
    assert out["lambda_a"] > out["lambda_b"]         # mandante favorito com dr>0


def test_perna_ad_off_por_default_e_hook():
    base = predictor.predict(100.0, 60.0, P)
    com_ad_off = predictor.predict(100.0, 60.0, P, ad_ved=(0.9, 0.05, 0.05))
    assert com_ad_off == base                        # w_ad=0 -> hook inerte (D-05)
    p_on = PredictParams(curve=CURVA, w_ad=0.5)
    com_ad_on = predictor.predict(100.0, 60.0, p_on, ad_ved=(0.9, 0.05, 0.05))
    assert com_ad_on["p_v"] > base["p_v"]            # perna AD puxa quando ligada


# ---------------------------------------------------------------- pipeline E2E
def _seed_pipeline(conn):
    for lg, times, empate_cada in (("BRA", ("Flamengo RJ", "Palmeiras"), 3),
                                   ("E0", ("Arsenal", "Chelsea"), 5)):
        a = db.get_or_create_team(conn, times[0])
        b = db.get_or_create_team(conn, times[1])
        for i in range(60):
            hs, as_ = (1, 1) if i % empate_cada == 0 else ((2, 0) if i % 2 else (0, 1))
            d = f"2024-{(i // 27) + 3:02d}-{(i % 27) + 1:02d}"
            conn.execute(
                "INSERT INTO matches(league,season,date,home_team_id,away_team_id,"
                "home_score,away_score,natural_key) VALUES (?,?,?,?,?,?,?,?)",
                (lg, 2024, d, a, b, hs, as_, f"{d}|{i}|{lg}"))
    conn.commit()
    elo_engine.run(conn)
    features_pit.run(conn)
    for lg in ("BRA", "E0"):
        draw_curve.freeze(conn, draw_curve.build(conn, lg, min_n=20))


def test_run_escreve_soma1_curva_da_liga_e_incremental(conn):
    _seed_pipeline(conn)
    s = predictor.run(conn)
    n_feat = conn.execute("SELECT COUNT(*) FROM match_features").fetchone()[0]
    assert s["predictions"] == n_feat == 120
    assert s["version"] == config.MODEL_VERSION
    for r in conn.execute("SELECT p_v, p_e, p_d, band_pv_lo, band_pv_hi FROM predictions"):
        assert abs(r["p_v"] + r["p_e"] + r["p_d"] - 1.0) < 1e-9
        assert r["band_pv_lo"] <= r["band_pv_hi"]
    # curvas POR LIGA de fato usadas: mesmo confronto técnico, P(E) difere entre ligas
    pe_bra = conn.execute("""SELECT AVG(p.p_e) FROM predictions p JOIN matches m USING(match_id)
                             WHERE m.league='BRA'""").fetchone()[0]
    pe_e0 = conn.execute("""SELECT AVG(p.p_e) FROM predictions p JOIN matches m USING(match_id)
                            WHERE m.league='E0'""").fetchone()[0]
    assert pe_bra > pe_e0                            # BRA empata mais -> modelo sabe (D-07)
    # idempotente + incremental == full
    s2 = predictor.run(conn, incremental=True)
    assert s2["predictions"] == 0
    antes = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    predictor.run(conn)
    depois = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    assert antes == depois == 120
