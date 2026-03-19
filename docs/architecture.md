# Architecture Overview

Three projects form the Activity Streams platform:

```
┌─────────────────────────────────────────────────────┐
│                  activity-serve                      │
│          (FastAPI HTTP server / API layer)            │
│                                                      │
│   Routes ──► Services ──► activity-bus                │
│                              │                       │
│                              ▼                       │
│                         activity-store               │
│                    (storage + caching layer)          │
└─────────────────────────────────────────────────────┘
```

## Project Roles

| Project | Role | Tech |
|---------|------|------|
| **activity-store** | Data persistence: stores/retrieves Activity Streams JSON-LD objects and collections. Pluggable backends (memory, Elasticsearch) and caches (memory, Redis). | Python, asyncio, pyld, orjson, pydantic |
| **activity-bus** | Processing engine: validates, enqueues, and executes rule-based behaviors on activities. Decorator-driven behavior registration. | Python, asyncio, activity-store |
| **activity-serve** | HTTP API: exposes ActivityPub-compliant endpoints (inbox, outbox, user management), handles authentication via Firebase/Google OAuth. | Python, FastAPI, firebase-admin, activity-store, activity-bus |

## Dependency Flow

```
activity-serve
├── activity-bus (git dependency)
│   └── activity-store (git dependency)
└── activity-store[es,redis] (git dependency)
```

Both `activity-bus` and `activity-serve` depend on `activity-store`. The store is the foundational layer; the bus adds processing logic; the serve project exposes it all over HTTP.

## Data Flow

### Activity Submission (POST /u/{key}/outbox)

1. **activity-serve** receives HTTP request, authenticates user via Firebase
2. Route handler validates ownership, injects actor/id
3. Hands activity to **activity-bus** `submit()`
4. Bus validates (actor, type required), sets `published`, initializes `result`
5. Bus stores activity via **activity-store** `store()`
6. Bus enqueues activity for background processing
7. Bus matches registered behaviors by pattern and executes them

### Object Retrieval (GET /u/{key}/outbox)

1. **activity-serve** receives HTTP request
2. Route queries **activity-store** via `query()` with collection/sort/pagination params
3. Store checks cache (memory/Redis), then backend (memory/Elasticsearch)
4. Returns OrderedCollection response

### Authentication

1. Client sends `Authorization: Bearer <token>`
2. `app/api/auth.py` extracts and validates token via Firebase or stock tokens
3. `app/services/user.py` looks up or creates Identity + Person objects in activity-store
4. User object injected into route handlers via FastAPI dependency injection

## Shared Conventions

- All three projects use `uv` for package management
- Python 3.10+ (activity-store and activity-bus target 3.13)
- Async-first design with sync wrappers where needed
- JSON-LD / Activity Streams 2.0 object format throughout
- pytest + pytest-asyncio for testing
- ruff for linting
