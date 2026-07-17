# PDF Document Manager

Sistema web para gerenciamento de documentos PDF com autenticação JWT,
adição de metadados, painel de analytics e integração opcional de assinatura
digital (DocuSign).

## Funcionalidades

- Autenticação JWT com controle de papéis (Admin / User / Viewer)
- Upload de PDFs com validação
- Gestão de metadados do documento
- Dashboard com métricas e gráficos
- Registro de auditoria das ações
- Integração opcional com DocuSign para assinatura

## Arquitetura

```
.
├── backend/
│   ├── app/
│   │   ├── auth/        # Autenticação JWT
│   │   ├── routes/      # Endpoints da API
│   │   ├── services/    # Regras de negócio (PDF, metadados, lote)
│   │   ├── utils/       # Validadores e helpers
│   │   ├── models.py    # Modelos do banco
│   │   ├── config.py    # Configuração via variáveis de ambiente
│   │   └── __init__.py  # Application factory
│   ├── tests/           # Testes automatizados (pytest)
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

```bash
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
| `SECRET_KEY` / `JWT_SECRET_KEY` | Chaves de sessão e JWT |
| `DATABASE_URL` | URL do banco (SQLite por padrão) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Admin criado no primeiro start |
| `COMPANY_NAME` / `DEFAULT_LOCATION` | Rótulos exibidos na aplicação |
| `DOCUSIGN_*` | Credenciais DocuSign (opcional) |

O primeiro administrador é criado automaticamente a partir de `ADMIN_EMAIL` e
`ADMIN_PASSWORD`. Defina uma senha forte antes de subir a aplicação.

## Execução

```bash
cd backend
python run.py
```

A API sobe em `http://localhost:5000`. Abra `frontend/index.html` no navegador
(ou sirva a pasta `frontend/` com um servidor estático) para usar a interface.

## Testes

```bash
cd backend
pytest tests/ -v
```

Cobertura dos testes:

- Autenticação e autorização
- Fluxos de documentos e metadados
- Validações de entrada
- Controle de papéis

## Endpoints principais

```http
POST /api/auth/login            # Login com email/senha
POST /api/auth/refresh          # Renovar token
GET  /api/auth/profile          # Dados do usuário atual

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
