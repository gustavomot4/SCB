"""Ingestão: football-data.co.uk -> SQLite, parametrizado por liga (D-03/D-04).

Uso (na sua máquina):
    python -m scb.ingest --download              # baixa snapshot (BRA + E0) p/ dados/  (requer rede)
    python -m scb.ingest                         # dados/*.csv -> dados/scb.sqlite (OFFLINE)
    python -m scb.ingest --league BRA            # só uma liga
    python -m scb.ingest --dedup [--apply]       # duplicatas quase-certas (D-82 SCM)

Aceite (BACKLOG M2): migration roda · contagens batem com dados/poc_m1_report.md ·
pytest verde (idempotência, guarda ±2d, anti-nulos, encoding/header sujo QA-01/02/03).

Herança direta do `scm/ingest.py` (D-02): idempotência por natural_key, guarda ±2d,
`--dedup` com remoção de derivadas, resultados_extra.csv (lag da fonte, D-80 SCM),
pular jogo sem placar (D-12 SCM). NADA lê a internet no cálculo — `--download` cria
snapshot em disco (1×); todo o resto roda offline.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from . import db, odds

_BASE = Path(__file__).resolve().parent.parent          # .../scb_analytics
DADOS = _BASE / "dados"
DEFAULT_DB = DADOS / "scb.sqlite"
LEAGUES_JSON = DADOS / "leagues.json"
DEFAULT_EXTRA = DADOS / "resultados_extra.csv"

# famílias de colunas de odds por formato do football-data (medido na M1, D-13):
# extra (BRA): SÓ fechamento; main (E0): abertura E fechamento. Fonte normalizada
# ('PS'/'Avg'/'B365'); o estágio distingue open/close (schema odds_hist).
ODDS_FAMILIES = {
    "extra": {"open": [],
              "close": [("PS", ("PSCH", "PSCD", "PSCA")),
                        ("Avg", ("AvgCH", "AvgCD", "AvgCA")),
                        ("B365", ("B365CH", "B365CD", "B365CA"))]},
    "main": {"open": [("PS", ("PSH", "PSD", "PSA")),
                      ("Avg", ("AvgH", "AvgD", "AvgA")),
                      ("B365", ("B365H", "B365D", "B365A"))],
             "close": [("PS", ("PSCH", "PSCD", "PSCA")),
                       ("Avg", ("AvgCH", "AvgCD", "AvgCA")),
                       ("B365", ("B365CH", "B365CD", "B365CA"))]},
}


# ---------------------------------------------------------------- parser robusto
def read_rows(path: Union[str, Path]) -> list[dict]:
    """Parser determinístico da M1 (QA-01/02/03) — stdlib, sem pandas.

    QA-01: encoding em cascata (utf-8-sig -> cp1252 -> latin-1);
    QA-02: linha com campos extras/faltantes é TRUNCADA/PREENCHIDA ao header
           (nenhum jogo é descartado em silêncio);
    QA-03: coluna de header sem nome cai; nome duplicado ganha sufixo __2.
    """
    rows = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, encoding=enc, newline="") as fh:
                rows = list(csv.reader(fh))
            break
        except UnicodeDecodeError:
            continue
    if not rows:
        raise ValueError(f"arquivo vazio ou encoding desconhecido: {path}")
    header = [h.strip() for h in rows[0]]
    n = len(header)
    keep, names, seen = [], [], {}
    for i, h in enumerate(header):
        if not h:
            continue
        seen[h] = seen.get(h, 0) + 1
        keep.append(i)
        names.append(h if seen[h] == 1 else f"{h}__{seen[h]}")
    out = []
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        r = (r + [""] * n)[:n]
        out.append({names[j]: r[keep[j]].strip() for j in range(len(keep))})
    return out


def parse_date(s: str) -> Optional[str]:
    """dd/mm/yyyy ou dd/mm/yy (pivô do %y: 69-99 -> 19xx; 00-68 -> 20xx) -> ISO."""
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def season_from_code(code: str) -> int:
    """Código de temporada main ('9394','0001','2425') -> ano de INÍCIO (1993, 2000, 2024)."""
    yy = int(code[:2])
    return (1900 + yy) if yy >= 69 else (2000 + yy)


def season_from_date(iso_date: str, season_format: str) -> int:
    """Deriva a temporada da data (usado no resultados_extra sem coluna season)."""
    y, m = int(iso_date[:4]), int(iso_date[5:7])
    if "cruzada" in (season_format or ""):
        return y if m >= 7 else y - 1
    return y  # ano-calendário (BRA)


def _int(v) -> Optional[int]:
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return None


def _float(v) -> Optional[float]:
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return None


def load_leagues(path: Union[str, Path] = LEAGUES_JSON) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: v for k, v in cfg.items() if not k.startswith("_")}


# ---------------------------------------------------------------- download (1x)
def e0_codes(first=1993, last=2025):
    for y in range(first, last + 1):
        yield f"{y % 100:02d}{(y + 1) % 100:02d}"


def download_snapshot(leagues: dict, only: Optional[list] = None,
                      dest_dir: Union[str, Path] = DADOS) -> None:
    """Baixa os CSVs (roda na SUA máquina; único passo com rede — regra 2)."""
    import requests
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    for lg, cfg in leagues.items():
        if only and lg not in only:
            continue
        if cfg["family"] == "extra":
            r = requests.get(cfg["url"], timeout=60)
            r.raise_for_status()
            (dest / f"{lg}.csv").write_bytes(r.content)
            print(f"{lg}.csv: {len(r.content):,} bytes")
        else:
            ok = 0
            for code in e0_codes():
                try:
                    r = requests.get(cfg["url_pattern"].format(season_code=code), timeout=60)
                    if r.status_code == 200 and len(r.content) > 1000:
                        (dest / f"{lg}_{code}.csv").write_bytes(r.content)
                        ok += 1
                except Exception as e:  # temporada faltante = lacuna declarada, não crash
                    print(f"  {lg} {code}: FALHOU ({e})")
            print(f"{lg}: {ok} temporadas baixadas")


# ---------------------------------------------------------------- carga
def _near_duplicate(conn, home_id, away_id, league, date, natural_key,
                    hs=None, as_=None, window_days=2):
    """Mesmo confronto+liga com data a ±window_days e chave diferente (D-82 SCM)."""
    q = ("SELECT match_id, date, home_score, away_score, natural_key FROM matches "
         "WHERE home_team_id=? AND away_team_id=? AND league=? AND natural_key != ? "
         "AND ABS(julianday(date) - julianday(?)) <= ?")
    args = [home_id, away_id, league, natural_key, date, window_days]
    if hs is not None and as_ is not None:
        q += " AND home_score=? AND away_score=?"
        args += [hs, as_]
    return conn.execute(q, args).fetchone()


def _store_odds_row(conn, family: str, row: dict, natural_key: str,
                    match_id: Optional[int], iso_date: str) -> int:
    """Grava as famílias de odds presentes na linha (de-vig; upsert idempotente)."""
    n = 0
    for stage, fams in ODDS_FAMILIES[family].items():
        for source, (ch, cd, ca) in fams:
            oh, od, oa = _float(row.get(ch)), _float(row.get(cd)), _float(row.get(ca))
            if not (oh and od and oa):
                continue
            try:
                mk = odds.implied_probs(oh, od, oa)
            except ValueError:
                continue
            odds.store(conn, natural_key, match_id, stage, source, mk, asof=iso_date)
            n += 1
    return n


# estatísticas de jogo do football-data (só nas ligas 'main'/E0). (col_no_banco, campo_fd)
_STAT_COLS = [("ht_home", "HTHG"), ("ht_away", "HTAG"),
              ("shots_home", "HS"), ("shots_away", "AS"),
              ("sot_home", "HST"), ("sot_away", "AST"),
              ("fouls_home", "HF"), ("fouls_away", "AF"),
              ("corners_home", "HC"), ("corners_away", "AC"),
              ("yellow_home", "HY"), ("yellow_away", "AY"),
              ("red_home", "HR"), ("red_away", "AR")]


def _store_stats_row(conn, row: dict, match_id: Optional[int]) -> int:
    """Upsert das estatísticas do jogo (escanteios/cartões/chutes) em match_stats.
    Idempotente por match_id. Se a linha não traz NENHUMA stat (BRA / temporada antiga),
    não cria registro — lacuna fica declarada como ausência, não como zeros inventados."""
    if match_id is None:
        return 0
    vals = {col: _int(row.get(src)) for col, src in _STAT_COLS}
    ref = (row.get("Referee") or "").strip() or None
    if ref is None and all(v is None for v in vals.values()):
        return 0
    conn.execute(
        """INSERT OR REPLACE INTO match_stats
           (match_id, ht_home, ht_away, shots_home, shots_away, sot_home, sot_away,
            fouls_home, fouls_away, corners_home, corners_away,
            yellow_home, yellow_away, red_home, red_away, referee)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (match_id, vals["ht_home"], vals["ht_away"], vals["shots_home"], vals["shots_away"],
         vals["sot_home"], vals["sot_away"], vals["fouls_home"], vals["fouls_away"],
         vals["corners_home"], vals["corners_away"], vals["yellow_home"], vals["yellow_away"],
         vals["red_home"], vals["red_away"], ref))
    return 1


