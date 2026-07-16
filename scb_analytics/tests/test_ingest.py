"""M2 — parser robusto (QA-01/02/03), datas, idempotência, guarda ±2d, dedup, seasons."""
from scb import db, ingest


# ---------------------------------------------------------------- parser (QA da M1)
def test_qa01_encoding_latin1(tmp_path):
    raw = "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nE0,19/08/95,Arsenal,Boro\xa0,1,1,D\n"
    p = tmp_path / "old.csv"
    p.write_bytes(raw.encode("latin-1"))
    rows = ingest.read_rows(p)
    assert len(rows) == 1 and rows[0]["FTR"] == "D"


def test_qa02_linhas_irregulares_nao_perdem_jogo(tmp_path):
    p = tmp_path / "ragged.csv"
    p.write_text("A,B,C,D\n1,2,3,4,,,,,,\n5,6\n7,8,9,10\n", encoding="utf-8")
    rows = ingest.read_rows(p)
    assert len(rows) == 3                                   # nenhuma linha descartada
    assert rows[0]["D"] == "4" and rows[1]["C"] == ""       # extra truncado; faltante vazio


def test_qa03_header_vazio_e_duplicado(tmp_path):
    p = tmp_path / "dirty.csv"
    p.write_text("A,B,,A\n1,2,3,4\n", encoding="utf-8")
    rows = ingest.read_rows(p)
    assert set(rows[0]) == {"A", "B", "A__2"}
    assert rows[0]["A"] == "1" and rows[0]["A__2"] == "4"


def test_parse_date_formatos():
    assert ingest.parse_date("19/05/2012") == "2012-05-19"
    assert ingest.parse_date("19/08/95") == "1995-08-19"    # pivô %y: 95 -> 1995
    assert ingest.parse_date("07/01/01") == "2001-01-07"    # 01 -> 2001
    assert ingest.parse_date("lixo") is None


def test_season_codes():
    assert ingest.season_from_code("9394") == 1993
    assert ingest.season_from_code("0001") == 2000
    assert ingest.season_from_code("2425") == 2024


# ---------------------------------------------------------------- carga BRA (extra)
def test_load_bra_conta_pula_nulo_e_idempotente(conn, bra_csv):
    p = bra_csv([
        "Brazil,Serie A,2024,20/04/2024,20:00,Flamengo RJ,Palmeiras,1,1,D,2.5,3.2,3.0,2.4,3.1,3.1,2.6,3.1,2.9",
        "Brazil,Serie A,2024,21/04/2024,18:30,Santos,Gremio,2,0,H,1.9,3.4,4.2,1.85,3.4,4.3,,,",
        "Brazil,Serie A,2024,22/04/2024,20:00,Bahia,Cruzeiro,,,,,,,,,,,,",   # sem placar (D-12)
    ])
    s = ingest.load_matches(conn, "BRA", "extra", ingest.read_rows(p))
    assert s["inserted"] == 2 and s["skipped"] == 1
    s2 = ingest.load_matches(conn, "BRA", "extra", ingest.read_rows(p))      # de novo
    assert s2["inserted"] == 0                                               # idempotente
    assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 2


def test_odds_bra_so_fechamento_e_fallback(conn, bra_csv):
    from scb import odds
    p = bra_csv([
        "Brazil,Serie A,2024,20/04/2024,20:00,Flamengo RJ,Palmeiras,1,1,D,2.5,3.2,3.0,2.4,3.1,3.1,2.6,3.1,2.9",
        "Brazil,Serie A,2024,21/04/2024,18:30,Santos,Gremio,2,0,H,,,,2.0,3.5,4.0,,,",  # só AvgC
    ])
    ingest.load_matches(conn, "BRA", "extra", ingest.read_rows(p))
    assert conn.execute("SELECT COUNT(*) FROM odds_hist WHERE stage='open'").fetchone()[0] == 0
    m1 = conn.execute("SELECT match_id FROM matches WHERE date='2024-04-20'").fetchone()[0]
    m2 = conn.execute("SELECT match_id FROM matches WHERE date='2024-04-21'").fetchone()[0]
    assert odds.market_read(conn, m1, "close")["source"] == "PS"    # prioridade D-16
    mk = odds.market_read(conn, m2, "close")
    assert mk["source"] == "Avg"                                    # fallback D-16 (Pinnacle morto)
    assert abs(mk["p_v"] + mk["p_e"] + mk["p_d"] - 1.0) < 1e-9


