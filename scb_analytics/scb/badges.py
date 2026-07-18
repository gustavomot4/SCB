"""badges — escudos SVG gerados por clube (M7): cores reais + override local.

R$0 e sem ToS: escudos oficiais são marca registrada → geramos um badge SVG com as
CORES do clube (cores não são protegíveis) + iniciais. IMERSÃO com honestidade.
Override local: se existir `static/logos/<slug>.png` (você mesmo salva o arquivo),
a web usa ele no lugar do badge — uso pessoal, decisão do usuário.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

# (primária, secundária, texto) — cores públicas dos clubes [curadas; fallback por hash]
CORES = {
    # BRA
    "flamengo rj": ("#C3151B", "#000000", "#FFFFFF"),
    "palmeiras": ("#006437", "#FFFFFF", "#FFFFFF"),
    "corinthians": ("#000000", "#FFFFFF", "#FFFFFF"),
    "sao paulo": ("#FE0000", "#000000", "#FFFFFF"),
    "santos": ("#111111", "#FFFFFF", "#FFFFFF"),
    "gremio": ("#0D80BF", "#000000", "#FFFFFF"),
    "internacional": ("#E5050F", "#FFFFFF", "#FFFFFF"),
    "cruzeiro": ("#003DA5", "#FFFFFF", "#FFFFFF"),
    "atletico-mg": ("#171717", "#FFFFFF", "#FFFFFF"),
    "atletico mg": ("#171717", "#FFFFFF", "#FFFFFF"),
    "vasco": ("#000000", "#FFFFFF", "#FFFFFF"),
    "botafogo rj": ("#0F0F0F", "#FFFFFF", "#FFFFFF"),
    "fluminense": ("#870A28", "#00613C", "#FFFFFF"),
    "bahia": ("#006CB5", "#E30613", "#FFFFFF"),
    "vitoria": ("#E30613", "#000000", "#FFFFFF"),
    "athletico-pr": ("#C3161C", "#000000", "#FFFFFF"),
    "coritiba": ("#00524C", "#FFFFFF", "#FFFFFF"),
    "bragantino": ("#E30613", "#FFFFFF", "#FFFFFF"),
    "fortaleza": ("#0A3B8C", "#E30613", "#FFFFFF"),
    "ceara": ("#111111", "#FFFFFF", "#FFFFFF"),
    "goias": ("#00693C", "#FFFFFF", "#FFFFFF"),
    "chapecoense-sc": ("#009846", "#FFFFFF", "#FFFFFF"),
    "mirassol": ("#FFD400", "#00693C", "#1A1A1A"),
    "remo": ("#16337D", "#FFFFFF", "#FFFFFF"),
    "sport recife": ("#D40000", "#000000", "#FFFFFF"),
    "cuiaba": ("#00913D", "#FFD400", "#FFFFFF"),
    "juventude": ("#00693C", "#FFFFFF", "#FFFFFF"),
    "figueirense": ("#111111", "#FFFFFF", "#FFFFFF"),
    "ponte preta": ("#111111", "#FFFFFF", "#FFFFFF"),
    "portuguesa": ("#D40000", "#00693C", "#FFFFFF"),
    "nautico": ("#D40000", "#FFFFFF", "#FFFFFF"),
    "america-mg": ("#00693C", "#FFFFFF", "#FFFFFF"),
    "avai": ("#0A3B8C", "#FFFFFF", "#FFFFFF"),
    # E0
    "arsenal": ("#EF0107", "#023474", "#FFFFFF"),
    "man city": ("#6CABDD", "#1C2C5B", "#FFFFFF"),
    "liverpool": ("#C8102E", "#00B2A9", "#FFFFFF"),
    "chelsea": ("#034694", "#FFFFFF", "#FFFFFF"),
    "man united": ("#DA291C", "#FBE122", "#FFFFFF"),
    "tottenham": ("#132257", "#FFFFFF", "#FFFFFF"),
    "newcastle": ("#241F20", "#FFFFFF", "#FFFFFF"),
    "aston villa": ("#670E36", "#95BFE5", "#FFFFFF"),
    "brighton": ("#0057B8", "#FFFFFF", "#FFFFFF"),
    "brentford": ("#E30613", "#FBB800", "#FFFFFF"),
    "fulham": ("#111111", "#FFFFFF", "#FFFFFF"),
    "nott'm forest": ("#DD0000", "#FFFFFF", "#FFFFFF"),
    "everton": ("#003399", "#FFFFFF", "#FFFFFF"),
    "west ham": ("#7A263A", "#1BB1E7", "#FFFFFF"),
    "wolves": ("#FDB913", "#231F20", "#1A1A1A"),
    "bournemouth": ("#DA291C", "#000000", "#FFFFFF"),
    "crystal palace": ("#1B458F", "#C4122E", "#FFFFFF"),
    "leicester": ("#003090", "#FDBE11", "#FFFFFF"),
    "southampton": ("#D71920", "#FFFFFF", "#FFFFFF"),
    "ipswich": ("#0044A9", "#FFFFFF", "#FFFFFF"),
    "coventry": ("#6CB4EE", "#0B1D3A", "#0B1D3A"),   # Sky Blues
    "hull": ("#F5A01A", "#000000", "#000000"),       # Tigers (âmbar e preto)
    "leeds": ("#FFFFFF", "#1D428A", "#1D428A"),
    "sunderland": ("#EB172B", "#FFFFFF", "#FFFFFF"),
    "burnley": ("#6C1D45", "#99D6EA", "#FFFFFF"),
    "west brom": ("#122F67", "#FFFFFF", "#FFFFFF"),
    "middlesbrough": ("#DE1B22", "#FFFFFF", "#FFFFFF"),
}

_PALETA_HASH = ["#E63946", "#2A9D8F", "#E9C46A", "#264653", "#7B2CBF",
                "#0077B6", "#BC4749", "#3A5A40", "#FB8500", "#5E548E"]


def slug(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def iniciais(name: str) -> str:
    """FLA / MC / NF — código curto estilo transmissão (sufixos de UF caem)."""
    stop = {"rj", "sc", "mg", "pr", "fc", "afc", "de", "do", "da"}
    parts = [p for p in re.split(r"[\s\-']+", name) if len(p) > 1]   # descarta 'm de Nott'm
    letras = [p[0] for p in parts if p.lower() not in stop][:3]
    if len(letras) < 2 and parts:
        return parts[0][:3].upper()
    return "".join(letras).upper()


def cores(name: str):
    key = slug(name).replace("-", " ")
    if key in CORES:
        return CORES[key]
    if slug(name) in CORES:
        return CORES[slug(name)]
    h = int(hashlib.md5(slug(name).encode()).hexdigest(), 16)
    return _PALETA_HASH[h % len(_PALETA_HASH)], "#FFFFFF", "#FFFFFF"


def badge_svg(name: str, size: int = 96) -> str:
    """Escudo SVG (determinístico): fundo na cor primária, anel secundário, iniciais."""
    c1, c2, tx = cores(name)
    ini = iniciais(name)
    fs = 34 if len(ini) <= 2 else 26
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 96 96">
<defs><radialGradient id="g" cx="35%" cy="30%"><stop offset="0%" stop-color="#ffffff" stop-opacity="0.25"/><stop offset="100%" stop-color="#000000" stop-opacity="0.15"/></radialGradient></defs>
<path d="M48 4 L86 16 V50 C86 72 68 86 48 92 C28 86 10 72 10 50 V16 Z" fill="{c1}" stroke="{c2}" stroke-width="4"/>
<path d="M48 4 L86 16 V50 C86 72 68 86 48 92 C28 86 10 72 10 50 V16 Z" fill="url(#g)"/>
<text x="48" y="58" text-anchor="middle" font-family="Arial Black, Arial, sans-serif" font-size="{fs}" font-weight="900" fill="{tx}" letter-spacing="1">{ini}</text>
</svg>'''
