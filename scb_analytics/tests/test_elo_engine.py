"""M3.1 — elo_engine: fórmulas, PIT (anti look-ahead), zero-sum, idempotência, hook C5."""
from scb import config, db, elo_engine
from scb.elo_engine import EloParams, g_factor, sigma_r, we


def _add_match(conn, league, season, date, home, away, hs, as_):
    hid = db.get_or_create_team(conn, home)
    aid = db.get_or_create_team(conn, away)
    conn.execute(
        "INSERT INTO matches(league,season,date,home_team_id,away_team_id,"
        "home_score,away_score,natural_key) VALUES (?,?,?,?,?,?,?,?)",
        (league, season, date, hid, aid, hs, as_, f"{date}|{home}|{away}|{league}"))
    conn.commit()


# ---------------------------------------------------------------- fórmulas (contrato §1)
def test_we_valores_e_simetria():
    assert abs(we(0) - 0.5) < 1e-12
    assert abs(we(100) - 0.6401) < 5e-4          # contrato: we(100) ~ 0.640
    assert abs(we(150) + we(-150) - 1.0) < 1e-12


def test_g_factor_margens():
    assert g_factor(0) == 1.0 and g_factor(1) == 1.0 and g_factor(-1) == 1.0
    assert g_factor(2) == 1.5 and g_factor(-2) == 1.5
    assert g_factor(3) == (11 + 3) / 8 and g_factor(5) == 2.0


def test_sigma_r_decrescente():
    p = EloParams()
    assert sigma_r(0, p) == p.sigma_provisional
    assert sigma_r(10, p) < sigma_r(0, p)
    assert abs(sigma_r(10_000, p) - p.sigma_floor) < 1e-6


# ---------------------------------------------------------------- PIT + mando + atualização
def test_pit_primeiro_jogo_e_mando(conn):
    _add_match(conn, "BRA", 2024, "2024-04-20", "Flamengo RJ", "Palmeiras", 2, 0)
    elo_engine.run(conn)
    r = conn.execute("SELECT * FROM match_ratings").fetchone()
    assert r["home_elo_pre"] == 1500.0 and r["away_elo_pre"] == 1500.0   # PRÉ, não pós
    assert r["dr"] == config.h_for("BRA")                                # mando em TODO jogo
    assert r["home_n_pre"] == 0 and r["away_n_pre"] == 0


def test_vencedor_sobe_zero_sum_e_encadeia(conn):
    _add_match(conn, "BRA", 2024, "2024-04-20", "Flamengo RJ", "Palmeiras", 2, 0)
    _add_match(conn, "BRA", 2024, "2024-04-27", "Palmeiras", "Flamengo RJ", 0, 0)
    elo_engine.run(conn)
    cur = {r["team_id"]: r["elo"] for r in conn.execute("SELECT * FROM ratings_current")}
    fla = conn.execute("SELECT team_id FROM teams WHERE name='Flamengo RJ'").fetchone()[0]
    pal = conn.execute("SELECT team_id FROM teams WHERE name='Palmeiras'").fetchone()[0]
    assert cur[fla] > 1500 > cur[pal]                                    # vencedor sobe
    assert abs(cur[fla] + cur[pal] - 3000.0) < 1e-9                      # zero-sum
    r2 = conn.execute("SELECT * FROM match_ratings ORDER BY match_id").fetchall()[1]
    assert r2["away_elo_pre"] > 1500.0                                   # pré do 2º = pós do 1º
    assert r2["home_n_pre"] == 1 and r2["away_n_pre"] == 1