def load_matches(conn, league: str, family: str, rows: list[dict],
                 season: Optional[int] = None, guard_dups: bool = False) -> dict:
    """Linhas do football-data -> teams + matches + odds_hist. Idempotente (natural_key).

    Campos por família: extra = Home/Away/HG/AG/Season · main = HomeTeam/AwayTeam/FTHG/FTAG
    (season vem do nome do arquivo). Pula jogo sem placar/chave (D-12 SCM).
    """
    cols = (("Home", "Away", "HG", "AG") if family == "extra"
            else ("HomeTeam", "AwayTeam", "FTHG", "FTAG"))
    n_rows = n_ins = n_skip = n_dup = n_odds = n_stats = 0
    for row in rows:
        n_rows += 1
        home, away = (row.get(cols[0]) or "").strip(), (row.get(cols[1]) or "").strip()
        hs, as_ = _int(row.get(cols[2])), _int(row.get(cols[3]))
        iso = parse_date(row.get("Date", ""))
        ssn = season if season is not None else _int(row.get("Season"))
        if not home or not away or hs is None or as_ is None or not iso or ssn is None:
            n_skip += 1
            continue
        nk = f"{iso}|{home}|{away}|{league}"
        hid = db.get_or_create_team(conn, home)
        aid = db.get_or_create_team(conn, away)
        if guard_dups:
            dup = _near_duplicate(conn, hid, aid, league, iso, nk, hs=hs, as_=as_)
            if dup is not None:
                n_dup += 1
                print(f"  [dup-guard D-82] pulado: {iso} {home}x{away} — já existe em "
                      f"{dup['date']} (match_id {dup['match_id']})")
                continue
        cur = conn.execute(
            """INSERT OR IGNORE INTO matches
               (league, season, date, time, home_team_id, away_team_id,
                home_score, away_score, natural_key)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (league, ssn, iso, (row.get("Time") or "").strip() or None,
             hid, aid, hs, as_, nk))
        if cur.rowcount:
            n_ins += 1
        mid = conn.execute("SELECT match_id FROM matches WHERE natural_key=?",
                           (nk,)).fetchone()
        mid_id = mid["match_id"] if mid else None
        n_odds += _store_odds_row(conn, family, row, nk, mid_id, iso)
        n_stats += _store_stats_row(conn, row, mid_id)
    conn.commit()
    return {"rows": n_rows, "inserted": n_ins, "skipped": n_skip,
            "dup_guarded": n_dup, "odds_rows": n_odds, "stats_rows": n_stats}


def update_seasons(conn) -> None:
    """Janelas por liga-temporada (contrato §3.4: virada de temporada / promovidos)."""
    conn.execute("DELETE FROM seasons")
    conn.execute(
        """INSERT INTO seasons(league, season, start_date, end_date, n_matches)
           SELECT league, season, MIN(date), MAX(date), COUNT(*)
           FROM matches GROUP BY league, season""")
    conn.commit()


def load_extra(conn, path: Union[str, Path], leagues: dict) -> dict:
    """resultados_extra.csv (D-80 SCM): jogos que a fonte ainda não publicou.

    Colunas: league,date,home,away,home_score,away_score[,season][,time]
    (date em dd/mm/yyyy ou ISO; season derivada da data se ausente).
    Sempre com guarda ±2d (D-82) — é o caminho que criou a duplicata no SCM.
    """
    n_ins = n_dup = n_skip = 0
    for r in read_rows(path):
        lg = (r.get("league") or "").strip()
        iso = parse_date(r.get("date", "")) or ((r.get("date") or "").strip() or None)
        if iso and not (len(iso) == 10 and iso[4] == "-"):
            iso = None
        home, away = (r.get("home") or "").strip(), (r.get("away") or "").strip()
        hs, as_ = _int(r.get("home_score")), _int(r.get("away_score"))
        if lg not in leagues or not iso or not home or not away or hs is None or as_ is None:
            n_skip += 1
            continue
        ssn = _int(r.get("season")) or season_from_date(iso, leagues[lg].get("season_format", ""))
        nk = f"{iso}|{home}|{away}|{lg}"
        hid = db.get_or_create_team(conn, home)
        aid = db.get_or_create_team(conn, away)
        if _near_duplicate(conn, hid, aid, lg, iso, nk) is not None:  # qualquer placar
            n_dup += 1
            print(f"  [dup-guard D-82] extra pulado: {iso} {home}x{away}")
            continue
        cur = conn.execute(
            """INSERT OR IGNORE INTO matches
               (league, season, date, time, home_team_id, away_team_id,
                home_score, away_score, natural_key)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (lg, ssn, iso, (r.get("time") or "").strip() or None, hid, aid, hs, as_, nk))
        n_ins += cur.rowcount
    conn.commit()
    return {"inserted": n_ins, "dup_guarded": n_dup, "skipped": n_skip}


