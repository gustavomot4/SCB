"""M4 — harness: métricas conhecidas, portão aceita skill e rejeita nulo, seed, folds."""
import numpy as np

from scb import backtest_harness as bh


def test_metricas_valores_conhecidos():
    y = np.array([0, 1, 2])
    uni = np.full((3, 3), 1 / 3)
    assert abs(bh.brier(uni, y).mean() - 2 / 3) < 1e-9          # uniforme = 0,667
    perfeito = np.eye(3)[y]
    assert bh.brier(perfeito, y).mean() < 1e-12                 # perfeito = 0
    assert bh.logloss(perfeito, y).mean() < 1e-9
    assert bh.rps(perfeito, y).mean() < 1e-12
    assert abs(bh.logloss(uni, y).mean() - np.log(3)) < 1e-9    # ln 3 ≈ 1,099


def test_portao_aceita_skill_e_rejeita_nulo():
    """Régua do SCM (M5): termo informativo passa; ruído não passa."""
    rng = np.random.default_rng(7)
    n = 4000
    true_p = rng.dirichlet((4, 3, 3), size=n)                   # probs verdadeiras
    y = np.array([rng.choice(3, p=p) for p in true_p])
    modelo_bom = true_p
    d_bom = bh.brier(np.full((n, 3), 1 / 3), y) - bh.brier(modelo_bom, y)
    lo, hi = bh.boot_ci(d_bom, B=2000)
    assert lo > 0                                               # skill real: IC não cruza zero
    ruido = rng.dirichlet((1, 1, 1), size=n)                    # modelo aleatório
    d_ruido = bh.brier(np.full((n, 3), 1 / 3), y) - bh.brier(ruido, y)
    lo2, hi2 = bh.boot_ci(d_ruido, B=2000)
    assert lo2 < 0                                              # sem skill inventado (D-15)


def test_bootstrap_deterministico_por_seed():
    d = np.random.default_rng(1).normal(0.01, 0.1, size=500)
    assert bh.boot_ci(d, B=1000) == bh.boot_ci(d, B=1000)       # mesma seed -> idêntico


def test_ece_zero_quando_calibrado():
    rng = np.random.default_rng(3)
    n = 20000
    p = np.tile(np.array([0.5, 0.3, 0.2]), (n, 1))
    y = np.array([rng.choice(3, p=q) for q in p])
    assert bh.ece(p, y) < 0.02                                  # calibrado -> ECE ~0


def test_walk_forward_folds_sem_overlap(conn):
    """Temporada de teste nunca entra na própria régua/curva (cutoff = S-1)."""
    from scb import db, elo_engine
    a = db.get_or_create_team(conn, "A")
    b = db.get_or_create_team(conn, "B")
    for s in (2012, 2013, 2014, 2015):
        for i in range(20):
            hs, as_ = (1, 1) if (s == 2015 and True) else ((2, 0) if i % 2 else (0, 1))
            d = f"{s}-{(i // 28) + 3:02d}-{(i % 28) + 1:02d}"
            conn.execute("INSERT INTO matches(league,season,date,home_team_id,away_team_id,"
                         "home_score,away_score,natural_key) VALUES (?,?,?,?,?,?,?,?)",
                         ("BRA", s, d, a, b, hs, as_, f"{d}|{i}"))
    conn.commit()
    elo_engine.run(conn)
    from scb import features_pit
    features_pit.run(conn)
    d = bh.collect(conn, "BRA", burn_in=2, n_strata=50)
    assert d["test_seasons"] == [2014, 2015]                    # burn-in respeitado
    assert len(d["Y"]) == 40                                    # só temporadas de teste
    # 2015 é 100% empate; a taxa-base do fold 2015 vem do TREINO (2012-14, sem empate):
    base_2015 = d["P_base"][-1]
    assert base_2015[1] < 0.10                                  # não viu os empates de 2015
