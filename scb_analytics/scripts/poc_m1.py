"""POC M1 — inventário completo do football-data (BRA + E0).

Roda NA MÁQUINA DO GUSTAVO (download = passo à parte, regra 2; o cálculo depois é offline).
    cd scb_analytics
    pip install pandas requests
    python scripts/poc_m1.py            # baixa p/ dados/ e gera dados/poc_m1_report.md
    python scripts/poc_m1.py --offline  # só re-analisa o que já está em dados/

Responde as 5 perguntas de contexto/DADOS.md §4:
 1. temporadas/linhas/colunas por temporada; fechamento desde quando (BRA e E0)
 2. qualidade: duplicatas ±3d, placares nulos, aliases de nome de time
 3. taxa de empate e gols/jogo por liga e por era
 4. (decisão D-14 já tomada; este script dá o n que a sustenta)
 5. snapshot versionado em dados/ (este script materializa)
"""
from __future__ import annotations
import argparse, io, os, sys, unicodedata
import pandas as pd

BASE = os.path.join(os.path.dirname(__file__), "..", "dados")
BRA_URL = "https://www.football-data.co.uk/new/BRA.csv"
E0_PATTERN = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"


def e0_codes():
    """9394..2526 (temporada cruzada). Gera códigos tipo '9899', '0001', '2425'."""
    for y in range(1993, 2026):
        yield f"{y % 100:02d}{(y + 1) % 100:02d}"


def download_all():
    import requests
    os.makedirs(BASE, exist_ok=True)
    r = requests.get(BRA_URL, timeout=60)
    r.raise_for_status()
    open(os.path.join(BASE, "BRA.csv"), "wb").write(r.content)
    print(f"BRA.csv: {len(r.content):,} bytes")
    ok = 0
    for code in e0_codes():
        try:
            r = requests.get(E0_PATTERN.format(code=code), timeout=60)
            if r.status_code == 200 and len(r.content) > 1000:
                open(os.path.join(BASE, f"E0_{code}.csv"), "wb").write(r.content)
                ok += 1
        except Exception as e:  # tolerante: temporada faltante vira lacuna declarada
            print(f"  E0 {code}: FALHOU ({e})")
    print(f"E0: {ok} temporadas baixadas")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return "".join(c for c in s.lower() if c.isalnum())


def _read(path):
    """Leitura robusta e DETERMINÍSTICA (QA-01/QA-02 do run de 2026-07-15):
    - QA-01: E0 dos anos 90 é Latin-1/cp1252, não UTF-8 -> tenta encodings em ordem.
    - QA-02: linhas antigas têm campos extras/faltantes; o parser do pandas ou
      DESCARTAVA o jogo (on_bad_lines) ou inventava MultiIndex (inferência do
      engine python). Aqui parseamos com o módulo csv e padronizamos CADA linha
      ao nº de colunas do header (pad/trunca) — nenhuma linha é perdida, nenhuma
      heurística de engine. Números viram numéricos só quando a conversão é
      sem perda; o resto fica string."""
    import csv
    rows = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, encoding=enc, newline="") as fh:
                rows = list(csv.reader(fh))
            break
        except UnicodeDecodeError:
            continue
    if not rows:
        raise ValueError(f"nenhum encoding serviu ou arquivo vazio: {path}")
    header = [h.strip() for h in rows[0]]
    n = len(header)
    fixed = [(r + [""] * n)[:n] for r in rows[1:] if any(c.strip() for c in r)]
    # QA-03: headers antigos têm nomes VAZIOS (vírgula sobrando) e DUPLICADOS ->
    # df[c] viraria DataFrame e quebraria to_numeric. Monta por posição, descarta
    # coluna sem nome e desambigua duplicata com sufixo (sem perder dados).
    df = pd.DataFrame(fixed, columns=range(n))
    keep, names, seen = [], [], {}
    for i, h in enumerate(header):
        if not h:
            continue
        seen[h] = seen.get(h, 0) + 1
        keep.append(i)
        names.append(h if seen[h] == 1 else f"{h}__{seen[h]}")
    df = df[keep]
    df.columns = names
    df = df.replace("", pd.NA)
    for c in df.columns:  # conversão numérica só se 100% sem perda
        conv = pd.to_numeric(df[c], errors="coerce")
        if conv.notna().eq(df[c].notna()).all():
            df[c] = conv
    return df


def load_bra():
    df = _read(os.path.join(BASE, "BRA.csv"))
    df = df.rename(columns={"Home": "home", "Away": "away", "HG": "hg", "AG": "ag",
                            "Res": "res", "Season": "season"})
    df["date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    return df


def load_e0():
    frames = []
    for f in sorted(os.listdir(BASE)):
        if f.startswith("E0_") and f.endswith(".csv"):
            d = _read(os.path.join(BASE, f))
            d = d.rename(columns={"HomeTeam": "home", "AwayTeam": "away", "FTHG": "hg",
                                  "FTAG": "ag", "FTR": "res"})
            d["season"] = f[3:7]
            frames.append(d)
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True).assign(
        date=lambda d: pd.to_datetime(d["Date"], dayfirst=True, errors="coerce"))


