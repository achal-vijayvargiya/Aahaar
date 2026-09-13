# AGENTS.md

## Cursor Cloud specific instructions

### What runs here
Only the **backend** (`backend/`) is a real, runnable product: a FastAPI + PostgreSQL API
("DrAssistent"/Aahaar). The `aahaar-wellness-hub` and `aahaar-mobile` directories are empty
placeholders (described in docs but no source committed), so there is no web/mobile app to run.

### Services
- **PostgreSQL 16** (system package, installed during environment setup) — DB `drassistent`,
  user/password `postgres`/`postgres`, port 5432. Start it with:
  `sudo pg_ctlcluster 16 main start` (it does not auto-start; `pg_isready` to check).
  Create the DB if missing: `sudo -u postgres psql -c "CREATE DATABASE drassistent;"`
- **FastAPI backend** on port 8000. Run in dev from `backend/`:
  `./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
  Swagger UI at `/docs`, health at `/health`. Routes are under `/api/v1/platform/...`.

### Python env
Dependencies live in a venv at `backend/venv` (created by the update script). Always invoke tools
via `./venv/bin/...` (e.g. `./venv/bin/pytest`, `./venv/bin/uvicorn`) from `backend/`.
`backend/.env` (gitignored) holds `DATABASE_URL` and other settings; defaults in `app/config.py`
already point at the local Postgres, so the app also runs without `.env`.

### Database schema — do NOT rely on Alembic
The legacy Alembic migration chain (`backend/alembic/versions/*`) is broken for a fresh DB
(early migrations reference a `clients` table that no migration creates). The current platform
app instead creates all tables from the ORM models via `init_db()` (`Base.metadata.create_all`),
which runs automatically on app startup. For tests, the fixtures also use `create_all`. Just start
the app (or import `app.main` and call `app.database.init_db()`) against an empty `drassistent` DB.

### Tests
From `backend/`, point tests at PostgreSQL and run only the platform suite (the current
architecture):
`TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/drassistent ./venv/bin/pytest tests/platform`
- The platform API, data-repository, auth and monitoring tests pass.
- Some `tests/platform/engines/*` and a few assessment/plan tests fail due to **pre-existing**
  mismatches between engine return shapes / unseeded KB data and the test expectations
  (e.g. `KeyError: 'bmr'`). These are not environment problems.
- The legacy `tests/test_auth.py` / `tests/test_main.py` target removed legacy code
  (`app.models`, `app.routers` → nonexistent `app.legacy.models`/`routers`) and cannot be
  collected; run `tests/platform` explicitly rather than the whole `tests/` dir.

### Auth / seeding for manual testing
There is no self-serve register endpoint. Seed a user directly, then log in via
`POST /api/v1/platform/auth/login` (form-encoded `username`/`password`) to get a JWT:
```
./venv/bin/python -c "
from app.database import SessionLocal; import app.main
from app.platform.data.repositories.platform_user_repository import PlatformUserRepository
from app.platform.utils.security import get_password_hash
db=SessionLocal(); r=PlatformUserRepository(db)
r.get_by_username('admin') or r.create({'username':'admin','email':'admin@drassistent.com','hashed_password':get_password_hash('admin123'),'role':'admin','is_active':True,'is_superuser':True})
db.close()"
```

### Gotchas
- Platform API routes require a **trailing slash** (e.g. `POST /api/v1/platform/clients/`).
  Without it FastAPI returns a 307 redirect that `curl` won't follow by default.
- `passlib` 1.7.4 logs a harmless `module 'bcrypt' has no attribute '__about__'` warning with
  bcrypt 4.x; password hashing/verification still works.
- `httpx` is pinned to `0.27.2` (the update script does this): the pinned `starlette` 0.35.1
  `TestClient` passes `app=` to `httpx.Client`, which httpx >= 0.28 removed.
