"""registrar — registro prospectivo IMUTÁVEL (regra de negócio nº 4) + settle + report.

Fluxo da rodada (runbook no vault):
    python -m scb.registrar register BRA "Flamengo RJ" "Palmeiras" --date 2026-07-19
    ... (após os jogos e o ingest --download + ingest)
    python -m scb.registrar settle
    python -m scb.registrar report

Imutabilidade: `dados/registro-prospectivo.csv` é APPEND-ONLY; registrar de novo o mesmo
jogo não duplica; colunas de previsão NUNCA mudam; `settle` só preenche resultado em linha
aberta (casa por liga+times com data ±2d — tolerância D-80c SCM). Sem isso, a métrica
prospectiva é autoengano (D-07 SCM).
"""
from __future__ import annotations

import argparse
import csv
from datetime import date as _date
from pathlib import Path
from typing import Optional

from . import config, db
from .ingest import DEFAULT_DB
from .predict_match import predict_now

REG = Path(__file__).resolve().parent.parent / "dados" / "registro-prospectivo.csv"
CAMPOS = ["chave", "registrado_em", "league", "date", "home", "away",
          "p_v", "p_e", "p_d", "lambda_a", "lambda_b", "p_over25", "p_btts",
          "versao", "home_score", "away_score", "brier"]


def _linhas():
    if not REG.exists():
        return []
    with REG.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _grava(linhas):
    REG.parent.mkdir(parents=True, exist_ok=True)
    with REG.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS, extrasaction="ignore")
        w.writeheader()
        for r in linhas:
            w.writerow(r)


def register(conn, league: str, home: str, away: str, dt: str) -> dict:
    """Registra a previsão ANTES do kickoff. Idempotente por chave (não duplica)."""
    chave = f"{dt}|{home}|{away}|{league}"
    linhas = _linhas()
    if any(r["chave"] == chave for r in linhas):
        return {"chave": chave, "ja_registrado": True}
    o = predict_now(conn, league, home, away)
    linhas.append({"chave": chave, "registrado_em": _date.today().isoformat(),
                   "league": league, "date": dt, "home": home, "away": away,
                   "p_v": f"{o['p_v']:.6f}", "p_e": f"{o['p_e']:.6f}", "p_d": f"{o['p_d']:.6f}",
                   "lambda_a": f"{o['lambda_a']:.4f}", "lambda_b": f"{o['lambda_b']:.4f}",
                   "p_over25": f"{o['p_over25']:.6f}", "p_btts": f"{o['p_btts']:.6f}",
                   "versao": o["versao"], "home_score": "", "away_score": "", "brier": ""})
    _grava(linhas)
    return {"chave": chave, "ja_registrado": False, "p_v": o["p_v"], "p_e": o["p_e"],
            "p_d": o["p_d"]}


def settle(conn) -> dict:
    """Preenche resultados das linhas abertas a partir de `matches` (data ±2d)."""
    linhas = _linhas()
    n_ok = n_aberto = 0
    for r in linhas:
        if r["home_score"] != "":
            continue
        row = conn.execute(
            """SELECT m.home_score hs, m.away_score aws
               FROM matches m JOIN teams th ON th.team_id=m.home_team_id
               JOIN teams ta ON ta.team_id=m.away_team_id
               WHERE m.league=? AND th.name=? AND ta.name=?
               AND ABS(julianday(m.date)-julianday(?)) <= 2""",
            (r["league"], r["home"], r["away"], r["date"])).fetchone()
        if row is None:
            # fallback p/ jogo ADIADO: o par ORDENADO (casa,fora) é ÚNICO por temporada
            # no turno-returno -> casar o jogo mais próximo APÓS o registro é seguro
            row = conn.execute(
                """SELECT m.home_score hs, m.away_score aws
                   FROM matches m JOIN teams th ON th.team_id=m.home_team_id
                   JOIN teams ta ON ta.team_id=m.away_team_id
                   WHERE m.league=? AND th.name=? AND ta.name=?
                   AND julianday(m.date) >= julianday(?) - 2
                   ORDER BY m.date LIMIT 1""",
                (r["league"], r["home"], r["away"], r["date"])).fetchone()
        if row is None:
            n_aberto += 1
            continue
        hs, aws = row["hs"], row["aws"]
        y = [0.0, 0.0, 0.0]
        y[0 if hs > aws else (1 if hs == aws else 2)] = 1.0
        p = [float(r["p_v"]), float(r["p_e"]), float(r["p_d"])]
        r["home_score"], r["away_score"] = str(hs), str(aws)
        r["brier"] = f"{sum((pi - yi) ** 2 for pi, yi in zip(p, y)):.6f}"
        n_ok += 1
    _grava(linhas)
    return {"preenchidos": n_ok, "em_aberto": n_aberto}


