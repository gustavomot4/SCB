"""Camada de dados do SCB: schema SQLite e helpers de conexão.

Port do `scm/db.py` (D-02) adaptado a LIGA (D-03/D-15):
- teams sem confederação/altitude (termos de Copa saíram — D-06);
- matches ganha `league` + `season` (int = ano de início) e perde tournament/city/
  country/neutral (todo jogo de liga tem mando real; "mando invertido" por punição
  não existe na fonte — limitação declarada);
- odds_hist ganha `stage` ('open'|'close') — D-13/D-16;
- seasons: janelas por liga-temporada (virada de temporada / regressão ρ, contrato §3.4);
- tabelas PIT (ratings/features/predictions) declaradas já (aditivo; M3 preenche).

Restrições da stack declaradas no DDL (lição SPO): sem enum nativo -> TEXT + CHECK;
datas ISO-8601 TEXT; probabilidade REAL em [0,1].
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Union

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS matches (
    match_id     INTEGER PRIMARY KEY,
    league       TEXT    NOT NULL CHECK (length(league) > 0),
    season       INTEGER NOT NULL CHECK (season > 1900),
    date         TEXT    NOT NULL CHECK (date LIKE '____-__-__'),
    time         TEXT,
    home_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    away_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    home_score   INTEGER NOT NULL CHECK (home_score >= 0),
    away_score   INTEGER NOT NULL CHECK (away_score >= 0),
    natural_key  TEXT    NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
CREATE INDEX IF NOT EXISTS idx_matches_league_season ON matches(league, season);
-- compostos (time, date): busca point-in-time do features_pit (herdado do SCM)
CREATE INDEX IF NOT EXISTS idx_matches_home_date ON matches(home_team_id, date);
CREATE INDEX IF NOT EXISTS idx_matches_away_date ON matches(away_team_id, date);
CREATE TABLE IF NOT EXISTS seasons (
    league     TEXT    NOT NULL,
    season     INTEGER NOT NULL,
    start_date TEXT,
    end_date   TEXT,
    n_matches  INTEGER,
    PRIMARY KEY (league, season)
);
-- odds de mercado JÁ de-vigged, por fonte e estágio (D-13/D-16).
-- stage: 'open' (pré, só ligas main) | 'close' (fechamento).
-- natural_key permite gravar odds de jogo FUTURO (captura manual em produção, D-77 SCM).
CREATE TABLE IF NOT EXISTS odds_hist (
    natural_key TEXT NOT NULL,
    match_id    INTEGER REFERENCES matches(match_id),
    stage       TEXT NOT NULL CHECK (stage IN ('open','close')),
    source      TEXT NOT NULL,
    p_home REAL CHECK (p_home BETWEEN 0 AND 1),
    p_draw REAL CHECK (p_draw BETWEEN 0 AND 1),
    p_away REAL CHECK (p_away BETWEEN 0 AND 1),
    asof   TEXT,
    PRIMARY KEY (natural_key, stage, source)
);
CREATE INDEX IF NOT EXISTS idx_odds_match ON odds_hist(match_id);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
-- ===== tabelas PIT (M3 preenche; declaradas já p/ evitar migração — estilo SCM) =====
CREATE TABLE IF NOT EXISTS ratings_current (
    team_id     INTEGER PRIMARY KEY REFERENCES teams(team_id),
    elo         REAL    NOT NULL,
    sigma_r     REAL    NOT NULL,
    n_games     INTEGER NOT NULL,
    provisional INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS match_ratings (
    match_id     INTEGER PRIMARY KEY REFERENCES matches(match_id),
    home_elo_pre REAL, away_elo_pre REAL,
    home_n_pre   INTEGER, away_n_pre INTEGER,
    dr           REAL, we_home REAL
);
CREATE TABLE IF NOT EXISTS match_features (
    match_id          INTEGER PRIMARY KEY REFERENCES matches(match_id),
    dr_elo            REAL,
    form_home         REAL, form_away REAL,
    dr_adj            REAL,
    sigma_r_home      REAL, sigma_r_away REAL,
    sigma_ajuste_home REAL, sigma_ajuste_away REAL,
    sigma_dr          REAL,
    n_home_pre        INTEGER, n_away_pre INTEGER
);
CREATE TABLE IF NOT EXISTS predictions (
    match_id      INTEGER NOT NULL REFERENCES matches(match_id),
    versao_modelo TEXT    NOT NULL,
    p_v REAL, p_e REAL, p_d REAL,
    band_pv_lo REAL, band_pv_hi REAL,
    lambda_a REAL, lambda_b REAL,
    p_over25 REAL, p_btts REAL,
    PRIMARY KEY (match_id, versao_modelo)
);
"""


def connect(db_path: Union[str, Path]) -> sqlite3.Connection:
    """Conexão SQLite com row_factory e FKs ligadas. Use ':memory:' nos testes."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def session(db_path: Union[str, Path]):
    """Conexão como context manager: FECHA sempre, mesmo em erro (audit P-I do SCM)."""
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def get_or_create_team(conn: sqlite3.Connection, name: str) -> int:
    """team_id do clube, criando se preciso. Idempotente por `name` (padrão football-data)."""
    row = conn.execute("SELECT team_id FROM teams WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return row["team_id"]
    cur = conn.execute("INSERT INTO teams(name) VALUES (?)", (name,))
    return int(cur.lastrowid)


def set_meta(conn: sqlite3.Connection, key: str, value: object) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
