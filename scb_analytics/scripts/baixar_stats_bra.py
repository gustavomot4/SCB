"""baixar_stats_bra — 2ª fonte (D-34): estatísticas do BRASILEIRÃO via API-Futebol
(api-futebol.com.br). O football-data NÃO traz chutes/escanteios/cartões p/ o Brasil;
a API-Futebol traz (finalizacao.no_gol = chutes no gol/SoT, escanteios, faltas, cartões).
VOCÊ roda, com sua chave grátis — igual ao script de escudos. Uso pessoal/estudo.

SETUP (1x):
  1. Conta grátis em https://www.api-futebol.com.br/  -> copie sua API key (live_...).
  2. Exponha na variável de ambiente:
        Windows PowerShell:  $env:APIFUTEBOL_KEY="live_suachave"
        Windows cmd:         set APIFUTEBOL_KEY=live_suachave
        Linux/Mac:           export APIFUTEBOL_KEY=live_suachave

COTA: o grátis limita requisições/dia. Cada jogo = 1 requisição de detalhe; a temporada
tem ~380 jogos, então é RESUMÍVEL (só busca o que falta) e respeita um teto (--max). Rode
alguns dias até completar a temporada.

FLUXO:
  python scripts/baixar_stats_bra.py            # -> dados/bra_stats.csv (append, resumível)
  python -m scb.ingest                          # casa em match_stats (OFFLINE)
  # reinicie o Abrir SCB.bat -> o painel do Prever Confronto acende p/ os times do BRA

Uso:  python scripts/baixar_stats_bra.py [--max 90]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scb.ingest import parse_apifutebol_stats            # parser PURO (testado no repo)

API = "https://api.api-futebol.com.br/v1"
CAMP_BRA = 10                                            # Campeonato Brasileiro Série A
DADOS = Path(__file__).resolve().parent.parent / "dados"
OUT = DADOS / "bra_stats.csv"
COLS = ["date", "home", "away", "home_score", "away_score", "ht_home", "ht_away", "shots_home", "shots_away",
        "sot_home", "sot_away", "fouls_home", "fouls_away", "corners_home", "corners_away",
        "yellow_home", "yellow_away", "red_home", "red_away",
        "possession_home", "possession_away", "pass_acc_home", "pass_acc_away",
        "tackles_home", "tackles_away", "saves_home", "saves_away"]


def _headers():
    key = os.environ.get("APIFUTEBOL_KEY")
    if not key:
        sys.exit("[erro] defina APIFUTEBOL_KEY (sua chave live_... de api-futebol.com.br). Veja o topo do arquivo.")
    return {"Authorization": f"Bearer {key}"}


def _get(path):
    r = requests.get(f"{API}{path}", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def _flatten(fixtures):
    """partidas vêm aninhadas por fase e rodada -> lista plana de jogos."""
    out = []
    for fase in (fixtures.get("partidas") or {}).values():
        if isinstance(fase, dict):
            for rodada in fase.values():
                if isinstance(rodada, list):
                    out.extend(rodada)
        elif isinstance(fase, list):
            out.extend(fase)
    return out


def _key(p):
    return ((p.get("data_realizacao_iso") or "")[:10],
            (p.get("time_mandante") or {}).get("nome_popular"),
            (p.get("time_visitante") or {}).get("nome_popular"))


def _load_existing():
    """Linhas já no CSV, indexadas por (date,home,away). Ler tudo e reescrever no fim migra o
    schema antigo de graça (o header velho vira o atual) e remove duplicatas."""
    out = {}
    if OUT.exists():
        with OUT.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                out[(r.get("date"), r.get("home"), r.get("away"))] = r
    return out


def _completo(row):
    """Jogo já com o essencial: precisa ter o PLACAR (home_score) — é ele que destrava o
    'Liquidar resultados'. Linhas antigas sem placar/posse são re-buscadas automaticamente."""
    return row is not None and str(row.get("home_score") or "").strip() != ""


def run(max_calls: int):
    partidas = _flatten(_get(f"/campeonatos/{CAMP_BRA}/partidas"))
    fin = [p for p in partidas if p.get("status") == "finalizado"]
    fin.sort(key=lambda p: (p.get("data_realizacao_iso") or ""), reverse=True)   # recentes 1º:
    #   o que importa p/ o 'Liquidar resultados' são as rodadas recém-jogadas — busca elas antes
    #   de gastar o teto do dia com jogos antigos.
    print(f"Brasileirão (campeonato {CAMP_BRA}): {len(partidas)} jogos · {len(fin)} finalizados")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = _load_existing()
    faltam = sum(1 for p in fin if not _completo(rows.get(_key(p))))
    print(f"  já completos: {len(fin) - faltam} · faltam (novos ou sem placar/posse): {faltam}")
    calls = 0
    rate_limited = False
    try:
        for p in fin:
            date, home, away = _key(p)
            if _completo(rows.get((date, home, away))):
                continue                                    # já tem placar+stats (resumível)
            if calls >= max_calls:
                print(f"  teto de {max_calls} chamadas atingido — rode de novo (continua de onde parou).")
                break
            try:
                det = _get(f"/partidas/{p['partida_id']}")
            except requests.HTTPError as e:                 # 429 = limite da API -> para com elegância
                if getattr(e.response, "status_code", None) == 429:
                    print("  429: a API cortou por limite de requisições. PAREI e SALVEI o que já veio — "
                          "rode de novo daqui a pouco (ou amanhã) que continua de onde parou.")
                    rate_limited = True
                    break
                raise
            calls += 1
            time.sleep(1.2)                                 # gentil com o limite da API
            st = parse_apifutebol_stats(det)
            if not st:
                print(f"  sem estatísticas ainda: {date} {home} x {away}")
                continue
            rows[(date, home, away)] = st                   # novo OU completa a linha antiga
            print(f"  + {st['date']} {st['home']} {st.get('home_score')}-{st.get('away_score')} {st['away']}  "
                  f"(SoT {st['sot_home']}-{st['sot_away']} · esc {st['corners_home']}-{st['corners_away']} · "
                  f"posse {st.get('possession_home')}-{st.get('possession_away')})")
    finally:
        _salvar(rows)                                       # SEMPRE grava — 429/erro não perde progresso
    print(f"feito: {calls} jogos buscados nesta rodada · {OUT.name} agora tem {len(rows)} jogos. "
          f"Depois: python -m scb.ingest (casa stats + preenche em matches os resultados que faltam).")


def _salvar(rows):
    """Reescreve o CSV inteiro (dedup, ordenado por data). Self-healing e sem linhas repetidas."""
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for k in sorted(rows, key=lambda x: (x[0] or "")):
            w.writerow(rows[k])
        fh.flush()
        os.fsync(fh.fileno())


def main():
    ap = argparse.ArgumentParser(description="Baixa stats do Brasileirão (API-Futebol) -> bra_stats.csv")
    ap.add_argument("--max", type=int, default=90, help="teto de chamadas por execução (cota grátis)")
    a = ap.parse_args()
    run(a.max)


if __name__ == "__main__":
    main()
