# School Diary (FastAPI)

[![CI](https://github.com/VitaliyLobko/diary/actions/workflows/ci.yml/badge.svg)](https://github.com/VitaliyLobko/diary/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A small school-diary web application: it manages students, teachers, groups,
disciplines and grades, with server-rendered pages (Jinja2 + Bootstrap) on top
of a JSON API. Built as a portfolio project to demonstrate a clean FastAPI
architecture — routers, a repository layer, Pydantic schemas, JWT auth,
role-based access control and Redis caching.

## Features

- REST API with full CRUD for every entity (students, teachers, groups,
  disciplines, grades).
- Server-rendered pages with Jinja2 templates and Bootstrap.
- OAuth2 / JWT authentication with refresh tokens and email confirmation.
- Role-based access control (`admin` / `moderator` / `user`).
- Per-IP rate limiting on the authentication endpoints (slowapi).
- Redis caching for user and student lookups.
- Aggregated queries (average grade, top-10 students).
- Fake data generator for quick local seeding (Faker).
- Alembic database migrations.
- Unit and integration tests with Pytest.

## Tech stack

FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL · Redis · Pydantic v2 ·
Jinja2 · Bootstrap · Docker · GitHub Actions

## Project structure

```
main.py                 # FastAPI app: middleware, routers, static, entrypoint
src/
  conf/                 # Pydantic settings (env-driven configuration)
  database/             # SQLAlchemy engine, session and ORM models
  schemas/              # Pydantic request/response models
  repository/           # Data-access layer (DB queries)
  routes/               # API routers and page handlers
  services/             # Auth, roles, email, Redis cache
migrations/             # Alembic migrations
templates/              # Jinja2 templates
static/                 # CSS, JS, images
tests/                  # Pytest suite
```

## Getting started

### Option 1 — Docker (recommended)

```bash
cp .env.example .env          # optional: adjust secrets
docker compose up --build
```

The API and pages are served at http://localhost:8000, PostgreSQL and Redis
start automatically, and database migrations are applied on startup.

### Option 2 — Local

Requires Python 3.12 and a running PostgreSQL. The easiest way to get the
database (and Redis) is to start just those services from the compose file.

```bash
docker compose up -d db redis   # PostgreSQL + Redis only

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env           # optional — the defaults already point at the compose db
alembic upgrade head           # apply migrations
uvicorn main:app --reload
```

On Windows, uvicorn's `--reload` may fail to restart its worker cleanly (the
old process keeps serving stale code). Use the bundled runner instead, which
reloads by restarting the whole process:

```bash
python dev.py
```

### Configuration

All settings are read from environment variables (or a local `.env`) and have
safe development defaults — see [.env.example](.env.example). Key variables:

| Variable       | Description                        | Default (dev)                |
|----------------|------------------------------------|------------------------------|
| `DATABASE_URL` | SQLAlchemy database URL (Postgres) | `postgresql://…/sdiary`      |
| `SECRET_KEY`   | JWT signing key (**set in prod**)  | `dev-secret-change-me`       |
| `REDIS_HOST`   | Redis host                         | `localhost`                  |
| `MAIL_*`       | SMTP settings for confirmation mail| placeholders                 |

## API documentation

Interactive OpenAPI docs are available once the app is running:

- Swagger UI — http://localhost:8000/docs
- ReDoc — http://localhost:8000/redoc

To populate the database with demo data, sign in as an admin and use the
"Insert fake data" button (or call `POST /seed/`). It is idempotent — a no-op
if data already exists — unless you pass `?reset=true` to wipe and reseed.

### Example requests

```bash
# 1. Register (returns 201; a confirmation link is emailed / logged in dev)
curl -X POST http://localhost:8000/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"teacher@example.com","email":"teacher@example.com","password":"secret123"}'

# 2. Log in once the email is confirmed (OAuth2 password form → JWT)
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -d "username=teacher@example.com&password=secret123" | jq -r .access_token)

# 3. Create a student via the JSON API (admin/moderator only — send the token)
curl -X POST http://localhost:8000/api/v1/students/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Ada","last_name":"Byron","dob":"2010-12-10","group_id":1}'

# 4. Read data as JSON (the /api/v1 surface is what the mobile app consumes)
curl http://localhost:8000/api/v1/students/avg_grade

# The same data as a server-rendered HTML page lives at the un-prefixed path:
#   http://localhost:8000/students/avg_grade
```

## Running tests

The suite runs against a real PostgreSQL that is started automatically in a
throwaway container (via [testcontainers]), so **Docker must be running** — no
manual database setup is needed.

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

[testcontainers]: https://testcontainers.com/

## Screenshots

![Home](static/img/home.png)
![Students](static/img/img_6.png)
![Grades](static/img/img_5.png)
![Student](static/img/img_7.png)

## Known limitations

Conscious trade-offs for a portfolio-sized project, and the natural next steps:

- **Open CORS** (`allow_origins=["*"]`, credentials disabled) to keep the demo
  easy to call; lock this down to known origins in production.
- **Rate-limit storage is in-memory** (per process). Fine for a single
  instance; point slowapi at Redis for a multi-instance deployment.
- **Cookie security is environment-driven.** Set `APP_ENV=production`,
  `COOKIE_SECURE=true` and a strong `SECRET_KEY`, and serve over HTTPS — the
  app refuses to start with the placeholder secret in production.
- **Email delivery needs SMTP.** In development no server is configured, so the
  confirmation link is written to the logs instead of being sent.
- **Caching assumes a single Redis** shared by all app instances; invalidation
  is best-effort on writes.

## License

Released under the [MIT License](LICENSE).

## Author

Developed by **Vitaliy Lobko** — [Telegram](https://t.me/MrLakin)
