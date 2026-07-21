# Escudos do BRA — RESOLVIDO (2026-07-21, D-37)

> **Este arquivo ficou obsoleto.** A lista manual abaixo não é mais necessária.

Os 16 clubes que faltavam agora vêm dos **escudos oficiais do CDN da API-Futebol**, mapeados
1 a 1 por clube (100% casaram). Basta rodar, uma vez:

```
cd scb_analytics
python scripts/baixar_escudos_bra.py            # os 20 oficiais do BRA (sem chave, sem cota)
python scripts/baixar_escudos.py                # Premier (GitHub) — Coventry/Hull inclusos
```

Depois, no navegador, **Ctrl+F5**. Por que mudou: o matcher por semelhança do GitHub (D-30)
chutava e deixava clubes brasileiros de fora; a própria 2ª fonte de dados (D-34) já entrega o
escudo certo de cada clube. O CDN é público, então não gasta a cota (baixa) da API.

Histórico (o que era a lista manual): Bragantino, Athletico-PR, Bahia, Cruzeiro, Corinthians,
Atlético-MG, São Paulo, Coritiba, Vitória, Internacional, Grêmio, Santos, Mirassol, Remo,
Vasco, Chapecoense — todos cobertos agora pelo script.
