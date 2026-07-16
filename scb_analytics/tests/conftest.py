"""Fixtures dos testes M2 — SEM REDE (D-13 SCM): tudo roda sobre CSVs sintéticos."""
import pytest

from scb import db


@pytest.fixture()
def conn():
    c = db.connect(":memory:")
    db.init_schema(c)
    yield c
    c.close()


@pytest.fixture()
def leagues():
    return {
        "BRA": {"family": "extra", "season_format": "ano-calendario"},
        "E0": {"family": "main", "season_format": "cruzada (ago-mai)"},
    }


BRA_HEADER = ("Country,League,Season,Date,Time,Home,Away,HG,AG,Res,"
              "PSCH,PSCD,PSCA,AvgCH,AvgCD,AvgCA,B365CH,B365CD,B365CA")
E0_HEADER = ("Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,"
             "PSH,PSD,PSA,AvgH,AvgD,AvgA,PSCH,PSCD,PSCA")


@pytest.fixture()
def bra_csv(tmp_path):
    """Fábrica: bra_csv(rows) -> Path de um BRA.csv sintético (formato extra medido na M1)."""
    def make(rows, name="BRA.csv"):
        p = tmp_path / name
        p.write_text(BRA_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
        return p
    return make


@pytest.fixture()
def e0_csv(tmp_path):
    """Fábrica: e0_csv(rows) -> Path de um E0 sintético (formato main, pré+fechamento)."""
    def make(rows, name="E0_2425.csv"):
        p = tmp_path / name
        p.write_text(E0_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
        return p
    return make
