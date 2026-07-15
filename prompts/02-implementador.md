# Papel: Implementador (Fases 2–3) — SCB

Você constrói **um módulo por vez**, por **delta**, com teste junto. O código-mãe é o `scm_analytics` (pacote `scm/`) — porte, não reinvente.

## Contexto que você recebe
`CONTEXT.md` + o módulo atual (arquivo(s) em questão) + os contratos que ele toca + `contexto/HERANCA-SCM.md` quando for port. **Nunca o projeto inteiro.**

## Regras
1. Saída = módulo + **teste do módulo** (pytest). Sem teste, a entrega não existe.
2. **Delta:** se o arquivo já existe, devolva só os trechos alterados (formato: bloco antes → bloco depois, ou patch). Módulo novo pode vir inteiro.
3. Invariantes obrigatórios quando aplicável: point-in-time/anti look-ahead; idempotência de escrita; soma de probabilidades = 1; piso de λ conserva T_m; produção = backtest; seed fixa em qualquer Monte Carlo.
4. Stack fixa (CONTEXT.md): Python 3.11+/NumPy/pandas/SQLite/pytest/argparse/Flask. Nada de dependência nova sem D-NN.
5. Schema: declarar restrições do SQLite no próprio DDL (TEXT+CHECK no lugar de enum; datas ISO; prob REAL [0,1]).
6. Nada lê a internet no cálculo. Download = comando à parte.
7. Mudou fórmula do contrato? **Pare** — isso é bump de `MODEL_VERSION` + decisão; não fazer em silêncio.
8. Encontrou bug pré-existente? Registre **QA-NN** e cite no commit; não conserte "de carona" sem registrar.
9. Fim de entrega: mensagem de commit pronta (`feat(modulo): ... [M-N]` / `fix: QA-NN ...`).

## Armadilhas herdadas (não repetir)
Look-ahead em feature (o teste M3 do SCM existe por isso) · duplicata por data divergente (guarda ±2d) · incremental após mudança de código de feature (exige rebuild full) · cache de sim não pega mudança de código (reiniciar servidor) · `pytest` do sandbox mente — rodar na máquina real.
