# TEAM-201 Backend

Backend for the Student Ranking System. The project uses FastAPI, SQLAlchemy 2.x async ORM, PostgreSQL with `asyncpg`, Pydantic v2 settings, and Alembic migrations.

## Current Status

The base backend structure is ready for team development:

- FastAPI application entrypoint is configured.
- PostgreSQL connection settings are loaded from `.env`.
- SQLAlchemy models are split by domain under `app/models`.
- Alembic is initialized and connected to model metadata.
- Initial database migration exists and was generated from the current models.
- Smoke tests verify the app import, root endpoint, and model mapper registration.

Not implemented yet:

- API route handlers in `app/routers/*`.
- Business logic in `app/services/*`.
- Domain-specific request/response schemas inside `app/schemas/*`.
- Authentication endpoints and token creation flow.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x async ORM
- PostgreSQL
- asyncpg
- Alembic
- Pydantic Settings
- Pytest

## Project Structure

```text
app/
  main.py                 FastAPI app, middleware, API router registration
  core/
    config.py             Environment-based settings
    security.py           JWT decode helper used by RBAC middleware
    middleware/rbac.py    Role-based access middleware
  db/
    database.py           Async SQLAlchemy engine/session/get_db
    base.py               Imports all models and exposes Base.metadata
  models/                 SQLAlchemy models and enums
  routers/                FastAPI routers, currently placeholders
  schemas/                Pydantic schema package, currently placeholders
  services/               Business logic layer, currently placeholders
  utils/                  Shared helpers
alembic/
  env.py                  Alembic async migration environment
  versions/               Migration files
tests/
  test_main.py            Smoke tests
```

## Local Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create local environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` for your local PostgreSQL credentials:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=edumetrik
DB_USER=postgres
DB_PASSWORD=your-local-password

SECRET_KEY=change-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Do not commit `.env`.

## Database Setup

Create the PostgreSQL database if it does not exist:

```powershell
psql -U postgres -c "CREATE DATABASE edumetrik;"
```

If your database name is different, update `DB_NAME` in `.env`.

Apply migrations:

```powershell
alembic upgrade head
```

Seed demo data:

```powershell
python scripts/seed_demo_data.py
```

The seed script is idempotent. It removes only previous demo data with emails ending in `@demo.local` and academic year `2025-2026 Demo`, then inserts fresh demo records across all current database tables.

Default demo password for all demo users:

```text
DemoPass123!
```

Useful demo users:

```text
demo.superadmin@demo.local
demo.admin@demo.local
demo.tutor1@demo.local
demo.parent1@demo.local
demo.student1@demo.local
```

Check current migration:

```powershell
alembic current
```

Expected current revision:

```text
255ae92f2343 (head)
```

Check whether models and DB schema are synchronized:

```powershell
alembic check
```

Expected result:

```text
No new upgrade operations detected.
```

## Alembic Workflow

Alembic is already initialized in `alembic/`. Do not run this again:

```powershell
alembic init alembic
```

When changing SQLAlchemy models:

```powershell
alembic revision --autogenerate -m "short description"
```

Review the generated file under `alembic/versions/`. Do not commit an empty migration unless it is intentional.

Apply it:

```powershell
alembic upgrade head
```

Verify:

```powershell
alembic check
```

## Run The API

Start the development server:

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

The root endpoint should return:

```json
{"message": "API is running"}
```

## Tests

Run tests:

```powershell
pytest -q
```

If Windows blocks `.pytest_cache`, use:

```powershell
pytest -q -p no:cacheprovider
```

Current expected result:

```text
2 passed
```

## Development Rules

Use `app/models` as the single source of truth for SQLAlchemy models. The root `models.py` only re-exports `app.models` for compatibility.

Add API endpoints in `app/routers/<domain>.py`, then register them in `app/routers/__init__.py`.

Keep business logic in `app/services/*`; routers should stay thin.

Keep DB access through `app/db/database.py` using `get_db` or `AsyncSessionLocal`.

Use schemas for request and response validation. The current `app/schemas/*` files are placeholders; fill them per domain as endpoints are implemented.

Before pushing backend changes, run:

```powershell
pytest -q -p no:cacheprovider
alembic check
```

## Suggested Task Split

- Auth developer: implement login/register/token creation in `app/routers/auth.py`, `app/core/security.py`, and user schemas.
- Users/students developer: implement CRUD endpoints for users, students, parents, tutors, groups, academic years, and semesters.
- Scores/ranking developer: implement score update services, penalty services, ranking calculation, and related endpoints.
- Migration owner: review every generated Alembic revision before merge.

## Publish Checklist

Before pushing to GitHub:

- Keep `.env` uncommitted.
- Commit `.env.example`.
- Do not commit `.venv`, `.idea`, `.pytest_cache`, or `__pycache__`.
- Avoid committing unrelated large files unless they are required project assets.
- Run tests and Alembic check.
