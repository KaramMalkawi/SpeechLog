# Mixed Miles Backend

## Setup

```bash
cp .env.local.example .env
```

## Run (Docker)

```bash
docker compose up --build
```

First time (and after new migrations):

```bash
docker compose exec web python manage.py migrate
```

API: http://localhost:8000  
Health: http://localhost:8000/api/v1/health/  
Docs: http://localhost:8000/api/v1/docs/  
Verify test (local): http://localhost:8000/api/v1/accounts/verify-test/

## Run (host, no Docker)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements/dev.txt
.venv/bin/python manage.py migrate
.venv/bin/uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload
```

## Tests

```bash
.venv/bin/pytest
```

## Env

`DJANGO_ENV` in `.env`: `local` | `dev` | `prod`
