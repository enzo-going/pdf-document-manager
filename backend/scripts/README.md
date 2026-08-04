# scripts/

Scripts de diagnóstico manual — **não** são testes automatizados e não são
coletados pelo pytest. Rodam contra a configuração de desenvolvimento, criando
ou usando o banco local.

| Script | Para quê |
|---|---|
| `diagnostico_imports.py` | Confere se as dependências, os modelos e os blueprints carregam, e lista as rotas registradas |
| `diagnostico_jwt.py` | Gera um token para o admin, decodifica os claims e exercita `GET /api/auth/me` |

```bash
cd backend
python scripts/diagnostico_imports.py
python scripts/diagnostico_jwt.py
```

`diagnostico_jwt.py` faz login com `ADMIN_EMAIL` / `ADMIN_PASSWORD` do `.env`.
Os testes automatizados ficam em [`../tests`](../tests) e rodam com `pytest`.
