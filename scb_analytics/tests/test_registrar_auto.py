"""Registro automático da rodada (fixtures.csv) + settle de jogo adiado."""
from scb import db, draw_curve, elo_engine, features_pit, registrar


def _base(conn):
    times = ["Flamengo RJ", "Palmeiras", "Santos", "Gremio"]
    ids = {n: db.get_or_create_team(conn, n) for n in times}
    jogos = [("Flamengo RJ", "Palmeiras", 2, 0), ("Santos", "Gremio", 1, 1),
             ("Palmeiras", "Santos", 3, 1), ("Gremio", "Flamengo RJ", 0, 2),
             ("Flamengo RJ", "Santos", 1, 0), ("Palmeiras", "Gremio", 2, 2)]
    for i, (h, a, hs, as_) in enumerate(jogos):
        d = f"2026-06-{i * 4 + 1:02d}"
        conn.execute("INSERT INTO matches(league,season,date,home_team_id,away_team_id,"
                     "home_score,away_score,natural_key) VALUES (?,?,?,?,?,?,?,?)",
                     ("BRA", 2026, d, ids[h], ids[a], hs, as_, f"{d}|{h}|{a}"))
    conn.commit()
    elo_engine.run(conn)
    features_pit.run(conn)
    draw_curve.freeze(conn, draw_curve.build(conn, "BRA", min_n=2))
    return ids


def test_auto_registra_so_a_janela_e_idempotente(conn, tmp_path, monkeypatch):
    _base(conn)
    monkeypatch.setattr(registrar, "REG", tmp_path / "reg.csv")
    fx = tmp_path / "fixtures.csv"
    fx.write_text("league,date,home,away\n"
                  "BRA,2026-07-19,Santos,Flamengo RJ\n"      # dentro da janela (hoje+2)
                  "BRA,19/07/2026,Gremio,Palmeiras\n"        # idem, formato BR
                  "BRA,2026-09-01,Palmeiras,Flamengo RJ\n",  # FORA da janela
                  encoding="utf-8")
    monkeypatch.setattr(registrar, "FIXTURES", fx)
    out = registrar.auto(conn, dias=4, hoje="2026-07-17")
    assert out["n_novos"] == 2 and out["fora_da_janela"] == 1 and not out["erros"]
    out2 = registrar.auto(conn, dias=4, hoje="2026-07-17")   # de novo: imutável
    assert out2["n_novos"] == 0 and out2["ja_registrados"] == 2
    assert len(registrar._linhas()) == 2


def test_settle_acha_jogo_adiado(conn, tmp_path, monkeypatch):
    """Registrado p/ dia X, jogo rolou 9 dias depois (adiado) — par ordenado é único
    na temporada, então o fallback liquida com segurança."""
    ids = _base(conn)
    monkeypatch.setattr(registrar, "REG", tmp_path / "reg.csv")
    registrar.register(conn, "BRA", "Santos", "Palmeiras", "2026-07-01")
    conn.execute("INSERT INTO matches(league,season,date,home_team_id,away_team_id,"
                 "home_score,away_score,natural_key) VALUES (?,?,?,?,?,?,?,?)",
                 ("BRA", 2026, "2026-07-10", ids["Santos"], ids["Palmeiras"], 0, 2,
                  "2026-07-10|Santos|Palmeiras"))
    conn.commit()
    s = registrar.settle(conn)
    assert s["preenchidos"] == 1 and s["em_aberto"] == 0
    linha = registrar._linhas()[0]
    assert linha["home_score"] == "0" and linha["away_score"] == "2"
