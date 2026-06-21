# HelpDesk Lite

Sistema acadêmico de **helpdesk** construído em **Flask**, para controle de
usuários, tickets (chamados) e atualizações de tickets. Esta é a **versão
final, única e consolidada** do projeto: usa ORM + migrations, autenticação
por sessão, validação server-side e uma suíte de testes automatizados.

> Os materiais didáticos anteriores (SQL manual sem `password_hash`, conceitos
> de JWT, pacotes `microtask`/`app`, etc.) foram usados **apenas como
> referência de aprendizado**. Eles **não fazem parte** desta implementação:
> aqui não há JWT, não há SQL manual como camada principal e não há pacotes
> legados — apenas o pacote final `helpdesk`.

---

## 1. Stack

| Camada                 | Tecnologia                                    |
| ---------------------- | --------------------------------------------- |
| Linguagem              | Python 3.11+                                   |
| Web framework          | Flask (app factory + blueprints)               |
| ORM                    | Flask-SQLAlchemy                               |
| Migrations             | Flask-Migrate (Alembic)                        |
| Driver MySQL           | PyMySQL (+ `cryptography` p/ auth sha2)        |
| Config                 | python-dotenv (Twelve-Factor)                  |
| Validação              | Marshmallow                                    |
| Hash de senha          | Werkzeug (`generate_password_hash`/`check_…`)  |
| Testes                 | pytest, pytest-cov, pytest-flask               |

**Autenticação:** por **sessão** (web tradicional com templates Jinja).
JWT **não** é usado nesta versão final — apenas serviu de referência
conceitual sobre autenticação e autorização.

---

## 2. Estrutura de pastas

```text
helpdesk_lite/
├── run.py                  # ponto de entrada (python run.py / flask --app run.py ...)
├── requirements.txt
├── .env.example
├── .gitignore
├── pyproject.toml          # layout src/, instalável com pip install -e .
├── pytest.ini
├── README.md
├── migrations/             # Flask-Migrate (Alembic)
└── src/
    └── helpdesk/
        ├── __init__.py     # create_app() — app factory
        ├── config.py       # Config / TestConfig (Twelve-Factor)
        ├── extensions.py   # db, migrate
        ├── models.py       # User, Ticket, TicketUpdate
        ├── schemas.py      # validação Marshmallow (anti mass assignment)
        ├── decorators.py   # login_required, agent_required
        ├── cli.py          # comandos `flask seed` e `flask create-agent`
        ├── blueprints/     # pages, auth, users, tickets
        └── templates/      # Jinja (base, auth, users, tickets, errors)
└── tests/                  # pytest (SQLite em memória)
```

---

## 3. Configuração do ambiente

Requisitos: Python 3.11+ e (para produção) um MySQL com o banco
`helpdesk_lite_db`.

```bash
# 1) Ambiente virtual
python -m venv venv_desenvolvimento
source venv_desenvolvimento/bin/activate        # Windows: venv_desenvolvimento\Scripts\activate

# 2) Dependências
pip install -r requirements.txt
```

### Criação do `.env`

Copie o exemplo e ajuste os valores (o `.env` real **nunca** é versionado):

```bash
cp .env.example .env
```

`.env.example`:

```env
FLASK_DEBUG=1
SECRET_KEY=change-this-dev-secret-key-with-at-least-32-chars
DATABASE_URL=mysql+pymysql://root:senha@localhost:3306/helpdesk_lite_db
SQLALCHEMY_TRACK_MODIFICATIONS=False
TICKETS_PER_PAGE=10
```

> `SECRET_KEY` é obrigatório e deve ter **pelo menos 32 caracteres**;
> `DATABASE_URL` é obrigatório. A aplicação falha rápido (`RuntimeError`) se
> faltarem — comportamento intencional do `config._require`.

---

## 4. Migrations

```bash
export FLASK_APP=run.py        # Windows: set FLASK_APP=run.py

flask db upgrade               # aplica as migrations já versionadas
```

Para evoluir o schema após alterar os models:

```bash
flask db migrate -m "descrição da mudança"
flask db upgrade
```

> O banco já vem com a migration inicial (`users`, `tickets`,
> `ticket_updates`). Bancos SQLite reais **não** são versionados.

---

## 5. Seed (dados de exemplo)

```bash
flask seed
```

Cria, de forma **idempotente**, usuários, tickets e atualizações de exemplo.
As senhas são sempre armazenadas como **hash** (nunca em texto puro).

---

## 6. Execução

```bash
# Modo desenvolvimento (sem instalar o pacote)
python run.py
# ou
flask --app run.py run --debug
```

Acesse http://127.0.0.1:5000.

Alternativamente, instale o pacote em modo editável e use o nome do pacote:

```bash
pip install -e .
flask --app helpdesk run
```

---

## 7. Testes

```bash
pytest -v
```

Os testes usam **SQLite em memória** (não tocam no banco real) e cobrem:
smoke, autenticação, autorização (customer/agent), CRUD de usuários e
tickets, validação e regressões de segurança (mass assignment).

---

## 8. Usuários de exemplo

Criados por `flask seed` (senha de desenvolvimento: **`Senha@123`**):

