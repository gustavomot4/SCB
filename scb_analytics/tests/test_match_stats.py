"""match_stats — ingest de escanteios/cartões/chutes (E0), ausência = NULL, BRA vazio,
idempotência. A tabela é DESCRITIVA: não toca o modelo (nenhum teste de previsão muda)."""
from scb import ingest


def _row_e0(**over):
    r = {"HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": "2", "FTAG": "1",
         "Date": "10/08/2024", "HTHG": "1", "HTAG": "0", "Referee": "M Oliver",
         "HS": "15", "AS": "9", "HST": "6", "AST": "4", "HF": "11", "AF": "13",
         "HC": "7", "AC": "3", "HY": "2", "AY": "3", "HR": "0", "AR": "1"}
    r.update(over)
    return r


def test_e0_popula_escanteios_cartoes_chutes(conn):
    ingest.load_matches(conn, "E0", "main", [_row_e0()], season=2024)
    r = conn.execute("SELECT * FROM match_stats").fetchone()
    assert (r["corners_home"], r["corners_away"]) == (7, 3)
    assert (r["yellow_home"], r["yellow_away"], r["red_home"], r["red_away"]) == (2, 3, 0, 1)
    assert (r["shots_home"], r["sot_home"]) == (15, 6)
    assert (r["ht_home"], r["ht_away"]) == (1, 0)
    assert r["referee"] == "M Oliver"


def test_zero_cartao_vermelho_e_zero_nao_viram_null(conn):
    ingest.load_matches(conn, "E0", "main", [_row_e0(HR="0", AR="0")], season=2024)
    r = conn.execute("SELECT red_home, red_away FROM match_stats").fetchone()
    assert r["red_home"] == 0 and r["red_away"] == 0        # 0 real != ausência


def test_coluna_ausente_vira_null_sem_linha(conn):
    # temporada antiga do football-data sem stats -> nenhuma coluna de stat
    row = {"HomeTeam": "Leeds", "AwayTeam": "Burnley", "FTHG": "0", "FTAG": "0",
           "Date": "11/08/2024"}
    ingest.load_matches(conn, "E0", "main", [row], season=2024)
    assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1   # jogo entra
    assert conn.execute("SELECT COUNT(*) FROM match_stats").fetchone()[0] == 0  # stats não


def test_bra_nao_gera_stats(conn):
    row = {"Home": "Flamengo RJ", "Away": "Palmeiras", "HG": "1", "AG": "1",
           "Date": "20/07/2026", "Season": "2026"}
    ingest.load_matches(conn, "BRA", "extra", [row])
    assert conn.execute("SELECT COUNT(*) FROM match_stats").fetchone()[0] == 0


def test_idempotente(conn):
    ingest.load_matches(conn, "E0", "main", [_row_e0()], season=2024)
    ingest.load_matches(conn, "E0", "main", [_row_e0()], season=2024)   # de novo
    assert conn.execute("SELECT COUNT(*) FROM match_stats").fetchone()[0] == 1
    out = ingest.load_matches(conn, "E0", "main", [_row_e0()], season=2024)
    assert out["stats_rows"] == 1
