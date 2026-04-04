# FastAPI MVC Framework

A **starter backend** for new API projects. It organizes code in a classic **Model–View–Controller** style on top of [FastAPI](https://fastapi.tiangolo.com/): HTTP routes live in **routers**, business logic in **controllers**, persistence in **models** (SQLAlchemy) and **schemas** (Pydantic request/response shapes). It ships with **JWT authentication**, **MySQL** via SQLAlchemy, **optional rate limiting** (SlowAPI), and a **pluggable AI chat layer** (OpenAI or a local OpenAI-compatible server such as Ollama).

Use this repository as a **template or clone**: rename the project in configuration, extend routers and controllers, add models, and deploy.

---

## Table of contents

1. [What you get](#what-you-get)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Database setup](#database-setup)
7. [Create the first user and get a token](#create-the-first-user-and-get-a-token)
8. [Run the application](#run-the-application)
9. [API overview](#api-overview)
10. [Extending the framework](#extending-the-framework)
11. [Operational notes](#operational-notes)

---

## What you get

| Area | Details |
|------|---------|
| **HTTP API** | FastAPI with automatic OpenAPI docs (`/docs`, `/redoc`) |
| **MVC layout** | Routers → Controllers → Models; Pydantic schemas for I/O validation |
| **Persistence** | SQLAlchemy 2.x + PyMySQL, session-per-request via `get_db()` |
| **Auth** | Bearer JWT (`python-jose`), bcrypt password hashing |
| **Users** | CRUD-style user API (protected routes require a valid JWT) |
| **Rate limiting** | SlowAPI, configurable per method and global default (in-memory per process) |
| **AI** | Factory-selected service: OpenAI Chat Completions or local HTTP API |
| **Settings** | `pydantic-settings` loading from `.env` in the `src` directory |

---

## Architecture

### Request flow

1. **Router** (`routers/`) — Defines URL paths, HTTP methods, dependencies (`Depends`), Pydantic body/query models, and rate-limit decorators.
2. **Controller** (`controllers/`) — Application logic: queries, transactions, orchestration. Receives a DB session (or other deps) from the router layer.
3. **Model** (`models/`) — SQLAlchemy ORM classes mapped to tables.
4. **Schema** (`schemas/`) — Pydantic models for request bodies and response serialization (decoupled from ORM where appropriate).

Supporting pieces:

- **`config/settings.py`** — Central `Settings` object (env-backed).
- **`database/mysql_session.py`** — Engine, `SessionLocal`, and `get_db()` dependency.
- **`middleware/`** — JWT user resolution (`get_current_user`, `get_optional_current_user`), rate limit helpers.
- **`utils/`** — JWT helpers, password hashing, shared error utilities.
- **`services/`** — AI chat abstraction (`AIChatService`), OpenAI and local implementations, plus `factory.create_ai_chat_service()`.
- **`prompts/`** — Text prompts used by AI features (e.g. connectivity test).

### Directory map (under `src/`)

```
src/
├── main.py                 # FastAPI app, rate-limit exception handler, router includes
├── requirements.txt
├── .env                    # Your secrets (not committed) — copy from .env.example
├── config/
│   └── settings.py         # Pydantic settings
├── routers/                # APIRouter modules (auth, users, ai, base)
├── controllers/            # Business logic per domain
├── models/                 # SQLAlchemy models
├── schemas/                # Pydantic I/O models
├── database/               # Engine + session factory
├── middleware/             # Auth + rate limiting
├── services/               # AI and other integrations
├── utils/
├── prompts/
└── enums/                  # Response messages / enums
```

---

## Prerequisites

- **Python** 3.10 or newer (recommended; match your deployment target).
- **MySQL** 5.7+ or 8.x (or compatible) with a database and user the app can use.
- **Git** (to clone the repository).

Optional, depending on features you enable:

- **OpenAI API key** — if `AI_PROVIDER=openai`.
- **Local LLM server** — e.g. [Ollama](https://ollama.com/) if `AI_PROVIDER=local`.

---

## Installation

### 1. Clone the repository

```bash
git clone <your-fork-or-remote-url> fasiapi_mvc_framework
cd fasiapi_mvc_framework
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**

```powershell
cd src
python -m venv env
.\env\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
cd src
python3 -m venv env
source env/bin/activate
```

### 3. Install Python dependencies

With the virtual environment active and `src` as the current directory:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment file

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

**Important:** `config/settings.py` loads **`.env` from the current working directory** when you run the app. Always start Uvicorn from the `src` directory (see [Run the application](#run-the-application)), or set the same variables in the process environment.

Set at minimum:

- `PROJECT_NAME`, `APP_VERSION`, `API_PREFIX`
- `CORS_ORIGINS` (comma-separated; used by settings for future or custom CORS wiring)
- `MYSQL_*` and `MYSQL_DATABASE`
- `SECRET_KEY` (strong random string; JWT signing)
- `AI_PROVIDER` and either OpenAI or local AI variables as needed

Generate a strong `SECRET_KEY` (example):

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Configuration

All variables below are read from `src/.env` (or the environment). Names are **case-sensitive**.

| Variable | Purpose |
|----------|---------|
| `PROJECT_NAME` | Display name in health response |
| `APP_VERSION` | Version string in health response |
| `API_PREFIX` | Global prefix for included routers (e.g. `/api/v1`) |
| `CORS_ORIGINS` | Comma-separated origins; `settings.cors_origins_list` parses this for middleware you may add |
| `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` | MySQL connection |
| `AI_PROVIDER` | `openai` or `local` |
| `OPENAI_API_KEY`, `OPENAI_API_URL`, `OPENAI_MODEL` | OpenAI chat (model must be set when using OpenAI) |
| `LOCAL_MODEL_API_URL`, `LOCAL_MODEL_NAME`, `LOCAL_MODEL_API_KEY` | Local backend (e.g. Ollama) |
| `AI_TEMPERATURE`, `AI_MAX_TOKENS` | Shared defaults for chat calls |
| `RATE_LIMIT_ENABLED` | `true` / `false` |
| `RATE_LIMIT_GLOBAL`, `RATE_LIMIT_GET`, `RATE_LIMIT_POST`, `RATE_LIMIT_PUT`, `RATE_LIMIT_DELETE` | SlowAPI limit strings |
| `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT |

See `src/.env.example` for the full list and sensible defaults.

---

## Database setup

### 1. Create a MySQL database

```sql
CREATE DATABASE your_database_name CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Grant privileges to the user configured in `.env`.

### 2. Create the `users` table

The ORM model expects a table compatible with `models/user.py`. Example DDL:

```sql
CREATE TABLE users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  first_name VARCHAR(100) NULL,
  last_name VARCHAR(100) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

You can alternatively use SQLAlchemy’s `Base.metadata.create_all(engine)` from a one-off script if you add imports for all models; the repository does not ship a migration tool by default—add **Alembic** if you need versioned migrations.

---

## Create the first user and get a token

There is **no public registration endpoint** in the stock template: user creation is **JWT-protected** (`POST /users/`). For the first user, insert a row manually or run a short script.

### 1. Hash a password

From `src/` with the virtual environment active:

```bash
python -c "from utils.password import hash_password; print(hash_password('YourSecurePassword123'))"
```

Copy the printed hash.

### 2. Insert into MySQL

```sql
INSERT INTO users (username, email, password_hash, first_name, last_name, is_active)
VALUES (
  'admin',
  'admin@example.com',
  '<paste bcrypt hash here>',
  'Admin',
  'User',
  1
);
```

### 3. Log in

`POST` to `{API_PREFIX}/auth/login` with JSON body:

```json
{
  "email": "admin@example.com",
  "password": "YourSecurePassword123"
}
```

Response includes `access_token`. Use `Authorization: Bearer <access_token>` on protected routes.

---

## Run the application

From the **`src`** directory (so `.env` is found and imports like `from config.settings` resolve):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **Interactive docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative docs:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

Production: use a process manager (systemd, Docker, etc.) and run **without** `--reload`; tune `uvicorn` workers and put a reverse proxy (nginx, Caddy) in front as needed.

---

## API overview

Assume `API_PREFIX=/api/v1` (default in `.env.example`). All paths below are relative to the server root.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `{API_PREFIX}/` | No | Health check (project name, version) |
| POST | `{API_PREFIX}/auth/login` | No | Email/password → JWT |
| GET | `{API_PREFIX}/auth/me` | Bearer | Current user profile |
| GET | `{API_PREFIX}/auth/optional-me` | Optional Bearer | Profile or `null` |
| GET | `{API_PREFIX}/users/` | Bearer | Paginated user list (`skip`, `limit`) |
| GET | `{API_PREFIX}/users/me` | Bearer | Same as `/auth/me` (user resource) |
| GET | `{API_PREFIX}/users/{user_id}` | Bearer | User by ID |
| POST | `{API_PREFIX}/users/` | Bearer | Create user |
| PUT | `{API_PREFIX}/users/{user_id}` | Bearer | Update user |
| DELETE | `{API_PREFIX}/users/{user_id}` | Bearer | Delete user |
| POST | `{API_PREFIX}/ai/connectivity-test` | Bearer | Runs AI connectivity prompt against configured provider |

Errors use conventional HTTP status codes (401, 404, 409, 429, 503, etc.). Rate limiting returns **429** with a JSON body when `RATE_LIMIT_ENABLED=true`.

---

## Extending the framework

1. **New resource** — Add `models/`, `schemas/`, `controllers/`, then `routers/`; register the router in `main.py` with `prefix=settings.API_PREFIX` if it should sit under the same API prefix.
2. **Shared DB access** — Inject `Session` with `Depends(get_db)` and pass it into your controller factory (see `users.py`).
3. **Protected routes** — Use `Depends(get_current_user)` or `Depends(get_optional_current_user)` from `middleware/auth.py`.
4. **Rate limits** — Decorate routes with `@apply_rate_limit(settings.RATE_LIMIT_POST)` (or GET/PUT/DELETE as appropriate).
5. **CORS for browsers** — `settings.cors_origins_list` is ready; add Starlette’s `CORSMiddleware` to `main.py` when you serve a SPA or another origin.
6. **Migrations** — Add Alembic under `src/` and point it at `settings.database_url` for team-friendly schema evolution.

---

## Operational notes

- **Rate limiting** uses **in-memory** storage per process. Multiple workers or hosts each maintain separate counters; for a shared limit use Redis-backed storage (SlowAPI supports this pattern).
- **AI connectivity test** requires a valid JWT and a correctly configured `AI_PROVIDER`; failures may return **503** with detail from the upstream.
- **Security** — Keep `.env` out of version control, rotate `SECRET_KEY` if leaked, and use TLS in production.

---

## License

This template does not include a default license file. Add a `LICENSE` at the repository root when you publish your project.