| E-mail                     | Perfil    |
| -------------------------- | --------- |
| `agente@helpdesk.local`    | agent     |
| `cliente1@helpdesk.local`  | customer  |
| `cliente2@helpdesk.local`  | customer  |

---

## 9. Modelo de dados

- **users**: `id`, `name`, `email` (único), `password_hash`, `role`
  (`customer`/`agent`), `created_at`.
- **tickets**: `id`, `customer_id` → users, `agent_id` → users (nullable),
  `title`, `description`, `status` (`open`/`in_progress`/`resolved`/`closed`),
  `priority` (`low`/`medium`/`high`), `created_at`, `updated_at`.
- **ticket_updates**: `id`, `ticket_id` → tickets, `author_id` → users,
  `message`, `created_at`.

`role`, `status` e `priority` são protegidos por `CheckConstraint` no banco.

---

## 10. Rotas

| Método      | Rota                          | Acesso              |
| ----------- | ----------------------------- | ------------------- |
| GET         | `/`                           | público / logado    |
| GET         | `/account`                    | logado              |
| GET/POST    | `/auth/login`                 | público (rate-limit)|
| GET/POST    | `/auth/logout`                | logado              |
| GET/POST    | `/auth/password`              | logado              |
| GET         | `/users/`                     | **agente**          |
| GET/POST    | `/users/create`               | **agente**          |
| GET         | `/tickets/` (filtros: `status`, `priority`, `assignment`, `q`) | logado |
| GET/POST    | `/tickets/create`             | logado              |
| GET         | `/tickets/<id>`               | dono ou agente      |
| POST        | `/tickets/<id>/update`        | dono ou agente      |
| POST        | `/tickets/<id>/edit`          | **agente**          |
| POST        | `/tickets/<id>/assign`        | **agente** (assume) |
| POST        | `/tickets/<id>/close`         | dono ou agente      |
| POST        | `/tickets/<id>/reopen`        | dono ou agente      |

---

## 11. Segurança implementada

- **Hash de senha** com Werkzeug; senha em texto puro nunca é persistida.
- **Login genérico**: falha de login não revela se o e-mail existe.
- **Sessão**: apenas `user_id` é guardado; `g.user` é carregado por requisição.
- **Proteção de rotas** via `login_required` / `agent_required`.
- **CSRF**: todos os formulários POST exigem token (Flask-WTF / `CSRFProtect`).
- **Rate limiting** no `POST /auth/login` (Flask-Limiter; `LOGIN_RATE_LIMIT`),
  retornando `429` ao exceder — mitiga força bruta.
- **Cabeçalhos de segurança** em toda resposta: `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy` e `Content-Security-Policy`.
- **Anti mass assignment**: schemas Marshmallow com whitelist e
  `unknown = EXCLUDE`. As rotas **nunca** fazem `Model(**request.form)`;
  campos sensíveis (`role`, `id`, `customer_id`, `status`, `password_hash`,
  `is_admin`, …) são ignorados e definidos explicitamente pelo servidor.
- **Autorização customer × agent**:
  - cliente vê/edita só os próprios tickets e cria chamados apenas para si;
  - cliente nunca escolhe `customer_id`, vira `agent` ou atribui agentes;
  - agente vê todos os tickets e altera `status`, `priority` e `agent_id`;
  - `agent_id` só pode apontar para um usuário com role `agent`.

---

## 12. Deploy com Docker

Sobe a aplicação **+ MySQL** com um comando (aplica migrations e popula o
seed automaticamente no primeiro start):

```bash
docker compose up --build
```

Acesse http://localhost:8000 (usuários de exemplo na seção 8).

- `Dockerfile`: imagem Python 3.11-slim servindo via **gunicorn**
  (`helpdesk:create_app()`).
- `docker-entrypoint.sh`: aguarda o banco, roda `flask db upgrade` e
  (se `SEED_ON_START=1`) `flask seed` antes de iniciar o servidor.
- `docker-compose.yml`: serviços `web` e `db` (MySQL 8) com healthcheck.

---

## 13. Qualidade de código

```bash
pip install -e ".[dev]"   # ruff, black, pre-commit
ruff check src tests run.py
black --check src tests run.py
pre-commit install        # roda os linters automaticamente em cada commit
```

A CI (GitHub Actions) tem dois jobs: **lint** (ruff + black) e **test**
(pytest com gate `--cov-fail-under=80`).

---

## 14. Dependências extra (justificativa)

- **cryptography**: exigida pelo PyMySQL para autenticar em MySQL 8 com
  `caching_sha2_password`.
- **Flask-WTF**: proteção CSRF dos formulários.
- **Flask-Limiter**: rate limiting do login.
- **gunicorn**: servidor WSGI de produção (usado no Docker).

---

## 13. Observação sobre os materiais antigos

Os documentos-fonte (preparação de ambiente, SQL manual, evolução para ORM,
exercícios de bcrypt/argon2, conceitos de JWT, etc.) foram utilizados
**somente como referência** para consolidar esta versão final. Nenhum código
legado, pacote `microtask`/`app`, SQL manual de produção ou autenticação JWT
faz parte da entrega.
