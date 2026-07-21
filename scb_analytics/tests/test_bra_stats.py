"""bra_stats (D-34) — parser da API-Futebol (puro) + loader que casa em match_stats do BRA
por (par de times + data ±2d), com alias de nomes. 2ª fonte declarada; não inventa dado."""
from scb import db, ingest


def _partida():                                            # formato real de /partidas/{id}
    return {
        "data_realizacao_iso": "2026-07-16T19:30:00-0300",
        "time_mandante": {"nome_popular": "Botafogo"}, "time_visitante": {"nome_popular": "Santos"},
        "placar_mandante": 2, "placar_visitante": 1,
        "estatisticas": {
            "mandante": {"posse_de_bola": "51%", "escanteios": 5, "faltas": 8, "desarmes": 18,
                         "finalizacao": {"total": 10, "no_gol": 6}, "passes": {"precisao": "78%"},
                         "defensivo": {"defesas": 12}},
            "visitante": {"posse_de_bola": "49%", "escanteios": 6, "faltas": 13, "desarmes": 20,
                          "finalizacao": {"total": 13, "no_gol": 8}, "passes": {"precisao": "84%"},
                          "defensivo": {"defesas": 6}}},
        "gols": {"mandante": [{"periodo_slug": "primeiro-tempo"}, {"periodo_slug": "segundo-tempo"}],
                 "visitante": [{"periodo_slug": "segundo-tempo"}]},
        "cartoes": {"amarelo": {"mandante": [{}, {}, {}, {}], "visitante": [{}, {}]},
                    "vermelho": {"mandante": [], "visitante": []}},
    }


def test_parse_apifutebol_stats():
    r = ingest.parse_apifutebol_stats(_partida())
    assert r["home"] == "Botafogo" and r["away"] == "Santos" and r["date"] == "2026-07-16"
    assert r["sot_home"] == 6 and r["sot_away"] == 8        # finalizacao.no_gol = chutes no gol
    assert r["shots_home"] == 10 and r["corners_home"] == 5 and r["fouls_away"] == 13
    assert r["yellow_home"] == 4 and r["yellow_away"] == 2 and r["red_home"] == 0  # contados
    assert r["ht_home"] == 1 and r["ht_away"] == 0         # 1 gol do mandante no 1º tempo
    assert r["possession_home"] == 51 and r["pass_acc_home"] == 78   # "51%"/"78%" -> int
    assert r["tackles_home"] == 18 and r["saves_home"] == 12
    assert r["home_score"] == 2 and r["away_score"] == 1   # placar (destrava o settle)


def test_parse_apifutebol_sem_estatisticas():
    # jogo não terminado: estatisticas vem como listas vazias -> None (não inventa)
    assert ingest.parse_apifutebol_stats({"estatisticas": {"mandante": [], "visitante": []}}) is None


def test_load_bra_stats_casa_por_alias_e_data(conn, tmp_path):
    fla = db.get_or_create_team(conn, "Flamengo RJ")
    pal = db.get_or_create_team(conn, "Palmeiras")
    conn.execute("""INSERT INTO matches(league,season,date,home_team_id,away_team_id,
                    home_score,away_score,natural_key) VALUES('BRA',2026,'2026-07-16',?,?,2,0,'k1')""",
                 (fla, pal))
    conn.commit()
    p = tmp_path / "bra_stats.csv"
    p.write_text("date,home,away,sot_home,sot_away,corners_home,corners_away,red_home,red_away\n"
                 "2026-07-17,Flamengo,Palmeiras,6,3,7,4,0,1\n", encoding="utf-8")   # data +1d, alias
    assert ingest.load_bra_stats(conn, p) == 1
    r = conn.execute("SELECT * FROM match_stats").fetchone()
    assert r["sot_home"] == 6 and r["corners_home"] == 7 and r["red_away"] == 1


def test_load_bra_stats_insere_resultado_faltante(conn, tmp_path):
    # rodada recém-jogada que o football-data ainda não publicou, mas a API-Futebol tem placar:
    # o resultado entra em matches (destrava o 'Liquidar resultados' do Prospectivo).
    db.get_or_create_team(conn, "Flamengo RJ")
    db.get_or_create_team(conn, "Palmeiras")
    conn.execute("""INSERT INTO matches(league,season,date,home_team_id,away_team_id,
                    home_score,away_score,natural_key)
                    SELECT 'BRA',2026,'2026-06-01',t1.team_id,t2.team_id,1,1,'seed'
                    FROM teams t1, teams t2 WHERE t1.name='Flamengo RJ' AND t2.name='Palmeiras'""")
    conn.commit()   # jogo-semente só p/ os dois times contarem como 'known' do BRA
    p = tmp_path / "s.csv"
    p.write_text("date,home,away,home_score,away_score,sot_home,sot_away,corners_home,corners_away\n"
                 "2026-07-20,Flamengo,Palmeiras,3,1,7,4,8,3\n", encoding="utf-8")
    assert ingest.load_bra_stats(conn, p) == 1
    m = conn.execute("SELECT home_score, away_score FROM matches WHERE date='2026-07-20'").fetchone()
    assert m["home_score"] == 3 and m["away_score"] == 1        # placar da API entrou em matches
    s = conn.execute("SELECT sot_home, corners_home FROM match_stats").fetchone()
    assert s["sot_home"] == 7 and s["corners_home"] == 8


def test_load_bra_stats_sem_jogo_no_banco_pula(conn, tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("date,home,away,sot_home,sot_away\n2026-07-16,Flamengo,Palmeiras,6,3\n",
                 encoding="utf-8")
    assert ingest.load_bra_stats(conn, p) == 0              # sem o jogo -> 0 (não inventa)
    assert conn.execute("SELECT COUNT(*) FROM match_stats").fetchone()[0] == 0
