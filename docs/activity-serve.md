# activity-serve

FastAPI HTTP server exposing ActivityPub-compliant endpoints. Handles authentication, user identity management, and routes requests to activity-bus and activity-store.

**Location:** `.` (this project)
**Python:** >=3.10

## Directory Structure

```
app/
├── __init__.py
├── main.py                  # FastAPI app factory, CORS, router includes
├── core/
│   ├── __init__.py
│   └── settings.py          # Pydantic BaseSettings (env vars, .env file)
├── api/
│   ├── __init__.py          # Central router, ActivityStreamResponse class
│   ├── health.py            # GET /healthz
│   ├── auth.py              # Token validation, User/UserMaybe dependencies
│   ├── admin.py             # GET /admin (HTML shell)
│   ├── user.py              # /u/{key}/inbox, /u/{key}/outbox (GET/POST)
│   └── query.py             # /u/{key}/{path} generic path resolver (incomplete)
├── middleware/
│   ├── __init__.py
│   ├── logging.py           # LoggingMiddleware (structlog, currently disabled)
│   ├── normalize.py         # NormalizeMiddleware (ID normalization, currently disabled)
│   └── firebase_auth.py     # Deprecated session/cookie auth (unused)
├── services/
│   ├── __init__.py
│   ├── firebase.py          # Firebase Admin SDK integration
│   ├── user.py              # Identity/Person creation, get_or_create_user
│   ├── store.py             # Empty
│   └── bootstrap.py         # System initialization (disabled)
└── models/
    └── __init__.py           # Pydantic models: Person, Identity, Collection, OrderedCollection

tests/
├── __init__.py
├── helpers.py               # assert_response utility
├── test_health.py
├── test_authorization.py
├── test_admin.py
├── test_inbox.py
└── test_outbox.py

conftest.py                   # Test fixtures: app, client, test_auth, storage
run.py                        # Dev entry point (uvicorn with reload)
Dockerfile                    # Docker build
ui/
└── index.ts                  # Placeholder frontend entry
```

## Module Dependencies

```
app/main.py
├── fastapi (FastAPI, CORSMiddleware)
├── app.core.settings (Settings)
├── app.api (router)
├── app.middleware.logging (LoggingMiddleware)     # commented out
└── app.middleware.normalize (NormalizeMiddleware)  # commented out

app/api/__init__.py
├── app.api.health (router)
├── app.api.admin (router)
├── app.api.user (router)
└── app.api.query (router)

app/api/auth.py
├── app.services.firebase (verify_id_token)
└── app.services.user (get_or_create_user)

app/api/user.py
├── nanoid
├── activity_store (ActivityStore)
├── activity_store.utils (first_id)
├── activity_bus (ActivityBus)
└── app.api.auth (User, UserMaybe)

app/api/query.py
├── nanoid
├── activity_store (ActivityStore, utils)
├── activity_bus (ActivityBus)
└── app.api.auth (User, UserMaybe)

app/services/firebase.py
└── firebase_admin (initialize_app, auth)

app/services/user.py
├── nanoid
├── hashlib (blake2s)
└── activity_store (ActivityStore)
```

## External Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi[standard]` | Web framework + uvicorn |
| `pydantic` / `pydantic-settings` | Models and configuration |
| `activity-store[es,redis]` | Object storage (git dependency) |
| `activity-bus` | Activity processing (git dependency) |
| `firebase-admin` | Firebase Auth token verification |
| `python-jose` | JWT handling |
| `nanoid` | Short unique ID generation |
| `structlog` | Structured logging |
| `python-multipart` | Form data parsing |

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/healthz` | No | Health check |
| GET | `/admin` | Yes | Admin UI shell |
| GET | `/me` | Yes | Current user's Person object |
| GET | `/u/{key}/inbox` | Yes | User inbox (OrderedCollection) |
| GET | `/u/{key}/outbox` | Yes | User outbox with pagination (sort, after) |
| POST | `/u/{key}/outbox` | Yes | Submit activity |
| GET | `/u/{key}/{path}` | Optional | Generic path resolver (incomplete) |

## Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `ACTIVITY_SERVE_BASE_URL` | — | Base URL override |
| `SESSION_COOKIE` | `session` | Cookie name |
| `SESSION_MAX_AGE` | `2592000` | Cookie max age (30 days) |
| `SESSION_COOKIE_SECURE` | `true` | Secure cookie flag |
| `SESSION_COOKIE_HTTPONLY` | `true` | HttpOnly flag |
| `SESSION_COOKIE_SAMESITE` | `lax` | SameSite policy |
| `GOOGLE_CLIENT_ID` | — | Google OAuth client ID |
| `ALLOW_ORIGINS` | `["*"]` | CORS allowed origins |

Plus all `activity-store` env vars for backend/cache configuration.

## Entry Points

| Command | Purpose |
|---------|---------|
| `python run.py` | Dev server (uvicorn with reload) |
| `uvicorn app.main:app` | Production ASGI server |
| `pytest` | Test suite |
| `docker build .` | Container build |

## Known Issues

- `app/api/query.py` has incomplete code (line 49 cut off, undefined `store` variable)
- `app/services/user.py` line 110: `claims` typed as `str` but used as `dict`
- Middleware (logging, normalize) commented out in `app/main.py`
- `app/services/bootstrap.py` returns early, bootstrap logic disabled
- `app/services/store.py` is empty
- `app/middleware/firebase_auth.py` is deprecated and unused
