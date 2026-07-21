"""baixar_escudos v3 — PNGs/SVGs de escudos p/ static/logos/ (VOCÊ roda; uso pessoal).

QA-05 (v1): chutava pasta → v2 lê a ÁRVORE completa (git/trees).
QA-07 (v2): matching frouxo criou falsos positivos (Juventude←Juventus, Mirassol←
Sassuolo, Portsmouth←Bournemouth) e faltava fonte com BRASIL. A v3:
  - fonte BRA dedicada: hugomiura/escudos-times-brasil-svg (Séries A e B, SVG —
    o <img> renderiza SVG igual; a web aceita .png OU .svg no override);
  - AFINIDADE POR REPO (repo brasileiro só alimenta BRA; europeu só E0) no lugar
    de hint por caminho — mata o vazamento cruzado;
  - cutoff 0,82 no pool da liga; fora do pool SÓ match EXATO de slug;
  - `--limpar` apaga tudo que foi baixado antes (refaz do zero com o matcher novo).

Uso:  cd scb_analytics
      python scripts/baixar_escudos.py --limpar     # 1ª vez após a v2 (remove os errados)
      python scripts/baixar_escudos.py
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scb import badges, db  # noqa: E402
from scb.ingest import DEFAULT_DB  # noqa: E402

# repo -> liga que ele alimenta. "auto" = classifica CADA arquivo pela pasta do
# país no caminho (brazil->BRA, england->E0; resto vai ao pool exato-apenas).
# v4 (QA-08): hugomiura tinha só 4 arquivos (fonte furada) -> substituído pelo
# Leo4815162342 (3.400+ escudos mundiais, SVG+PNG).
REPOS = {"Leo4815162342/football-logos": "auto",
         "sportlogos/football.db.logos": "auto",   # openfootball: pastas br-brazil/ etc.
         "FCLOGO/fclogo.top": "auto",
         "luukhopman/football-logos": "E0",
         "klunn91/team-logos": "E0"}
# hints MEDIDOS no --investigar: FCLOGO organiza por FEDERAÇÃO (Brasil = /CBF/);
# sportlogos usa south-america/br-brazil; Leo só tem bandeiras (1200x630 — filtradas)
PATH_HINTS = {"BRA": ("/cbf/", "br-brazil", "brazil", "brasil"), "E0": ("england", "/the-fa/")}
ALIAS = {
    "man city": "manchester city", "man united": "manchester united",
    "nott'm forest": "nottingham forest", "wolves": "wolverhampton wanderers",
    "west ham": "west ham united", "newcastle": "newcastle united",
    "brighton": "brighton hove albion", "leeds": "leeds united",
    "leicester": "leicester city", "norwich": "norwich city",
    "west brom": "west bromwich albion", "qpr": "queens park rangers",
    "stoke": "stoke city", "swansea": "swansea city", "cardiff": "cardiff city",
    "hull": "hull city", "coventry": "coventry city",
    "birmingham": "birmingham city", "derby": "derby county",
    "bolton": "bolton wanderers", "blackburn": "blackburn rovers",
    "charlton": "charlton athletic", "wigan": "wigan athletic",
    "flamengo rj": "flamengo", "botafogo rj": "botafogo", "vasco": "vasco da gama",
    "atletico-mg": "atletico mineiro", "atletico mg": "atletico mineiro",
    "atletico go": "atletico goianiense", "athletico-pr": "athletico paranaense",
    "bragantino": "red bull bragantino", "america-mg": "america mineiro",
    "america mg": "america mineiro", "chapecoense-sc": "chapecoense",
}
DEST = Path(__file__).resolve().parent.parent / "static" / "logos"
UA = {"User-Agent": "scb-estudo-pessoal"}
EXTS = (".png", ".svg")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def arvore(repo: str) -> list:
    for branch in ("master", "main"):
        try:
            data = json.loads(_get(
                f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1").decode())
            arqs = [(repo, branch, t["path"]) for t in data.get("tree", [])
                    if t["path"].lower().endswith(EXTS)]
            if arqs:
                print(f"  {repo} [{branch}]: {len(arqs)} arquivos de escudo")
                return arqs
        except Exception as e:
            print(f"  {repo} [{branch}]: {e}")
    return []


import re as _re

# QA-09: chaves do ALIAS passam pela MESMA normalização do lookup (nott'm -> nott m)
ALIAS_NORM = {badges.slug(k).replace("-", " "): v for k, v in ALIAS.items()}


def stem_norm(path: str) -> str:
    nome = path.rsplit("/", 1)[-1]
    nome = nome[:nome.rfind(".")]
    s = badges.slug(nome).replace("-", " ")
    s = _re.sub(r"\bv\d+\b", "", s)                   # FCLOGO: sufixo de versão v0000
    s = _re.sub(r"\b\d+x\d+\b", "", s)                # bandeiras 1200x630 (Leo)
    return _re.sub(r"\s+", " ", s).strip()


def _alvo(clube: str) -> str:
    k = badges.slug(clube).replace("-", " ")
    return ALIAS_NORM.get(k, k)


def melhor_match(clube: str, liga: str, pools: dict):
    alvo = _alvo(clube)
    pool = pools.get(liga, [])
    stems = [stem_norm(c[2]) for c in pool]
    hit = difflib.get_close_matches(alvo, stems, n=1, cutoff=0.82)
    if hit:
        return pool[stems.index(hit[0])]
    # estágio 2 (medido no --investigar): nome OFICIAL contém o apelido —
    # todas as palavras do alvo dentro do stem ("flamengo" ⊆ "clube de regatas do
    # flamengo"); desempate pela MAIOR similaridade (evita botafogo-sp etc.)
    alvo_tok = set(alvo.split())
    cands = [(difflib.SequenceMatcher(None, alvo, s).ratio(), i)
             for i, s in enumerate(stems) if alvo_tok <= set(s.split())]
    if cands:
        return pool[max(cands)[1]]
    for c in pools.get(None, []):                     # fora da liga: SÓ exato
        if stem_norm(c[2]) == alvo:
            return c
    return None


def investigar(pools: dict, times: dict) -> None:
    """Imprime a estrutura REAL dos repositórios + candidatos por clube (fim do chute)."""
    todos = [c for lst in pools.values() for c in lst]
    print("\n===== ESTRUTURA (prefixos de pasta com mais arquivos, por repo) =====")
    from collections import Counter
    por_repo: dict = {}
    for repo, br, path in todos:
        pref = "/".join(path.split("/")[:2])
        por_repo.setdefault(repo, Counter())[pref] += 1
    for repo, cnt in por_repo.items():
        print(f"\n{repo}:")
        for pref, n in cnt.most_common(12):
            print(f"  {n:5d}  {pref}")
    print("\n===== CANDIDATOS p/ clubes do BRA sem escudo (3 stems mais próximos) =====")
    stems = [(stem_norm(c[2]), c[2]) for c in todos]
    nomes = [s for s, _ in stems]
    for clube in times.get("BRA", []):
        if any((DEST / f"{badges.slug(clube)}{e}").exists() for e in EXTS):
            continue
        alvo = ALIAS.get(badges.slug(clube).replace("-", " "),
                         badges.slug(clube).replace("-", " "))
        prox = difflib.get_close_matches(alvo, nomes, n=3, cutoff=0.4)
        exemplos = [stems[nomes.index(p)][1] for p in prox]
        print(f"  {clube:20s} -> {exemplos}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limpar", action="store_true",
                    help="apaga os escudos baixados antes (refaz com o matcher v3)")
    ap.add_argument("--investigar", action="store_true",
                    help="NÃO baixa: imprime a estrutura real dos repos + candidatos por clube")
    args = ap.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    if args.limpar:
        n = 0
        for f in list(DEST.glob("*.png")) + list(DEST.glob("*.svg")):
            f.unlink()
            n += 1
        print(f"--limpar: {n} arquivos removidos (recomeço limpo)")
    with db.session(DEFAULT_DB) as conn:
        ligas = [r[0] for r in conn.execute("SELECT DISTINCT league FROM matches ORDER BY league")]
        times = {lg: [r[0] for r in conn.execute(
            """SELECT DISTINCT t.name FROM teams t WHERE t.team_id IN
               (SELECT home_team_id FROM matches WHERE league=?
                UNION SELECT away_team_id FROM matches WHERE league=?)""",
            (lg, lg))] for lg in ligas}
    print("Baixando árvores dos repositórios…")
    pools: dict = {}
    for repo, liga in REPOS.items():
        arqs = arvore(repo)
        if liga != "auto":
            pools.setdefault(liga, []).extend(arqs)
            continue
        for a in arqs:                                # "auto": classifica pelo caminho
            p = a[2].lower()
            destino_pool = None
            for lg, hints in PATH_HINTS.items():
                if any(h in p for h in hints):
                    destino_pool = lg
                    break
            pools.setdefault(destino_pool, []).append(a)
    for lg in ("BRA", "E0"):
        print(f"  pool {lg}: {len(pools.get(lg, []))} arquivos")
    if args.investigar:
        investigar(pools, times)
        return 0
    ok = total = 0
    sem = []
    for lg, clubes in times.items():
        print(f"\n== {lg}: {len(clubes)} clubes ==")
        for clube in clubes:
            total += 1
            ja = [DEST / f"{badges.slug(clube)}{e}" for e in EXTS]
            if any(p.exists() for p in ja):
                ok += 1
                continue
            m = melhor_match(clube, lg, pools)
            if not m:
                sem.append(f"{lg}:{clube}")
                continue
            repo, branch, path = m
            ext = path[path.rfind("."):].lower()
            try:
                url = f"https://raw.githubusercontent.com/{repo}/{branch}/" + \
                      urllib.request.quote(path)
                (DEST / f"{badges.slug(clube)}{ext}").write_bytes(_get(url))
                ok += 1
                print(f"  {clube:24s} <- {path.rsplit('/', 1)[-1]}  [{repo.split('/')[0]}]")
                time.sleep(0.1)
            except Exception as e:
                sem.append(f"{lg}:{clube}")
                print(f"  falhou {clube}: {e}")
    print(f"\n{ok}/{total} escudos em {DEST}")
    if sem:
        print("sem match (badge gerado segue no ar — ou salve o arquivo manualmente):")
        for s in sem:
            print(f"  - {s}")
    print("\nDepois: recarregue a web com Ctrl+F5 (cache já está em no-cache na v0.3).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
