"""M5 — simulate_league (invariantes), predict_match (produção=backtest), registrar (imutável)."""
from scb import config, db, draw_curve, elo_engine, features_pit, predict_match
from scb import registrar, simulate_league


def _liga_2026(conn):
    """4 clubes, turno-returno parcial: 8 de 12 jogos disputados."""
    times = ["Flamengo RJ", "Palmeiras", "Santos", "Gremio"]
    ids = {n: db.get_or_create_team(conn, n) for n in times}
    jogos = [("Flamengo RJ", "Palmeiras", 2, 0), ("Santos", "Gremio", 1, 1),
             ("Palmeiras", "Santos", 3, 1), ("Gremio", "Flamengo RJ", 0, 2),
             ("Flamengo RJ", "Santos", 1, 0), ("Palmeiras", "Gremio", 2, 2),
             ("Santos", "Flamengo RJ", 0, 1), ("Gremio", "Palmeiras", 1, 3)]
    for i, (h, a, hs, as_) in enumerate(jogos):
        d = f"2026-0{(i // 4) + 4}-{(i % 4) * 7 + 1:02d}"
        conn.execute("INSERT INTO matches(league,season,date,home_team_id,away_team_id,"
                     "home_score,away_score,natural_key) VALUES (?,?,?,?,?,?,?,?)",
                     ("BRA", 2026, d, ids[h], ids[a], hs, as_, f"{d}|{h}|{a}"))
    conn.commit()
    elo_engine.run(conn)
    features_pit.run(conn)
    draw_curve.freeze(conn, draw_curve.build(conn, "BRA", min_n=2))
    return ids


def test_sim_invariantes_e_determinismo(conn):
    _liga_2026(conn)
    r = simulate_league.run(conn, "BRA", 2026, sims=400)
    assert r["played"] == 8 and r["remaining"] == 4          # 12 (4x3) − 8
    assert abs(sum(t["titulo"] for t in r["tabela"]) - 1.0) < 1e-9    # Σ título = 1
    assert abs(sum(t["z4"] for t in r["tabela"]) - 4.0) < 1e-9        # 4 vagas de Z4 (n=4!)
    assert abs(sum(t["pos_media"] for t in r["tabela"]) - 10.0) < 1e-9  # Σ(1..4)
    r2 = simulate_league.run(conn, "BRA", 2026, sims=400)
    assert r["tabela"] == r2["tabela"]                       # seed fixa -> idêntico
    # Flamengo 100% aproveitamento em 4 jogos -> favorito ao título
    fla = next(t for t in r["tabela"] if t["team"] == "Flamengo RJ")
    assert fla["titulo"] == max(t["titulo"] for t in r["tabela"])


def test_predict_now_consistente_com_features(conn):
    """dr da porta da frente == fórmula do backtest (elo + forma + H) — D-34."""
    _liga_2026(conn)
    o = predict_match.predict_now(conn, "BRA", "Flamengo RJ", "Palmeiras")
    from scb.features_pit import team_form
    fla = conn.execute("SELECT team_id FROM teams WHERE name='Flamengo RJ'").fetchone()[0]
    pal = conn.execute("SELECT team_id FROM teams WHERE name='Palmeiras'").fetchone()[0]
    elo = {r["team_id"]: r["elo"] for r in conn.execute("SELECT * FROM ratings_current")}
    fh = team_form(conn, fla, "9999-12-31")[0]
    fa = team_form(conn, pal, "9999-12-31")[0]
    esperado = elo[fla] - elo[pal] + fh - fa + config.h_for("BRA")
    assert abs(o["dr"] - esperado) < 1e-9
    assert abs(o["p_v"] + o["p_e"] + o["p_d"] - 1.0) < 1e-9


def test_registrar_imutavel_settle_e_report(conn, tmp_path, monkeypatch):
    _liga_2026(conn)
    monkeypatch.setattr(registrar, "REG", tmp_path / "registro.csv")
    r1 = registrar.register(conn, "BRA", "Flamengo RJ", "Gremio", "2026-06-01")
    assert r1["ja_registrado"] is False
    r2 = registrar.register(conn, "BRA", "Flamengo RJ", "Gremio", "2026-06-01")
    assert r2["ja_registrado"] is True                       # imutável: não duplica
    linhas = registrar._linhas()
    assert len(linhas) == 1 and linhas[0]["home_score"] == ""
    # settle acha o jogo real (2026-05-29... nosso fixture tem Fla x Santos etc.;
    # registramos Fla x Gremio 06-01 SEM jogo correspondente -> fica aberto)
    s = registrar.settle(conn)
    assert s["em_aberto"] == 1 and s["preenchidos"] == 0
    # registra um jogo QUE existe (Flamengo 2x0 Palmeiras em 2026-04-01) e liquida ±2d
    registrar.register(conn, "BRA", "Flamengo RJ", "Palmeiras", "2026-04-02")
    s2 = registrar.settle(conn)
    assert s2["preenchidos"] == 1
    fech = [r for r in registrar._linhas() if r["brier"] != ""]
    assert len(fech) == 1 and float(fech[0]["brier"]) < 0.667    # acertou o favorito
    assert fech[0]["p_v"] != "" and fech[0]["home_score"] == "2"  # previsão intacta + placar real
    assert registrar.report()["n"] == 1
