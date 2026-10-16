# PDF Document Manager

[![tests](https://github.com/enzo-going/pdf-document-manager/actions/workflows/tests.yml/badge.svg)](https://github.com/enzo-going/pdf-document-manager/actions/workflows/tests.yml)

Sistema web para gerenciamento de documentos PDF com autenticação JWT,
adição de metadados e painel de analytics.

## Funcionalidades

- Autenticação JWT com controle de papéis (Admin / User / Viewer)
- Upload de PDFs com validação
- Gestão de metadados do documento
- Dashboard com métricas e gráficos
- Registro de auditoria das ações

> Assinatura digital ainda **não** está implementada. A configuração reserva as
> variáveis de um provedor externo, mas não há código de integração no projeto.

## Arquitetura

```
.
├── backend/
│   ├── app/
│   │   ├── routes/      # Endpoints da API (auth, documentos, analytics)
│   │   ├── services/    # Regras de negócio (PDF, metadados, lote)
│   │   ├── utils/       # Validadores e helpers
│   │   ├── models.py    # Modelos do banco
│   │   ├── config.py    # Configuração via variáveis de ambiente
│   │   └── __init__.py  # Application factory
│   ├── tests/           # Testes automatizados (pytest)
│   ├── scripts/         # Diagnósticos manuais (não são testes)
│   ├── requirements.txt
│   └── run.py           # Ponto de entrada
└── frontend/            # Interface estática (HTML/CSS/JS)
```

## Requisitos

- Python 3.11+
- pip

## Configuração

Todas as configurações sensíveis são lidas de variáveis de ambiente. Nenhum
valor real é versionado — use o arquivo de exemplo como base:

```powershell
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
# source venv/bin/activate

pip install -r requirements.txt

# Crie seu .env local a partir do exemplo e preencha os valores
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
```

Edite `backend/.env` com os seus próprios valores. As chaves principais:

| Variável | Descrição |
|----------|-----------|
| `FLASK_ENV` | `development` (padrão), `production` ou `testing` |
| `SECRET_KEY` / `JWT_SECRET_KEY` | Chaves de sessão e JWT |
| `DATABASE_URL` | URL do banco (SQLite por padrão) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Admin criado no primeiro start |
| `COMPANY_NAME` / `DEFAULT_LOCATION` | Rótulos exibidos na aplicação |
| `CORS_ORIGINS` | Origens que podem chamar a API, separadas por vírgula (`*` libera todas, o padrão) |
| `DOCUSIGN_*` | Reservadas para assinatura digital; sem uso hoje |

O primeiro administrador é criado automaticamente a partir de `ADMIN_EMAIL` e
`ADMIN_PASSWORD`. Defina uma senha forte antes de subir a aplicação.

Com `FLASK_ENV=production` a aplicação **se recusa a subir** se `SECRET_KEY`,
`JWT_SECRET_KEY` ou `ADMIN_PASSWORD` ainda estiverem com um valor de exemplo
(`change-me` e os padrões do código): esses valores estão publicados e permitem
forjar o token de qualquer usuário. Em produção, `/debug/routes` também não existe.
O `.env.example` já restringe o `CORS_ORIGINS` a `http://localhost:3000` e
`http://127.0.0.1:5500`, então a interface precisa ser servida por HTTP (veja
[Execução](#execução)): aberta direto do disco, o navegador manda a origem `null`
e a API recusa as chamadas.

## Execução

```bash
cd backend
python run.py
```

A API sobe em `http://localhost:5000`. Em outro terminal, na raiz do
repositório, sirva a interface na porta que o `.env.example` libera:

```bash
python -m http.server 5500 --bind 127.0.0.1 --directory frontend
```

e abra <http://127.0.0.1:5500>. Abrir o `frontend/index.html` direto do disco não
funciona com o `CORS_ORIGINS` do exemplo (origem `null`).

O `run.py` escuta só nesta máquina (`127.0.0.1`). Para abrir na rede, defina
`HOST=0.0.0.0`; nesse caso o depurador do Werkzeug fica desligado mesmo com
`FLASK_ENV=development`, porque ele executa código pelo navegador. Em produção,
use um servidor WSGI como o `gunicorn`, que já está nas dependências.

## Testes

```bash
cd backend
pytest -v
```

O que a suíte cobre:

- **Autenticação** (`test_auth.py`): login (sucesso, email inexistente, senha
  errada, campos faltando, conta desativada), `GET /api/auth/me` com e sem token,
  gestão de usuários e papéis, renovação de token (recusando access token na rota
  de refresh), logout e troca de senha
- **Documentos** (`test_documents.py`): upload (título, páginas, recusa de
  extensão, de PDF inválido e de duplicata, arquivos de mesmo nome no mesmo
  envio), busca e filtro por tipo, metadados, download e exclusão simples e em
  lote. A exclusão mantém a auditoria e só apaga o arquivo depois do commit
- **Configuração** (`test_config.py`): produção recusa segredo e senha de admin de
  exemplo, ambiente desconhecido falha em vez de cair em desenvolvimento,
  `CORS_ORIGINS`, `/debug/routes` só em debug, endereço, porta e depurador do `run.py`
- **Permissões** (`test_decorators.py`): erro dentro da rota não vira erro de
  autorização, usuário comum continua barrado
- **Lote de metadados** (`test_batch.py`): a auditoria registra valor anterior e novo
- **Erros internos** (`test_erros.py`): a exceção vai para o log, não para a resposta

O painel de analytics só tem teste do caminho de erro.

Em `backend/scripts/` ficam dois diagnósticos manuais (imports/rotas e JWT), que
o pytest não coleta — veja [`backend/scripts/README.md`](backend/scripts/README.md).

## Endpoints principais

```http
POST /api/auth/login            # Login com email/senha
POST /api/auth/refresh          # Renovar token (usa o refresh_token)
GET  /api/auth/me               # Dados do usuário atual
POST /api/auth/logout
POST /api/auth/change-password
GET  /api/auth/users            # Listar usuários (admin)
POST /api/auth/users            # Criar usuário (admin)

POST /api/documents/upload      # Upload de PDFs
GET  /api/documents             # Listar documentos
GET  /api/documents/{id}        # Detalhes do documento
POST /api/documents/{id}/metadata
GET  /api/documents/{id}/download
DELETE /api/documents/{id}

GET  /api/analytics/dashboard/summary
```

## Segurança

- Não versione o arquivo `.env`, bancos de dados, certificados, chaves privadas
  ou documentos reais — todos já estão cobertos pelo `.gitignore`.
- Rotacione as credenciais caso suspeite de exposição.

## Licença

MIT.