def test_odds_e0_abre_e_fecha(conn, e0_csv):
    p = e0_csv(["E0,16/08/2024,20:00,Man United,Fulham,1,0,H,"
                "1.63,4.38,5.3,1.62,4.36,5.15,1.65,4.23,5.28"])
    ingest.load_matches(conn, "E0", "main", ingest.read_rows(p), season=2024)
    stages = {r[0] for r in conn.execute("SELECT DISTINCT stage FROM odds_hist")}
    assert stages == {"open", "close"}
    assert conn.execute("SELECT season FROM matches").fetchone()[0] == 2024


# ---------------------------------------------------------------- extra + guarda ±2d
def test_extra_guard_2dias(conn, bra_csv, tmp_path, leagues):
    p = bra_csv(["Brazil,Serie A,2026,10/07/2026,21:00,Flamengo RJ,Palmeiras,1,1,D,,,,2.0,3.5,4.0,,,"])
    ingest.load_matches(conn, "BRA", "extra", ingest.read_rows(p))
    extra = tmp_path / "resultados_extra.csv"
    extra.write_text(
        "league,date,home,away,home_score,away_score\n"
        "BRA,11/07/2026,Flamengo RJ,Palmeiras,1,1\n"     # MESMO jogo, data divergente
        "BRA,12/07/2026,Botafogo RJ,Santos,2,0\n",       # jogo novo legítimo
        encoding="utf-8")
    s = ingest.load_extra(conn, extra, leagues)
    assert s["dup_guarded"] == 1 and s["inserted"] == 1
    assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 2
    ssn = conn.execute("SELECT season FROM matches WHERE date='2026-07-12'").fetchone()[0]
    assert ssn == 2026                                   # season derivada (ano-calendário)


def test_dedup_encontra(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "DEFAULT_EXTRA", tmp_path / "nao_existe.csv")
    hid = db.get_or_create_team(conn, "Flamengo RJ")
    aid = db.get_or_create_team(conn, "Palmeiras")
    for iso in ("2026-07-10", "2026-07-11"):             # mesma dupla+placar, ±1d (D-82)
        conn.execute(
            "INSERT INTO matches(league,season,date,home_team_id,away_team_id,"
            "home_score,away_score,natural_key) VALUES ('BRA',2026,?,?,?,1,1,?)",
            (iso, hid, aid, f"{iso}|Flamengo RJ|Palmeiras|BRA"))
    conn.commit()
    dups = ingest.find_near_duplicates(conn)
    assert len(dups) == 1
    assert dups[0]["keep"] < dups[0]["drop"]             # sem pista do extra: mantém a 1ª


def test_seasons_table(conn, bra_csv):
    p = bra_csv([
        "Brazil,Serie A,2024,20/04/2024,20:00,Flamengo RJ,Palmeiras,1,1,D,,,,2,3.5,4,,,",
        "Brazil,Serie A,2024,01/12/2024,16:00,Palmeiras,Flamengo RJ,2,1,H,,,,2,3.5,4,,,",
    ])
    ingest.load_matches(conn, "BRA", "extra", ingest.read_rows(p))
    ingest.update_seasons(conn)
    r = conn.execute("SELECT * FROM seasons WHERE league='BRA' AND season=2024").fetchone()
    assert r["start_date"] == "2024-04-20" and r["end_date"] == "2024-12-01" and r["n_matches"] == 2