FIXTURES = Path(__file__).resolve().parent.parent / "dados" / "fixtures.csv"


def auto(conn, dias: int = 4, hoje: Optional[str] = None) -> dict:
    """Registra TODOS os jogos do calendário (dados/fixtures.csv) que vencem em até
    `dias` — o botão de 1 clique da rodada. Idempotente (re-registrar não duplica).

    O calendário é colado 1x por temporada (a fonte não traz futuro — lacuna
    declarada). Formato: league,date,home,away (date ISO ou dd/mm/aaaa).
    """
    from .ingest import parse_date
    if not FIXTURES.exists():
        return {"erro": f"calendário não encontrado: {FIXTURES.name} "
                        f"(copie o .example e cole a tabela da temporada)"}
    h = _date.fromisoformat(hoje) if hoje else _date.today()
    novos, ja, fora, erros = [], 0, 0, []
    with FIXTURES.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            iso = parse_date(r.get("date", "")) or (r.get("date") or "").strip()
            try:
                d = _date.fromisoformat(iso)
            except ValueError:
                erros.append(f"data inválida: {r}")
                continue
            if not (0 <= (d - h).days <= dias):
                fora += 1
                continue
            try:
                out = register(conn, r["league"].strip(), r["home"].strip(),
                               r["away"].strip(), iso)
            except (ValueError, KeyError) as e:
                erros.append(f"{r.get('home')}x{r.get('away')}: {e}")
                continue
            if out["ja_registrado"]:
                ja += 1
            else:
                novos.append(f"{r['home']} x {r['away']} ({iso})")
    return {"novos": novos, "n_novos": len(novos), "ja_registrados": ja,
            "fora_da_janela": fora, "erros": erros}


def report() -> dict:
    """Brier prospectivo acumulado vs uniforme (power-aware: n pequeno é dito)."""
    fech = [r for r in _linhas() if r["brier"] != ""]
    n = len(fech)
    if n == 0:
        print("registro sem jogos liquidados ainda.")
        return {"n": 0}
    br = sum(float(r["brier"]) for r in fech) / n
    print(f"Brier prospectivo: {br:.4f} em n={n} (uniforme = 0,667)"
          + ("  [n BAIXO — sem potência p/ afirmar skill; siga registrando]" if n < 60 else ""))
    return {"n": n, "brier": br}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Registro prospectivo imutável.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register"); r.add_argument("league"); r.add_argument("home")
    r.add_argument("away"); r.add_argument("--date", required=True); r.add_argument("--db", default=str(DEFAULT_DB))
    s = sub.add_parser("settle"); s.add_argument("--db", default=str(DEFAULT_DB))
    sub.add_parser("report")
    a = sub.add_parser("auto", help="registra os jogos do fixtures.csv que vencem em até --dias")
    a.add_argument("--dias", type=int, default=4); a.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args(argv)
    if args.cmd == "auto":
        with db.session(args.db) as conn:
            out = auto(conn, dias=args.dias)
        if "erro" in out:
            print(out["erro"]); return 1
        print(f"auto: {out['n_novos']} novos registrados | {out['ja_registrados']} já estavam "
              f"| {out['fora_da_janela']} fora da janela")
        for n in out["novos"]:
            print(f"  + {n}")
        for e in out["erros"]:
            print(f"  ! {e}")
        return 0
    if args.cmd == "register":
        with db.session(args.db) as conn:
            out = register(conn, args.league, args.home, args.away, args.date)
        print("já registrado (imutável — nada mudou)" if out["ja_registrado"]
              else f"registrado: {out['chave']}  V {out['p_v']:.1%} E {out['p_e']:.1%} D {out['p_d']:.1%}")
    elif args.cmd == "settle":
        with db.session(args.db) as conn:
            out = settle(conn)
        print(f"settle: {out['preenchidos']} preenchidos, {out['em_aberto']} em aberto")
    else:
        report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
