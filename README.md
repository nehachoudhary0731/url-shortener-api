# URL Shortener API

A production-ready URL shortener built with **FastAPI**, **PostgreSQL**, and **Redis**.

## Features

- Generate short codes (7-char, 62^7 = 3.5 trillion unique combinations)
- Custom aliases (`yourdomain.com/my-brand`)
- **Redis caching** — redirects served from cache; DB only queried on cache miss
- **Per-IP rate limiting** — sliding window counter in Redis
- **Click analytics** — device type, browser, OS, referrer stored per click
- Link expiry with configurable datetime
- JWT auth — users own and manage their links
- Anonymous shortening (no login required)
- Collision handling — retries on the rare code clash

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI |
| Database | PostgreSQL + SQLAlchemy ORM |
| Cache + Rate Limit | Redis |
| Auth | JWT (python-jose) + bcrypt |
| User-Agent Parsing | user-agents |

## Quick Start

### With Docker

```bash
cp .env.example .env
docker-compose up --build
```

API at `http://localhost:8000/api` | Docs at `http://localhost:8000/docs`

### Without Docker

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## API Endpoints

### Auth
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `api/auth/register` | — | Register |
| POST | `api/auth/login` | — | Login, get JWT |

### URLs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/shorten` | Optional | Shorten a URL |
| GET | `/{short_code}` | — | Redirect to original |
| GET | `/api/urls` | Required | List your URLs |
| PATCH | `/api/urls/{code}` | Required | Activate/deactivate/update expiry |
| DELETE | `/api/urls/{code}` | Required | Delete a URL |
| GET | `/api/urls/{code}/analytics` | Required | Click analytics |

## Example Usage

```bash
# Shorten anonymously
curl -X POST http://localhost:8000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://github.com"}'

# Response
{
  "short_code": "aB3kP9x",
  "short_url": "http://localhost:8000/aB3kP9x",
  "total_clicks": 0
}

# Shorten with custom alias (login required)
curl -X POST http://localhost:8000/api/shorten \
  -H "Authorization: Bearer <token>" \
  -d '{"original_url": "https://github.com", "custom_alias": "my-github"}'

# View analytics
curl http://localhost:8000/api/urls/my-github/analytics \
  -H "Authorization: Bearer <token>"
```

## Key Design Decisions

- **Redis caching**: Every redirect checks Redis first. Cache-hit takes ~1ms vs ~10ms DB query. Cache TTL = 1 hour; invalidated immediately on URL update/delete.
- **Collision handling**: `secrets.choice()` over 62-char alphabet gives 3.5 trillion combos. On collision (astronomically rare), retries up to 5 times.
- **Rate limiting**: Sliding window in Redis — `SETEX key 60 1` on first request, `INCR` on subsequent. Resets every 60 seconds.
- **Analytics non-blocking**: Click recording wrapped in try/except so a DB error never breaks a redirect.
