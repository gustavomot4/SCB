"""web — interface local do SCB (M7), estilo EA FC: dark, tipografia condensada, cards.

100% local (Flask). Fonte via Google Fonts CDN COM fallback de sistema — offline a
página funciona igual (regra 2 intacta: nada de rede no CÁLCULO). Escudos: SVG gerado
(`scb/badges.py`, cores reais) com OVERRIDE local `static/logos/<slug>.png`.

Uso:  python -m scb.web            # http://127.0.0.1:5000  (ou o Abrir SCB.bat)
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from . import badges, config, db, draw_curve, predictor, registrar, simulate_league
from .elo_engine import EloParams, sigma_r
from .features_pit import FeatureParams, team_form, vol_mult
from .ingest import DEFAULT_DB
from .predict_match import predict_now

_BASE = Path(__file__).resolve().parent.parent
STATIC = _BASE / "static"
_SIM_CACHE: dict = {}
_FIX_CACHE: dict = {}

# Rótulo de exibição das ligas na web: o código interno segue o padrão football-data
# (E0 = Premier League) e é usado em dados/banco/curvas/config do modelo — trocar SÓ o
# display para "PRE" (padrão BRA), sem tocar no pipeline. Único ponto de verdade.
NOMES_LIGA = {"E0": "PRE"}


def nome_liga(code: str) -> str:
    """Código interno da liga -> rótulo mostrado na web (E0 -> PRE)."""
    return NOMES_LIGA.get(code, code)


def temporada_atual(conn, league: str) -> int:
    return conn.execute("SELECT MAX(season) FROM matches WHERE league=?", (league,)).fetchone()[0]


def clubes_da_temporada(conn, league: str, season: int) -> list:
    return [r[0] for r in conn.execute(
        """SELECT DISTINCT t.name FROM teams t WHERE t.team_id IN
           (SELECT home_team_id FROM matches WHERE league=? AND season=?
            UNION SELECT away_team_id FROM matches WHERE league=? AND season=?)
           ORDER BY t.name""", (league, season, league, season))]


def season_sim(conn, league: str) -> int:
    """Temporada que a 'Tabela Simulada' deve projetar: a mais recente entre o que já está
    em matches e o que o fixtures.csv anuncia. Ex.: PRE 2025/26 terminou -> projeta a
    2026/27 a partir do calendário; BRA 2026 está em curso -> segue em matches."""
    m = conn.execute("SELECT MAX(season) FROM matches WHERE league=?", (league,)).fetchone()[0]
    f = simulate_league.fixtures_season(league)
    cand = [x for x in (m, f) if x is not None]
    return max(cand) if cand else m


def team_info(conn, league: str, name: str) -> dict:
    """Ficha do clube p/ o painel de clique: Elo, ranking Elo na temporada projetada,
    forma recente, jogos no histórico do rating e incerteza (σ)."""
    from .features_pit import team_form
    row = conn.execute("SELECT team_id FROM teams WHERE name=?", (name,)).fetchone()
    if row is None:
        raise ValueError(f"time '{name}' não encontrado")
    tid = row["team_id"]
    rc = conn.execute("SELECT * FROM ratings_current WHERE team_id=?", (tid,)).fetchone()
    if rc is None:
        raise ValueError(f"sem rating para '{name}' — rode o pipeline")
    teams, _, _, elo, _ = simulate_league.current_state(conn, league, season_sim(conn, league))
    ranked = sorted(teams, key=lambda t: elo.get(t, 1500.0), reverse=True)
    rank = ranked.index(tid) + 1 if tid in ranked else None
    return {"team": name, "elo": rc["elo"], "sigma_r": rc["sigma_r"], "n_games": rc["n_games"],
            "provisional": bool(rc["provisional"]), "form": team_form(conn, tid, "9999-12-31")[0],
            "elo_rank": rank, "elo_total": len(teams)}


def _fixtures_rows(league: str) -> list:
    """Linhas do dados/fixtures.csv para a liga (na ordem do arquivo)."""
    import csv
    fx = simulate_league._FIX
    if not fx.exists():
        return []
    out = []
    with fx.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("league") or "").strip() == league:
                rd = (r.get("round") or "").strip()
                out.append({"round": int(rd) if rd.isdigit() else None,
                            "date": (r.get("date") or "").strip(),
                            "home": (r.get("home") or "").strip(),
                            "away": (r.get("away") or "").strip()})
    return out


def fixtures_predicted(conn, league: str) -> list:
    """Cada jogo do fixtures.csv com o PLACAR MAIS PROVÁVEL do modelo. Em lote, mas com a
    MESMA matriz do predict_now (D-34): força por time computada uma vez; λ e placar por
    confronto via predictor.predict — idêntico à porta da frente, só que rápido."""
    rows = _fixtures_rows(league)
    if not rows:
        return []
    ep, fp = EloParams(), FeatureParams()
    cur = {r["team_id"]: r for r in conn.execute("SELECT * FROM ratings_current")}
    nid = {r["name"]: r["team_id"] for r in conn.execute("SELECT team_id, name FROM teams")}
    curve = draw_curve.load(conn, league) or draw_curve.build(conn, league)
    pp = predictor.PredictParams(t_base=config.t_base_for(league), curve=curve)
    H = config.h_for(league)
    md = 0.0
    if config.mando_rolling_for(league):
        from . import mando_rolling
        md = mando_rolling.delta_today(conn, league, config.MANDO_ROLLING_W)
    fc: dict = {}

    def _tf(t):
        if t not in fc:
            fc[t] = team_form(conn, t, "9999-12-31", fp)
        return fc[t]

    out = []
    for r in rows:
        hid, aid = nid.get(r["home"]), nid.get(r["away"])
        if hid is None or aid is None or hid not in cur or aid not in cur:
            continue
        rh, ra = cur[hid], cur[aid]
        fh, dh, nh = _tf(hid); fa, da, na = _tf(aid)
        dr = rh["elo"] - ra["elo"] + (fh - fa) + H + md
        srh = sigma_r(rh["n_games"], ep) * vol_mult(dh, nh)
        sra = sigma_r(ra["n_games"], ep) * vol_mult(da, na)
        sd = math.sqrt(srh ** 2 + sra ** 2 + (fp.sigma_ajuste_c * dh) ** 2 + (fp.sigma_ajuste_c * da) ** 2)
        o = predictor.predict(dr, sd, pp)
        out.append({"round": r.get("round"), "date": r["date"], "home": r["home"], "away": r["away"],
                    "score": o["top5"][0][0], "score_p": o["top5"][0][1],
                    "top3": [list(t) for t in o["top5"][:3]],
                    "p_v": o["p_v"], "p_e": o["p_e"], "p_d": o["p_d"]})
    out.sort(key=lambda x: (x["round"] if x["round"] is not None else 10 ** 6, x["date"], x["home"]))
    return out


def team_recent_stats(conn, league: str, name: str, n: int = 20) -> Optional[dict]:
    """Médias por jogo (últimos `n` jogos COM stats) de chutes/escanteios/cartões etc.
    None quando o time não tem stats na base (ex.: qualquer time do BRA — a fonte não
    fornece). Descritivo: sai direto do match_stats, não passa pelo modelo."""
    row = conn.execute("SELECT team_id FROM teams WHERE name=?", (name,)).fetchone()
    if row is None:
        return None
    rows = conn.execute(
        """SELECT CASE WHEN m.home_team_id=:t THEN ms.shots_home   ELSE ms.shots_away   END sf,
                  CASE WHEN m.home_team_id=:t THEN ms.sot_home     ELSE ms.sot_away     END of,
                  CASE WHEN m.home_team_id=:t THEN ms.corners_home ELSE ms.corners_away END cf,
                  CASE WHEN m.home_team_id=:t THEN ms.fouls_home   ELSE ms.fouls_away   END ff,
                  CASE WHEN m.home_team_id=:t THEN ms.yellow_home  ELSE ms.yellow_away  END yc,
                  CASE WHEN m.home_team_id=:t THEN ms.red_home     ELSE ms.red_away     END rc
           FROM match_stats ms JOIN matches m USING(match_id)
           WHERE (m.home_team_id=:t OR m.away_team_id=:t) AND m.league=:lg
             AND ms.corners_home IS NOT NULL
           ORDER BY m.date DESC LIMIT :n""",
        {"t": row["team_id"], "lg": league, "n": n}).fetchall()
    if not rows:
        return None

    def avg(col):
        vals = [r[col] for r in rows if r[col] is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    return {"n": len(rows), "shots": avg("sf"), "sot": avg("of"), "corners": avg("cf"),
            "fouls": avg("ff"), "yellow": avg("yc"), "red": avg("rc")}


def create_app(db_path=DEFAULT_DB):
    from flask import Flask, jsonify, render_template, request, send_file
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"),
                static_folder=str(STATIC))
    app.jinja_env.filters["nome_liga"] = nome_liga

    def _conn():
        return db.connect(db_path)

    @app.context_processor
    def _globais():
        return {"versao": config.MODEL_VERSION, "nomes_liga": NOMES_LIGA}

    @app.route("/badge/<name>.svg")
    def badge(name):
        # QA-06: max-age=86400 fazia o navegador segurar o badge antigo por 24h e o
        # override baixado "não aparecia" — agora no-cache (app local, perf irrelevante)
        from flask import Response
        base = STATIC / "logos" / badges.slug(name)
        for ext, mime in ((".png", "image/png"), (".svg", "image/svg+xml")):
            arq = base.with_suffix(ext)
            if arq.exists():                   # override local do usuário (uso pessoal)
                r = send_file(arq, mimetype=mime)
                r.headers["Cache-Control"] = "no-cache"
                return r
        return Response(badges.badge_svg(name), mimetype="image/svg+xml",
                        headers={"Cache-Control": "no-cache"})

    @app.route("/")
    @app.route("/predict")
    def predict_page():
        conn = _conn()
        try:
            ligas = [r[0] for r in conn.execute("SELECT DISTINCT league FROM matches ORDER BY league")]
            times = {lg: clubes_da_temporada(conn, lg, temporada_atual(conn, lg)) for lg in ligas}
        finally:
            conn.close()
        return render_template("predict.html", ligas=ligas, times=times, tela="predict")

    @app.route("/api/predict")
    def api_predict():
        lg = request.args.get("league", "BRA")
        home, away = request.args.get("home"), request.args.get("away")
        conn = _conn()
        try:
            o = predict_now(conn, lg, home, away)
        except ValueError as e:
            return jsonify({"erro": str(e)}), 400
        finally:
            conn.close()
        o["top5"] = [list(t) for t in o["top5"]]
        return jsonify(o)

    @app.route("/api/matchstats")
    def api_matchstats():
        lg = request.args.get("league", "BRA")
        home, away = request.args.get("home"), request.args.get("away")
        conn = _conn()
        try:
            return jsonify({"home": team_recent_stats(conn, lg, home),
                            "away": team_recent_stats(conn, lg, away)})
        finally:
            conn.close()

    @app.route("/tabela")
    def tabela_page():
        return render_template("tabela.html", tela="tabela")

    @app.route("/jogos")
    def jogos_page():
        conn = _conn()
        try:
            ligas = [r[0] for r in conn.execute("SELECT DISTINCT league FROM matches ORDER BY league")]
        finally:
            conn.close()
        return render_template("jogos.html", tela="jogos", ligas=ligas)

    @app.route("/api/simulate")
    def api_simulate():
        lg = request.args.get("league", "BRA")
        conn = _conn()
        try:
            season = season_sim(conn, lg)
            n_played = conn.execute("SELECT COUNT(*) FROM matches WHERE league=? AND season=?",
                                    (lg, season)).fetchone()[0]
            key = (lg, season, n_played, config.MODEL_VERSION)
            if key not in _SIM_CACHE:
                _SIM_CACHE.clear()
                _SIM_CACHE[key] = simulate_league.run(conn, lg, season, sims=5000)
        finally:
            conn.close()
        return jsonify(_SIM_CACHE[key])

    @app.route("/api/team")
    def api_team():
        lg = request.args.get("league", "BRA")
        name = request.args.get("team", "")
        conn = _conn()
        try:
            info = team_info(conn, lg, name)
        except ValueError as e:
            return jsonify({"erro": str(e)}), 404
        finally:
            conn.close()
        return jsonify(info)

    @app.route("/api/fixtures")
    def api_fixtures():
        lg = request.args.get("league", "BRA")
        fx = simulate_league._FIX
        mtime = fx.stat().st_mtime if fx.exists() else 0
        key = (lg, config.MODEL_VERSION, mtime)
        if key not in _FIX_CACHE:
            _FIX_CACHE.clear()
            conn = _conn()
            try:
                _FIX_CACHE[key] = fixtures_predicted(conn, lg)
            finally:
                conn.close()
        return jsonify({"league": lg, "jogos": _FIX_CACHE[key]})

    @app.route("/prospectivo")
    def prospectivo_page():
        linhas = registrar._linhas()
        fech = [r for r in linhas if r["brier"] != ""]
        brier = sum(float(r["brier"]) for r in fech) / len(fech) if fech else None
        conn = _conn()
        try:
            ligas = [r[0] for r in conn.execute("SELECT DISTINCT league FROM matches ORDER BY league")]
            times = {lg: clubes_da_temporada(conn, lg, temporada_atual(conn, lg)) for lg in ligas}
        finally:
            conn.close()
        return render_template("prospectivo.html", tela="prospectivo",
                               linhas=list(reversed(linhas)), n=len(linhas),
                               n_fech=len(fech), brier=brier, ligas=ligas, times=times)

    @app.route("/api/registrar", methods=["POST"])
    def api_registrar():
        d = request.get_json(force=True)
        conn = _conn()
        try:
            out = registrar.register(conn, d["league"], d["home"], d["away"], d["date"])
        except (ValueError, KeyError) as e:
            return jsonify({"erro": str(e)}), 400
        finally:
            conn.close()
        return jsonify(out)

    @app.route("/api/settle", methods=["POST"])
    def api_settle():
        conn = _conn()
        try:
            out = registrar.settle(conn)
        finally:
            conn.close()
        return jsonify(out)

    @app.route("/api/registrar-auto", methods=["POST"])
    def api_registrar_auto():
        dias = int((request.get_json(silent=True) or {}).get("dias", 4))
        conn = _conn()
        try:
            out = registrar.auto(conn, dias=dias)
        finally:
            conn.close()
        return jsonify(out)

    return app


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Interface local do SCB (estilo EA FC).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--open", action="store_true", help="abre o navegador")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print("[erro] rode o pipeline antes (ingest/elo/features/draw_curve/predictor).")
        return 1
    app = create_app(args.db)
    if args.open:
        import threading
        import webbrowser
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    print(f"SCB web em http://127.0.0.1:{args.port}  [{config.MODEL_VERSION}] — Ctrl+C para sair")
    app.run(host="127.0.0.1", port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
