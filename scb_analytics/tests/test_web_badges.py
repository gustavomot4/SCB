"""M7 — badges (stdlib, testável sem Flask) e sanidade do módulo web."""
from scb import badges


def test_cores_curadas_e_fallback_deterministico():
    assert badges.cores("Flamengo RJ")[0] == "#C3151B"
    assert badges.cores("Palmeiras")[0] == "#006437"
    assert badges.cores("Man City")[0] == "#6CABDD"
    a = badges.cores("Time Inventado XYZ")
    b = badges.cores("Time Inventado XYZ")
    assert a == b                                   # hash determinístico
    assert a[0].startswith("#")


def test_iniciais_estilo_transmissao():
    assert badges.iniciais("Flamengo RJ") == "FLA"  # sufixo UF cai -> código de 3 letras
    assert badges.iniciais("Man City") == "MC"
    assert badges.iniciais("Nott'm Forest") == "NF"
    assert badges.iniciais("Athletico-PR") == "ATH"
    assert badges.iniciais("Palmeiras") == "PAL"


def test_badge_svg_bem_formado():
    svg = badges.badge_svg("Palmeiras")
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert "#006437" in svg and "PAL" in svg


def test_slug():
    assert badges.slug("São Paulo") == "sao-paulo"
    assert badges.slug("Nott'm Forest") == "nott-m-forest"


def test_web_importa_sem_flask():
    """web.py importa sem Flask instalado (import lazy dentro do create_app)."""
    import importlib
    from scb import web
    importlib.reload(web)
    assert hasattr(web, "create_app") and hasattr(web, "temporada_atual")
