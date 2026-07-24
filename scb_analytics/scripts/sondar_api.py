"""sondar_api — SONDAGEM da API-Futebol antes de gastar o trial (2026-07-22).

Pergunta que este script responde, NA SUA CONTA REAL (não em suposição):
  1. Quanto de cota ainda tenho? (cabeçalhos de rate-limit)
  2. O trial ('acesso completo') libera TEMPORADAS PASSADAS do Brasileirão?
     -> se sim, o transformador (backfill p/ um termo de modelo do BRA) está ao alcance;
     -> se não (403/vazio), o trial só serve p/ terminar a temporada 2026 (marginal).
  3. Qual o FORMATO exato do endpoint de edições passadas (p/ escrever o backfill certo).

Gasta pouca cota (~6-9 chamadas). NÃO baixa a temporada inteira — só sonda e imprime.

RODAR:
  # Windows PowerShell:  $env:APIFUTEBOL_KEY="live_suachave"
  python scripts/sondar_api.py

DEPOIS: me mande o que ele imprimir (ou o conteúdo de dados/_sonda_*.json) que eu monto
o script de backfill com o endpoint EXATO. Nada é inventado — decidimos pelo payload real.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

API = "https://api.api-futebol.com.br/v1"
CAMP_BRA = 10
DADOS = Path(__file__).resolve().parent.parent / "dados"


def _headers():
    key = os.environ.get("APIFUTEBOL_KEY")
    if not key:
        sys.exit("[erro] defina APIFUTEBOL_KEY (sua chave live_... do trial).")
    return {"Authorization": f"Bearer {key}"}


def _get(path):
    """GET cru — devolve (status, json_ou_texto, headers). Nunca levanta: sondagem tolera erro."""
    try:
        r = requests.get(f"{API}{path}", headers=_headers(), timeout=30)
    except Exception as e:
        return (None, f"EXCEPTION {e}", {})
    try:
        body = r.json()
    except Exception:
        body = r.text[:400]
    return (r.status_code, body, dict(r.headers))


def _quota(headers):
    """Imprime qualquer cabeçalho de limite que a API mandar."""
    achou = False
    for k, v in headers.items():
        if any(t in k.lower() for t in ("ratelimit", "rate-limit", "quota", "remaining", "limit")):
            print(f"    {k}: {v}")
            achou = True
    if not achou:
        print("    (a API não mandou cabeçalho de cota nesta resposta)")


def _dump(nome, obj):
    DADOS.mkdir(parents=True, exist_ok=True)
    p = DADOS / f"_sonda_{nome}.json"
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"    -> salvo cru em dados/{p.name}")


def _keys(obj, prefixo=""):
    """Mostra as chaves de topo (e um nível abaixo) sem despejar o payload inteiro."""
    if isinstance(obj, dict):
        for k in obj:
            v = obj[k]
            tipo = type(v).__name__
            amostra = ""
            if isinstance(v, (str, int, float, bool)) or v is None:
                amostra = f" = {v!r}"[:80]
            elif isinstance(v, list):
                amostra = f" [{len(v)} itens]"
            print(f"    {prefixo}{k}: {tipo}{amostra}")
    elif isinstance(obj, list):
        print(f"    {prefixo}(lista de {len(obj)} itens)")
        if obj:
            _keys(obj[0], prefixo="  [0]. ")


def main():
    print("=" * 68)
    print("SONDA API-FUTEBOL — o que o trial te dá agora")
    print("=" * 68)

    # 1) Lista de campeonatos que a SUA chave enxerga + cota
    print("\n[1] GET /campeonatos  (o que o plano libera + cota)")
    st, body, hd = _get("/campeonatos")
    print(f"    status: {st}")
    _quota(hd)
    if st == 200 and isinstance(body, list):
        print(f"    {len(body)} campeonatos visíveis. Procurando Brasileirão / edições:")
        for c in body:
            nome = (c.get("nome") or c.get("nome_popular") or "?")
            if "brasil" in str(nome).lower() or c.get("campeonato_id") == CAMP_BRA:
                print(f"      * {c}")
        _dump("campeonatos", body)
    else:
        print(f"    resposta: {str(body)[:300]}")

    # 2) Detalhe do Brasileirão — mostra se há 'edicao_atual' e se cita edições passadas
    print(f"\n[2] GET /campeonatos/{CAMP_BRA}  (estrutura: edição atual? temporadas?)")
    st, body, hd = _get(f"/campeonatos/{CAMP_BRA}")
    print(f"    status: {st}")
    if st == 200 and isinstance(body, dict):
        _keys(body)
        _dump("campeonato_bra", body)
    else:
        print(f"    resposta: {str(body)[:300]}")

    # 3) Tentativas de endpoint de edições/temporadas passadas — reporta o que existe
    print("\n[3] Caça ao endpoint de TEMPORADAS PASSADAS (o transformador):")
    candidatos = [
        f"/campeonatos/{CAMP_BRA}/edicoes",
        f"/campeonatos/{CAMP_BRA}/temporadas",
        f"/campeonatos/{CAMP_BRA}/partidas?temporada=2024",
        f"/campeonatos/{CAMP_BRA}/tabela?temporada=2024",
    ]
    achou_hist = False
    for path in candidatos:
        st, body, hd = _get(path)
        tam = len(body) if isinstance(body, (list, dict)) else 0
        veredito = "OK (acessível!)" if st == 200 else ("403 = fora do plano" if st == 403 else f"status {st}")
        print(f"    {path}")
        print(f"       -> {veredito}" + (f"  [{tam} campos/itens]" if st == 200 else ""))
        if st == 200:
            achou_hist = True
            safe = path.strip("/").replace("/", "_").replace("?", "_").replace("=", "")
            _dump(safe, body)

    print("\n" + "=" * 68)
    print("VEREDITO RÁPIDO:")
    if achou_hist:
        print("  ✅ Alguma rota de temporada passada respondeu 200 — o TRANSFORMADOR está")
        print("     ao alcance. Me mande os dados/_sonda_*.json e eu monto o backfill exato.")
    else:
        print("  ❌ Nenhuma rota de temporada passada respondeu — o trial provavelmente NÃO")
        print("     expõe histórico. Então o trial só serve p/ terminar a 2026 (marginal):")
        print("     rode  python scripts/baixar_stats_bra.py  e pare por aí.")
    print("=" * 68)


if __name__ == "__main__":
    main()
