# Activity Serve

An ActivityPub-compatible server and library built with FastAPI. Provides storage, processing, and HTTP endpoints for Activity Streams 2.0 objects — all in a single importable package.

## Package Structure

```
activity_serve/
├── core/       # JSON-LD processing and utilities
├── store/      # Object storage with pluggable backends
├── bus/        # Rule-based activity processing engine
├── api/        # FastAPI HTTP endpoints
├── services/   # User management, authentication
└── middleware/  # Request logging, normalization
```

**Use as a library:**

```python
from activity_serve.store import ActivityStore
from activity_serve.bus import ActivityBus, when
from activity_serve.core.ld import frame
from activity_serve.core.utils import first_id
```

**Use as an app:**

```python
from activity_serve.main import create_app

app = create_app()
```

## Installation

```bash
uv add activity-serve

# With optional backends
uv add "activity-serve[es]"     # Elasticsearch storage
uv add "activity-serve[redis]"  # Redis caching
```

For development:

```bash
git clone https://github.com/yourusername/activity-serve.git
cd activity-serve
uv sync
```

## Configuration

Environment variables:

```
GOOGLE_CLIENT_ID=your-google-client-id
```

For Elasticsearch storage:
```
ELASTICSEARCH_URL=http://localhost:9200
```

For Redis caching:
```
REDIS_URL=redis://localhost:6379/0
```

## Running

```bash
uv run uvicorn activity_serve.main:app --reload
```

## Testing

```bash
uv run pytest

# Integration tests (require running services)
ELASTICSEARCH_URL=http://localhost:9200 uv run pytest tests/store/test_elasticsearch_backend.py
REDIS_URL=redis://localhost:6379/0 uv run pytest tests/store/test_redis_cache.py
```

## API Endpoints

- `GET /me` — Current authenticated user
- `GET /u/{key}/inbox` — User inbox
- `GET /u/{key}/outbox` — User outbox
- `POST /u/{key}/outbox` — Submit an activity
- `GET /u/{key}/{path}` — Query any sub-path (objects, collections)
- `GET /admin` — Admin UI
- `GET /healthz` — Health check

## Core Concepts

**ActivityStore** manages storage and caching of Activity Streams objects. Backends are pluggable — in-memory for development, Elasticsearch for production, Redis for caching.

**ActivityBus** processes activities through a rule-based behavior system. Register behaviors with the `@when` decorator to match activities by JSON-LD pattern:

```python
from activity_serve.bus import when

@when({"type": "Create", "object": {"type": "Note"}})
def handle_new_note(activity):
    print(f"New note created: {activity['object']['content']}")
```

**core.ld** provides JSON-LD operations — normalize, expand, compact, and frame — built on pyld.

## License

MIT
