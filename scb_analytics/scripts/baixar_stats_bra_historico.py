"""baixar_stats_bra_historico — BACKFILL de temporadas PASSADAS do Brasileirão (2026-07-22).

Por quê: a sonda (sondar_api.py) confirmou que o trial de 'acesso completo' libera o
histórico via query param -> GET /campeonatos/10/partidas?temporada=AAAA (200 OK).
Uma temporada só (a 2026 parcial) NÃO gateia termo de modelo; o histórico SIM. Este é o
ÚNICO ganho perecível do trial: capturar um snapshot LOCAL das temporadas passadas com
chutes-no-gol (SoT) por jogo -> alimenta `match_stats` do BRA -> vira o dataset de um
futuro termo SoT->gols no BRA (à la D-33, que passou na E0). Depois disso: R$0 e offline
p/ sempre (regra 1), trial pode expirar.

AUTOVERIFICAÇÃO: o detalhe de jogo antigo PODE vir só com placar (sem SoT). O script
CHECA o 1º jogo antigo e avisa em alto e bom som — se vier sem SoT, o histórico serve
p/ pouco e você para (não gasta o trial à toa). Nada é suposto: decide pelo dado real.

RODAR (com a chave do trial exposta em APIFUTEBOL_KEY):
  python scripts/baixar_stats_bra_historico.py --temporadas 2025 2024 2023 2022 2021 2020 --max 300
  python -m scb.ingest        # casa o histórico em match_stats (past seasons já estão em `matches`)

Resumível (só busca o que falta) · trata 429 (salva sempre, retoma depois) · escreve no
MESMO dados/bra_stats.csv (a chave é data+times, única por temporada) -> convive com a
coleta da 2026. Custo: ~380 chamadas por temporada + 1 de listagem. Rode em levas.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

# a própria pasta scripts/ e a raiz do pacote no path (roda de qualquer cwd)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from scb.ingest import parse_apifutebol_stats
# reusa os helpers JÁ TESTADOS do coletor da temporada corrente (DRY, mesmo formato)
from baixar_stats_bra import (CAMP_BRA, OUT, _completo, _flatten, _get, _key,
                              _load_existing, _salvar)


def _tem_sot(st) -> bool:
    a = str(st.get("sot_home") or "").strip()
    b = str(st.get("sot_away") or "").strip()
    return (a not in ("", "0")) or (b not in ("", "0"))


def run(temporadas, max_calls):
    rows = _load_existing()
    calls = 0
    checou = False
    try:
        for ano in temporadas:
            try:
                partidas = _flatten(_get(f"/campeonatos/{CAMP_BRA}/partidas?temporada={ano}"))
            except requests.HTTPError as e:
                sc = getattr(e.response, "status_code", None)
                print(f"[{ano}] a listagem falhou (status {sc}) — pulo esta temporada.")
                if sc == 429:
                    print("  429 na listagem: para com elegância; rode de novo mais tarde.")
                    return
                continue
            fin = [p for p in partidas if p.get("status") == "finalizado"]
            fin.sort(key=lambda p: (p.get("data_realizacao_iso") or ""))     # cronológico
            faltam = sum(1 for p in fin if not _completo(rows.get(_key(p))))
            print(f"[{ano}] {len(partidas)} jogos · {len(fin)} finalizados · faltam {faltam}")
            for p in fin:
                k = _key(p)
                if _completo(rows.get(k)):
                    continue
                if calls >= max_calls:
                    print(f"  teto de {max_calls} chamadas atingido — rode de novo (continua de onde parou).")
                    return
                try:
                    det = _get(f"/partidas/{p['partida_id']}")
                except requests.HTTPError as e:
                    if getattr(e.response, "status_code", None) == 429:
                        print("  429: a API cortou por limite. PAREI e SALVEI — rode de novo depois (retoma).")
                        return
                    raise
                calls += 1
                time.sleep(1.2)                                              # gentil com a cota
                st = parse_apifutebol_stats(det)
                if not st:
                    print(f"  sem estatísticas: {k}")
                    continue
                if not checou:                                              # verificação única e honesta
                    checou = True
                    ok = _tem_sot(st)
                    print("  " + "-" * 60)
                    print(f"  [CHECK] 1º jogo antigo ({st['date']} {st['home']} x {st['away']}): "
                          f"SoT {st.get('sot_home')}-{st.get('sot_away')}")
                    if ok:
                        print("  [CHECK] ✅ o detalhe antigo TEM SoT — o backfill VALE (transformador real).")
                    else:
                        print("  [CHECK] ⚠️  veio SEM SoT (só placar). O histórico NÃO serve p/ o termo")
                        print("           SoT->gols. Se as próximas linhas também vierem 0-0 de SoT, PARE")
                        print("           (Ctrl+C) e não gaste o trial — o transformador não está aqui.")
                    print("  " + "-" * 60)
                rows[k] = st
                print(f"  + {st['date']} {st['home']} {st.get('home_score')}-{st.get('away_score')} {st['away']}  "
                      f"(SoT {st['sot_home']}-{st['sot_away']} · posse {st.get('possession_home')}-{st.get('possession_away')})")
    finally:
        _salvar(rows)                                                       # 429/erro nunca perde progresso
    print(f"feito: {calls} jogos buscados nesta rodada · {OUT.name} agora tem {len(rows)} jogos. "
          f"Depois: python -m scb.ingest (casa o histórico em match_stats).")


def main():
    ap = argparse.ArgumentParser(description="Backfill de temporadas passadas do Brasileirão (API-Futebol) -> bra_stats.csv")
    ap.add_argument("--temporadas", nargs="+", type=int,
                    default=[2025, 2024, 2023, 2022, 2021, 2020],
                    help="anos a baixar, na ordem (default: 2025..2020, recentes primeiro)")
    ap.add_argument("--max", type=int, default=300, help="teto de chamadas por execução (trial dá folga; ajuste)")
    a = ap.parse_args()
    print(f"temporadas alvo: {a.temporadas} · teto/execução: {a.max}")
    run(a.temporadas, a.max)


if __name__ == "__main__":
    main()
