"""baixar_escudos_bra — escudos OFICIAIS do Brasileirão. VOCÊ roda.

O baixar_escudos.py casa por SEMELHANÇA em repositórios do GitHub — erra e deixa clubes
brasileiros sem escudo. Aqui os 20 escudos são os OFICIAIS: URLs do CDN da API-Futebol já
MAPEADAS por clube (sem chute, 100% dos clubes da Série A). Baixa do CDN público — não precisa
de chave nem gasta a cota da API — e salva em static/logos/<slug>.svg (a web aceita .svg).

Uso:  cd scb_analytics
      python scripts/baixar_escudos_bra.py            # baixa só os que faltam
      python scripts/baixar_escudos_bra.py --forcar   # rebaixa todos (atualiza os antigos)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scb import badges                                     # noqa: E402

DEST = Path(__file__).resolve().parent.parent / "static" / "logos"
EXTS = (".png", ".svg")
UA = {"User-Agent": "scb-estudo-pessoal"}

# clube (nome do banco) -> escudo OFICIAL (CDN público da API-Futebol). Série A 2026, 20 clubes.
ESCUDOS = {
    "Athletico-PR":   "https://cdn.api-futebol.com.br/times/escudos/677fc73c0814b.svg",
    "Atletico-MG":    "https://cdn.api-futebol.com.br/times/escudos/677fc73a35795.svg",
    "Bahia":          "https://cdn.api-futebol.com.br/times/escudos/677fc749f1800.svg",
    "Botafogo RJ":    "https://cdn.api-futebol.com.br/times/escudos/677fc743454d0.svg",
    "Bragantino":     "https://cdn.api-futebol.com.br/times/escudos/677fc752d567b.svg",
    "Chapecoense-SC": "https://cdn.api-futebol.com.br/times/escudos/677fc8287cf47.svg",
    "Corinthians":    "https://cdn.api-futebol.com.br/times/escudos/677fc7386c4ef.svg",
    "Coritiba":       "https://cdn.api-futebol.com.br/times/escudos/677fc7a85d84c.svg",
    "Cruzeiro":       "https://cdn.api-futebol.com.br/times/escudos/677fc7451529e.svg",
    "Flamengo RJ":    "https://cdn.api-futebol.com.br/times/escudos/677fc73fcec1e.svg",
    "Fluminense":     "https://cdn.api-futebol.com.br/times/escudos/677fc750c6c81.svg",
    "Gremio":         "https://cdn.api-futebol.com.br/times/escudos/677fc735c7d91.svg",
    "Internacional":  "https://cdn.api-futebol.com.br/times/escudos/677fc74bc3190.svg",
    "Mirassol":       "https://cdn.api-futebol.com.br/times/escudos/677fc831214bd.svg",
    "Palmeiras":      "https://cdn.api-futebol.com.br/times/escudos/677fc746b0687.svg",
    "Remo":           "https://cdn.api-futebol.com.br/times/escudos/677fc7625e677.svg",
    "Santos":         "https://cdn.api-futebol.com.br/times/escudos/677fc82a860d4.svg",
    "Sao Paulo":      "https://cdn.api-futebol.com.br/times/escudos/677fc754a5a78.svg",
    "Vasco":          "https://cdn.api-futebol.com.br/times/escudos/677fc702ef04f.svg",
    "Vitoria":        "https://cdn.api-futebol.com.br/times/escudos/677fc74855410.svg",
}


def _tem(clube):
    return any((DEST / f"{badges.slug(clube)}{e}").exists() for e in EXTS)


def run(forcar: bool):
    DEST.mkdir(parents=True, exist_ok=True)
    ok = pulou = falhou = 0
    for clube, url in ESCUDOS.items():
        if _tem(clube) and not forcar:
            pulou += 1
            continue
        try:
            img = requests.get(url, headers=UA, timeout=40)
            img.raise_for_status()
            (DEST / f"{badges.slug(clube)}.svg").write_bytes(img.content)
            ok += 1
            print(f"  {clube:16s} <- {url.rsplit('/', 1)[-1]}")
            time.sleep(0.1)
        except Exception as e:                              # noqa: BLE001 — best-effort
            falhou += 1
            print(f"  falhou {clube}: {e}")
    print(f"\n{ok} baixados · {pulou} já tinham · {falhou} falharam -> {DEST}")
    print("Recarregue a web com Ctrl+F5 (o escudo entra no lugar do badge gerado).")


def main():
    ap = argparse.ArgumentParser(description="Baixa escudos oficiais do BRA (CDN público) -> static/logos/")
    ap.add_argument("--forcar", action="store_true", help="rebaixa mesmo os clubes que já têm escudo")
    run(ap.parse_args().forcar)


if __name__ == "__main__":
    main()