# ---------------------------------------------------------------- dedup (D-82)
def find_near_duplicates(conn, window_days: int = 2) -> list:
    """Pares quase-idênticos (mesma orientação+liga+placar, datas ±window, chaves diferentes).
    `drop` prefere a linha vinda do resultados_extra.csv; senão, a inserida por último."""
    extra_keys = set()
    if DEFAULT_EXTRA.exists():
        for r in read_rows(DEFAULT_EXTRA):
            iso = parse_date(r.get("date", "")) or (r.get("date") or "").strip()
            if iso and r.get("home") and r.get("away") and r.get("league"):
                extra_keys.add(f"{iso}|{r['home'].strip()}|{r['away'].strip()}|{r['league'].strip()}")
    rows = conn.execute(
        """SELECT m1.match_id id1, m2.match_id id2, m1.date d1, m2.date d2,
                  m1.natural_key k1, m2.natural_key k2,
                  th.name home, ta.name away, m1.home_score hs, m1.away_score aws, m1.league lg
           FROM matches m1
           JOIN matches m2 ON m1.home_team_id=m2.home_team_id AND m1.away_team_id=m2.away_team_id
                AND m1.league=m2.league AND m1.match_id < m2.match_id
                AND m1.home_score=m2.home_score AND m1.away_score=m2.away_score
                AND ABS(julianday(m1.date)-julianday(m2.date)) <= ?
           JOIN teams th ON th.team_id=m1.home_team_id
           JOIN teams ta ON ta.team_id=m1.away_team_id""", (window_days,)).fetchall()
    out = []
    for r in rows:
        if r["k2"] in extra_keys and r["k1"] not in extra_keys:
            keep, drop, drop_key, motivo = r["id1"], r["id2"], r["k2"], "linha veio do resultados_extra"
        elif r["k1"] in extra_keys and r["k2"] not in extra_keys:
            keep, drop, drop_key, motivo = r["id2"], r["id1"], r["k1"], "linha veio do resultados_extra"
        else:
            keep, drop, drop_key, motivo = r["id1"], r["id2"], r["k2"], "sem pista; descarta a última"
        out.append({"keep": keep, "drop": drop, "drop_key": drop_key, "motivo": motivo,
                    "home": r["home"], "away": r["away"], "hs": r["hs"], "aws": r["aws"],
                    "d1": r["d1"], "d2": r["d2"], "league": r["lg"]})
    return out


