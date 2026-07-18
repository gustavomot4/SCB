"""Adoções da E0 (D-26/D-27): wiring por liga do mando rolling e do Dixon-Coles."""
from scb import config, db, dixon_coles, elo_engine, features_pit, predictor


def _add(conn, league, season, date, home, away, hs, as_):
    hid = db.get_or_create_team(conn, home)
    aid = db.get_or_create_team(conn, away)
    conn.execute(
        "INSERT INTO matches(league,season,date,home_team_id,away_team_id,"
        "home_score,away_score,natural_key) VALUES (?,?,?,?,?,?,?,?)",
        (league, season, date, hid, aid, hs, as_, f"{date}|{home}|{away}|{league}"))
    conn.commit()


def test_poisson_reads_dc_consistente_e_rho0_puro():
    base = predictor.poisson_reads(1.4, 1.1)
    dc = predictor.poisson_reads(1.4, 1.1, dc_rho=-0.05)
    ref = dixon_coles.dc_reads(1.4, 1.1, -0.05)
    assert abs(dc["pe"] - ref["pe"]) < 1e-9            # núcleo único: predictor == módulo do gate
    assert abs(dc["btts"] - ref["btts"]) < 1e-9
    assert dc["pe"] > base["pe"]                       # ρ<0 sobe empate
    puro = predictor.poisson_reads(1.4, 1.1, dc_rho=0.0)
    assert puro["pe"] == base["pe"]                    # ρ=0 ≡ Poisson puro


def test_params_for_le_dc_rho_do_config(conn, monkeypatch):
    _add(conn, "E0", 2024, "2024-08-16", "Arsenal", "Chelsea", 2, 0)
    elo_engine.run(conn)
    monkeypatch.setattr(config, "DC_RHO", {"E0": -0.05, "default": 0.0})
    p_e0 = predictor.params_for(conn, "E0")
    assert p_e0.dc_rho == -0.05
    _add(conn, "BRA", 2024, "2024-04-20", "Flamengo RJ", "Palmeiras", 2, 0)
    elo_engine.run(conn)
    p_bra = predictor.params_for(conn, "BRA")
    assert p_bra.dc_rho == 0.0                         # BRA fica Poisson puro


def test_mando_rolling_so_na_liga_flagada(conn, monkeypatch):
    """Com MUITOS jogos (>MIN_N) o δ liga na E0 e NÃO liga no BRA (flag default)."""
    from scb import mando_rolling
    monkeypatch.setattr(mando_rolling, "MIN_N", 5)     # amostra de teste pequena
    monkeypatch.setattr(config, "MANDO_ROLLING", {"E0": True, "default": False})
    for i in range(12):                                # mandante da E0 SEMPRE perde: δ<0
        _add(conn, "E0", 2024, f"2024-08-{i+1:02d}", "Arsenal", "Chelsea", 0, 1)
        _add(conn, "BRA", 2024, f"2024-08-{i+1:02d}", "Flamengo RJ", "Palmeiras", 0, 1)
    elo_engine.run(conn)
    features_pit.run(conn)
    dr = {}
    for lg in ("E0", "BRA"):
        r = conn.execute(
            """SELECT mf.dr_adj, mf.dr_elo, mf.form_home, mf.form_away
               FROM match_features mf JOIN matches m USING(match_id)
               WHERE m.league=? ORDER BY m.match_id DESC LIMIT 1""", (lg,)).fetchone()
        dr[lg] = r["dr_adj"] - (r["dr_elo"] + r["form_home"] - r["form_away"])
    assert dr["E0"] < -5.0                             # δ negativo aplicado (mandante ruim)
    assert abs(dr["BRA"]) < 1e-9                       # BRA intocado (flag off)