def inventory(df, league, close_probe, pre_probe, out):
    out.append(f"\n## {league}\n")
    df = df.dropna(subset=["home", "away"])
    total, nulos = len(df), int(df["hg"].isna().sum())
    out.append(f"- Linhas: **{total:,}** · placares nulos: **{nulos}**")
    per = df.dropna(subset=["hg"]).groupby("season").agg(
        jogos=("res", "size"), times=("home", "nunique"),
        empate=("res", lambda s: (s == "D").mean()),
        gols=("hg", "mean"))
    per["gols"] = per["gols"] + df.dropna(subset=["hg"]).groupby("season")["ag"].mean()
    close_ok = df.groupby("season")[close_probe].apply(lambda s: s.notna().mean()) if close_probe in df else None
    pre_ok = df.groupby("season")[pre_probe].apply(lambda s: s.notna().mean()) if (pre_probe and pre_probe in df) else None
    out.append("\n| temporada | jogos | times | empate% | gols/jogo | close% | pre% |")
    out.append("|---|---|---|---|---|---|---|")
    for s, row in per.iterrows():
        c = f"{close_ok.get(s, 0):.0%}" if close_ok is not None else "—"
        p = f"{pre_ok.get(s, 0):.0%}" if pre_ok is not None else "—"
        out.append(f"| {s} | {row.jogos:.0f} | {row.times:.0f} | {row.empate:.1%} | {row.gols:.2f} | {c} | {p} |")
    j = df.dropna(subset=["hg"])
    out.append(f"\n- **Agregado:** empate {(j['res'] == 'D').mean():.1%} · "
               f"gols/jogo {(j['hg'] + j['ag']).mean():.2f} · temporadas {per.index.min()}–{per.index.max()}")
    # 2. qualidade — duplicatas ±3d (mesma orientação), aliases
    d = df.dropna(subset=["date"]).sort_values("date")
    d = d.merge(d, on=["home", "away", "season"], suffixes=("", "_b"))
    dups = d[(d.date < d.date_b) & ((d.date_b - d.date).dt.days <= 3)]
    out.append(f"- Duplicatas suspeitas (mesmo confronto/temporada ≤3d): **{len(dups)}**")
    for _, r in dups.head(10).iterrows():
        out.append(f"  - {r.home} x {r.away} ({r.season}): {r.date.date()} e {r.date_b.date()}")
    names = pd.Series(sorted(set(df["home"]) | set(df["away"])))
    coll = names.groupby(names.map(_norm)).apply(list)
    coll = coll[coll.str.len() > 1]
    out.append(f"- Aliases suspeitos (nomes que normalizam igual): **{len(coll)}**")
    for k, v in coll.items():
        out.append(f"  - {v}")
    return per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    if not args.offline:
        download_all()
    out = ["# POC M1 — inventário medido (gerado por scripts/poc_m1.py)",
           f"\nGerado em: {pd.Timestamp.now():%Y-%m-%d %H:%M}"]
    bra = load_bra()
    inventory(bra, "BRA (Série A)", close_probe="PSCH", pre_probe=None, out=out)
    b365c = bra.groupby("season")["B365CH"].apply(lambda s: s.notna().mean())
    first_b365 = b365c[b365c > 0.5].index.min() if (b365c > 0.5).any() else "nunca"
    out.append(f"- B365C (fechamento bet365) ≥50% a partir de: **{first_b365}**")
    e0 = load_e0()
    if e0 is not None:
        inventory(e0, "E0 (Premier)", close_probe="PSCH", pre_probe="PSH", out=out)
        if "B365CH" in e0.columns:
            cc = e0.groupby("season")["B365CH"].apply(lambda s: s.notna().mean())
            first_close = cc[cc > 0.5].index.min() if (cc > 0.5).any() else "nunca"
            out.append(f"- Fechamento (B365CH) ≥50% a partir da temporada: **{first_close}**")
        else:
            out.append("- Coluna B365CH ausente em TODAS as temporadas E0 [inesperado — investigar]")
    else:
        out.append("\n## E0 — SEM ARQUIVOS (rode sem --offline)")
    rep = os.path.join(BASE, "poc_m1_report.md")
    open(rep, "w", encoding="utf-8").write("\n".join(out))
    print("\n".join(out))
    print(f"\nRelatório: {rep}")
    print("Próximo: colar a tabela no dev/POC-M1 e fechar o portão da M1 (CHECKLIST).")


if __name__ == "__main__":
    sys.exit(main())