def _remove_extra_line(natural_key: str) -> bool:
    if not DEFAULT_EXTRA.exists():
        return False
    rows = read_rows(DEFAULT_EXTRA)
    fields = ["league", "date", "home", "away", "home_score", "away_score", "season", "time"]
    keep = []
    for r in rows:
        iso = parse_date(r.get("date", "")) or (r.get("date") or "").strip()
        nk = f"{iso}|{(r.get('home') or '').strip()}|{(r.get('away') or '').strip()}|{(r.get('league') or '').strip()}"
        if nk != natural_key:
            keep.append(r)
    if len(keep) == len(rows):
        return False
    with DEFAULT_EXTRA.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in keep:
            w.writerow(r)
    return True


def dedup(db_path, apply: bool = False, window_days: int = 2) -> dict:
    """Lista (apply=True: REMOVE) duplicatas quase-certas + derivadas (D-82 SCM).
    Após aplicar: REBUILD COMPLETO (elo_engine/features_pit/predictor — M3+)."""
    with db.session(db_path) as conn:
        dups = find_near_duplicates(conn, window_days)
        removed = 0
        for d in dups:
            print(f"  {d['d1']} / {d['d2']}  {d['home']} {d['hs']}x{d['aws']} {d['away']} "
                  f"({d['league']}) -> manter {d['keep']}, remover {d['drop']} [{d['motivo']}]")
            if apply:
                for tab in ("predictions", "match_features", "match_ratings", "odds_hist", "matches"):
                    conn.execute(f"DELETE FROM {tab} WHERE match_id=?", (d["drop"],))
                if _remove_extra_line(d["drop_key"]):
                    print(f"    linha removida do resultados_extra.csv ({d['drop_key']})")
                removed += 1
        if apply and removed:
            conn.commit()
            print(f"\n  {removed} removida(s). REBUILD COMPLETO obrigatório (M3+).")
        elif not dups:
            print("  nenhuma duplicata quase-certa encontrada.")
    return {"encontradas": len(dups), "removidas": removed}


