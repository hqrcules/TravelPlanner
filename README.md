# Travel Planner

Production-quality FastAPI backend for planning trips. Each project owns up to ten "places" verified against the [Art Institute of Chicago API](https://api.artic.edu/docs/) and tracked via a `visited` flag.

## Tech stack

- **FastAPI** + **uvicorn** — async REST API & OpenAPI docs.
- **SQLAlchemy 2.0** (async) + **Alembic** — typed ORM and migrations.
- **PostgreSQL** as primary store with **SQLite (aiosqlite)** fallback via `DATABASE_URL`.
- **Pydantic v2** + **pydantic-settings** — runtime validation and config.
- **httpx** + **tenacity** — async HTTP client with retry for ArtIC.
- **aiocache** + **Redis** — caches ArtIC responses (in-memory fallback if `REDIS_URL` empty).
- **structlog** — JSON logs with `request_id` context.
- **pytest** + **pytest-asyncio** + **respx** — tests.
- **Docker / docker-compose**, **GitHub Actions**, **pre-commit** (ruff, black, mypy).

## Architecture

```
┌──────────────┐   HTTP    ┌───────────────┐
│   Client     ├──────────▶│ FastAPI app   │
└──────────────┘           │  (routers)    │
                           └──────┬────────┘
                                  │ depends_on
                                  ▼
                           ┌───────────────┐
                           │   Services    │  ← business rules live here
                           │ project/place │
                           │   /artic      │
                           └──┬─────────┬──┘
              repositories    │         │   integrations
                              ▼         ▼
                       ┌─────────┐  ┌──────────────┐
                       │   DB    │  │ ArtIC client │──▶ api.artic.edu
                       │ (async) │  │ + Redis cache│
                       └─────────┘  └──────────────┘
```

Layered structure — `api → services → repositories → models`. Routers carry no business logic; services raise typed exceptions translated to HTTP codes by a global handler.

## Quick start

### Docker (recommended)

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api uv run alembic upgrade head   # runs automatically too
```

Service is available at <http://localhost:8000>, Swagger UI at <http://localhost:8000/docs>.

### Local (uv)

```bash
uv sync --all-extras
cp .env.example .env
# point DATABASE_URL at a Postgres or use sqlite+aiosqlite:///./travel_planner.db
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Environment variables

See `.env.example`. Highlights:

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy async URL (`postgresql+asyncpg://...` or `sqlite+aiosqlite:///...`). |
| `REDIS_URL` | Redis URL for caching. Leave empty for in-memory fallback. |
| `ARTIC_BASE_URL` | Override Art Institute API base URL (useful in tests). |
| `ARTIC_CACHE_TTL_SECONDS` | Cache TTL for artwork lookups. |
| `BASIC_AUTH_USER` / `BASIC_AUTH_PASS` | Credentials for HTTP Basic auth. |
| `CORS_ORIGINS` | Comma-separated origins (e.g. `*` or `https://app.example.com,https://admin.example.com`). |
| `LOG_LEVEL` | `DEBUG`/`INFO`/... |

## Migrations

```bash
uv run alembic upgrade head            # apply
uv run alembic revision --autogenerate -m "message"
uv run alembic downgrade -1
```

## Tests

```bash
uv run pytest --cov=app --cov-fail-under=70
```

Layout:
- `tests/unit` — repositories & services with in-memory SQLite and stubbed ArtIC.
- `tests/integration` — full ASGI flow via `httpx.AsyncClient` + `respx`.

Lint & types:

```bash
uv run ruff check .
uv run black --check .
uv run mypy app
```

## Sample requests

```bash
AUTH="admin:changeme"

# Create a project
curl -u $AUTH -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Chicago","start_date":"2026-06-01"}'

# Add a place (verifies via api.artic.edu/v1/artworks/27992)
curl -u $AUTH -X POST http://localhost:8000/api/v1/projects/<PROJECT_ID>/places \
  -H "Content-Type: application/json" \
  -d '{"external_id":"27992","notes":"Nighthawks"}'

# Mark visited
curl -u $AUTH -X PATCH http://localhost:8000/api/v1/projects/<PROJECT_ID>/places/<PLACE_ID> \
  -H "Content-Type: application/json" \
  -d '{"visited":true}'
```

OpenAPI: <http://localhost:8000/docs>. Postman collection: [`postman/TravelPlanner.postman_collection.json`](postman/TravelPlanner.postman_collection.json).

## Business rules

1. Max 10 places per project (`409 Conflict` once limit reached).
2. Cannot delete a project that still contains a visited place (`409`).
3. Every new place is verified against Art Institute of Chicago (`422` if missing, `502` on upstream failure).
4. `external_id` is unique per project (`409` on duplicate).
5. When all places are visited the project status flips to `completed`; reverting any to unvisited drops it back to `in_progress`.

## Future improvements (TODO)

- Soft delete & audit log for projects/places.
- Rate limiting for the public API.
- OAuth2/JWT authentication alongside Basic auth.
- Background task to refresh ArtIC metadata.
- OpenTelemetry tracing.
