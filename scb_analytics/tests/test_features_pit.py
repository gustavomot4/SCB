"""M3.2 — features_pit: ANTI LOOK-AHEAD (o portão), forma, decay por jogo, σ_dr, incremental."""
import math

from scb import db, elo_engine, features_pit
from scb.features_pit import FeatureParams, team_form, vol_mult


def _add(conn, date, home, away, hs, as_, league="BRA", season=2024):
    hid = db.get_or_create_team(conn, home)
    aid = db.get_or_create_team(conn, away)
    conn.execute(
        "INSERT INTO matches(league,season,date,home_team_id,away_team_id,"
        "home_score,away_score,natural_key) VALUES (?,?,?,?,?,?,?,?)",
        (league, season, date, hid, aid, hs, as_, f"{date}|{home}|{away}|{league}"))
    conn.commit()


def _rebuild(conn):
    elo_engine.run(conn)
    features_pit.run(conn)


def _feat(conn, date):
    return dict(conn.execute(
        """SELECT mf.* FROM match_features mf JOIN matches m USING(match_id)
           WHERE m.date=?""", (date,)).fetchone())


# ---------------------------------------------------------------- O PORTÃO
def test_anti_look_ahead(conn):
    """Feature de um jogo NÃO muda quando um jogo FUTURO entra na base."""
    _add(conn, "2024-04-01", "Flamengo RJ", "Palmeiras", 2, 0)
    _add(conn, "2024-04-08", "Palmeiras", "Santos", 1, 1)
    _add(conn, "2024-04-15", "Santos", "Flamengo RJ", 0, 3)
    _rebuild(conn)
    antes = _feat(conn, "2024-04-15")
    _add(conn, "2024-04-22", "Flamengo RJ", "Santos", 0, 5)   # futuro: goleada que mudaria tudo
    _rebuild(conn)                                            # rebuild COMPLETO
    depois = _feat(conn, "2024-04-15")
    assert antes == depois                                    # passado é imutável


def test_form_zero_sem_historico(conn):
    _add(conn, "2024-04-01", "Flamengo RJ", "Palmeiras", 2, 0)
    elo_engine.run(conn)
    f, d, n = team_form(conn, 1, "2024-04-01")
    assert f == 0.0 and d == 0.0 and n == 0


def test_form_sinal_e_cap(conn):
    """Quem vence acima da expectativa tem forma positiva; o oposto, negativa; |form| <= cap."""
    for i in range(6):                                        # Fla vence sempre (upset leve: mando alheio)
        _add(conn, f"2024-04-{i+1:02d}", "Palmeiras", "Flamengo RJ", 0, 2)
    elo_engine.run(conn)
    fla = db.get_or_create_team(conn, "Flamengo RJ")
    pal = db.get_or_create_team(conn, "Palmeiras")
    f_fla, _, n = team_form(conn, fla, "2024-05-01")
    f_pal, _, _ = team_form(conn, pal, "2024-05-01")
    assert n == 6 and f_fla > 0 > f_pal
    p = FeatureParams()
    assert abs(f_fla) <= p.form_cap and abs(f_pal) <= p.form_cap


def test_decay_por_jogo_recente_pesa_mais(conn):
    """Derrota antiga + vitória recente > vitória antiga + derrota recente (mesmo saldo)."""
    _add(conn, "2024-04-01", "Santos", "Flamengo RJ", 2, 0)   # Fla perde (antigo)
    _add(conn, "2024-04-08", "Flamengo RJ", "Gremio", 2, 0)   # Fla vence (recente)
    _add(conn, "2024-04-01", "Bahia", "Palmeiras", 0, 2)      # Pal vence (antigo)
    _add(conn, "2024-04-08", "Palmeiras", "Cruzeiro", 0, 2)   # Pal perde (recente)
    elo_engine.run(conn)
    fla = db.get_or_create_team(conn, "Flamengo RJ")
    pal = db.get_or_create_team(conn, "Palmeiras")
    f_fla, _, _ = team_form(conn, fla, "2024-05-01")
    f_pal, _, _ = team_form(conn, pal, "2024-05-01")
    assert f_fla > f_pal                                      # recência por JOGO mordendo


def test_dr_adj_e_sigma_rss(conn):
    _add(conn, "2024-04-01", "Flamengo RJ", "Palmeiras", 2, 0)
    _add(conn, "2024-04-08", "Palmeiras", "Flamengo RJ", 1, 1)
    _rebuild(conn)
    r = _feat(conn, "2024-04-08")
    assert abs(r["dr_adj"] - (r["dr_elo"] + r["form_home"] - r["form_away"])) < 1e-9
    rss = math.sqrt(r["sigma_r_home"] ** 2 + r["sigma_r_away"] ** 2 +
                    r["sigma_ajuste_home"] ** 2 + r["sigma_ajuste_away"] ** 2)
    assert abs(r["sigma_dr"] - rss) < 1e-9


def test_incremental_igual_full(conn):
    _add(conn, "2024-04-01", "Flamengo RJ", "Palmeiras", 2, 0)
    _add(conn, "2024-04-08", "Palmeiras", "Santos", 1, 1)
    _rebuild(conn)
    _add(conn, "2024-04-15", "Santos", "Flamengo RJ", 0, 3)   # jogo novo (append-only)
    elo_engine.run(conn)
    features_pit.run(conn, incremental=True)                  # só o novo
    inc = {r["match_id"]: tuple(r) for r in conn.execute("SELECT * FROM match_features")}
    features_pit.run(conn)                                    # rebuild completo
    full = {r["match_id"]: tuple(r) for r in conn.execute("SELECT * FROM match_features")}
    assert inc == full                                        # incremental == full (invariância PIT)


def test_vol_mult_regras():
    assert vol_mult(0.0, n_form=2) == 1.0                     # pouca forma -> neutro
    assert vol_mult(0.35, n_form=10) == 1.0 + 0.0 or abs(vol_mult(0.35, 10) - 1.0) < 1e-9
    assert vol_mult(2.0, n_form=10) == 1.6                    # clamp alto
    assert vol_mult(0.0, n_form=10) == 0.6                    # clamp baixo