# ---------------------------------------------------------------- orquestração
def ingest_all(db_path=DEFAULT_DB, leagues: Optional[dict] = None,
               only: Optional[list] = None, csv_dir: Union[str, Path] = DADOS) -> dict:
    leagues = leagues or load_leagues()
    csv_dir = Path(csv_dir)
    stats = {}
    with db.session(db_path) as conn:
        db.init_schema(conn)
        for lg, cfg in leagues.items():
            if only and lg not in only:
                continue
            s = {"rows": 0, "inserted": 0, "skipped": 0, "dup_guarded": 0, "odds_rows": 0}
            if cfg["family"] == "extra":
                f = csv_dir / f"{lg}.csv"
                if f.exists():
                    r = load_matches(conn, lg, "extra", read_rows(f))
                    s = {k: s[k] + r.get(k, 0) for k in s}
            else:
                for f in sorted(csv_dir.glob(f"{lg}_*.csv")):
                    code = f.stem.split("_")[1]
                    r = load_matches(conn, lg, "main", read_rows(f),
                                     season=season_from_code(code))
                    s = {k: s[k] + r.get(k, 0) for k in s}
            s["total"] = conn.execute(
                "SELECT COUNT(*) FROM matches WHERE league=?", (lg,)).fetchone()[0]
            stats[lg] = s
        update_seasons(conn)
        db.set_meta(conn, "source", "football-data.co.uk")
        db.set_meta(conn, "leagues", ",".join(sorted(stats)))
    return stats


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Ingestão football-data -> SQLite (por liga).")
    p.add_argument("--download", action="store_true", help="baixa snapshot (requer rede)")
    p.add_argument("--league", action="append", help="restringe a liga(s) (ex.: --league BRA)")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--csv-dir", default=str(DADOS))
    p.add_argument("--extra", default=None,
                   help="CSV de resultados manuais (default: dados/resultados_extra.csv se existir)")
    p.add_argument("--dedup", action="store_true")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args(argv)

    leagues = load_leagues()
    if args.dedup:
        r = dedup(args.db, apply=args.apply)
        return 0
    if args.download:
        download_snapshot(leagues, only=args.league)

    stats = ingest_all(args.db, leagues, only=args.league, csv_dir=args.csv_dir)
    extra = args.extra or (str(DEFAULT_EXTRA) if DEFAULT_EXTRA.exists() else None)
    if extra and Path(extra).exists():
        with db.session(args.db) as conn:
            ex = load_extra(conn, extra, leagues)
            update_seasons(conn)
        print(f"  + resultados manuais: {ex['inserted']} novos"
              + (f" | {ex['dup_guarded']} barrados (guarda D-82)" if ex["dup_guarded"] else ""))
    for lg, s in stats.items():
        print(f"{lg}: {s['total']} jogos na base | novos {s['inserted']} | pulados {s['skipped']} "
              f"| odds gravadas {s['odds_rows']}")
    print(f"db={args.db}\nAceite M2: confira os totais contra dados/poc_m1_report.md "
          f"(BRA 5.497 linhas -> 5.496 jogos [1 nulo]; E0 12.704).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