def test_idempotente_e_media_por_liga(conn):
    _add_match(conn, "BRA", 2024, "2024-04-20", "Flamengo RJ", "Palmeiras", 2, 0)
    _add_match(conn, "E0", 2024, "2024-08-16", "Man United", "Fulham", 1, 3)
    elo_engine.run(conn)
    first = {r["team_id"]: r["elo"] for r in conn.execute("SELECT * FROM ratings_current")}
    elo_engine.run(conn)                                                 # de novo
    second = {r["team_id"]: r["elo"] for r in conn.execute("SELECT * FROM ratings_current")}
    assert first == second                                               # idempotente
    for lg in ("BRA", "E0"):                                             # média 1500 POR liga
        elos = [r["elo"] for r in conn.execute(
            """SELECT elo FROM ratings_current WHERE team_id IN
               (SELECT DISTINCT home_team_id FROM matches WHERE league=?
                UNION SELECT DISTINCT away_team_id FROM matches WHERE league=?)""", (lg, lg))]
        assert abs(sum(elos) / len(elos) - 1500.0) < 1e-9


def test_hook_regressao_temporada_c5(conn):
    _add_match(conn, "BRA", 2024, "2024-04-20", "Flamengo RJ", "Palmeiras", 3, 0)
    _add_match(conn, "BRA", 2025, "2025-04-20", "Flamengo RJ", "Palmeiras", 0, 0)
    elo_engine.run(conn, EloParams(season_rho=0.0))                      # rho=0 (forçado OFF)
    off = conn.execute("SELECT home_elo_pre FROM match_ratings ORDER BY match_id").fetchall()[1][0]
    elo_engine.run(conn, EloParams(season_rho=0.5))                      # rho=0.5 (ON)
    on = conn.execute("SELECT home_elo_pre FROM match_ratings ORDER BY match_id").fetchall()[1][0]
    assert on < off                                                      # regrediu rumo a 1500
    assert abs((on - 1500.0) - 0.5 * (off - 1500.0)) < 1e-9              # exatamente (1-rho)
    # e zero-sum preservado no estado final
    cur = [r["elo"] for r in conn.execute("SELECT elo FROM ratings_current")]
    assert abs(sum(cur) - 3000.0) < 1e-9


def test_rho_por_liga_d25(conn):
    """D-25: default (None) aplica ρ POR LIGA — BRA=0,30 regride; E0=0 não."""
    for lg, h, a in (("BRA", "Flamengo RJ", "Palmeiras"), ("E0", "Arsenal", "Chelsea")):
        _add_match(conn, lg, 2024, "2024-04-20", h, a, 3, 0)
        _add_match(conn, lg, 2025, "2025-04-20", h, a, 0, 0)
    elo_engine.run(conn)                                                 # None -> config por liga
    pre = {}
    for lg in ("BRA", "E0"):
        rows = conn.execute(
            """SELECT mr.home_elo_pre FROM match_ratings mr JOIN matches m USING(match_id)
               WHERE m.league=? ORDER BY m.match_id""", (lg,)).fetchall()
        pre[lg] = [r[0] for r in rows]
    ganho_bra_2024 = pre["BRA"][0]                                       # 1500 (estreia)
    assert ganho_bra_2024 == 1500.0
    # vencedor de 2024 chega em 2025 REGREDIDO no BRA...
    elo_off = elo_engine.run(conn, EloParams(season_rho=0.0)) and None
    rows_off = conn.execute(
        """SELECT mr.home_elo_pre FROM match_ratings mr JOIN matches m USING(match_id)
           WHERE m.league='BRA' ORDER BY m.match_id""").fetchall()
    elo_engine.run(conn)                                                 # volta ao default
    rows_on = conn.execute(
        """SELECT mr.home_elo_pre FROM match_ratings mr JOIN matches m USING(match_id)
           WHERE m.league='BRA' ORDER BY m.match_id""").fetchall()
    assert rows_on[1][0] < rows_off[1][0]                                # BRA regrediu
    # ...e na E0 o default NÃO regride (igual ao off)
    e0_on = conn.execute(
        """SELECT mr.home_elo_pre FROM match_ratings mr JOIN matches m USING(match_id)
           WHERE m.league='E0' ORDER BY m.match_id""").fetchall()
    assert abs((e0_on[1][0] - 1500.0) / (rows_off[1][0] - 1500.0) - 1.0) < 1e-9
