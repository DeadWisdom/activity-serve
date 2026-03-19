# Consolidation: activity-store + activity-bus → activity-serve

Merging the `activity-store` and `activity-bus` libraries into `activity-serve`
as sub-packages of a single installable package: `activity_serve`.

## Goals

- Single repo, single package (`activity_serve`)
- Importable by external FastAPI apps: `from activity_serve.store import ActivityStore`
- TDD: tests first, implementation to make them pass
- Start with in-memory backends only; add Elasticsearch/Redis later

## Package Structure

Rename `app/` → `activity_serve/`. The package has four sub-packages:

```
activity_serve/
├── __init__.py
├── core/                    # JSON-LD and Activity Streams foundations
│   ├── __init__.py
│   ├── ld.py               # JSON-LD normalization, framing, expansion (from activity-store)
│   └── utils.py            # Chain/first/gather utilities (from activity-store)
├── store/                   # Object storage and caching
│   ├── __init__.py          # Exports: ActivityStore, Query, exceptions
│   ├── store.py             # ActivityStore class
│   ├── query.py             # Query model
│   ├── interfaces.py        # StorageBackend / CacheBackend ABCs
│   ├── exceptions.py        # ActivityStoreError, InvalidLDObject
│   ├── logging.py           # Structured logger
│   └── backends/
│       ├── __init__.py
│       └── memory.py        # InMemoryStorageBackend, InMemoryCacheBackend
├── bus/                     # Activity processing engine
│   ├── __init__.py          # Exports: ActivityBus, when, exceptions
│   ├── bus.py               # ActivityBus class
│   ├── behaviors.py         # @when decorator, get_all_behaviors
│   ├── registry.py          # BehaviorRegistry
│   └── errors.py            # ActivityBusError, InvalidActivityError, etc.
└── api/                     # FastAPI HTTP layer
    ├── __init__.py
    ├── auth.py
    ├── user.py
    ├── query.py
    ├── health.py
    └── admin.py
```

Also at the top level:
```
├── models/                  # Stays under activity_serve (was app/models)
├── services/                # Stays under activity_serve (was app/services)
├── middleware/               # Stays under activity_serve (was app/middleware)
```

## Import Changes

Old → New:
```python
# Store
from activity_store import ActivityStore       → from activity_serve.store import ActivityStore
from activity_store.ld import frame            → from activity_serve.core.ld import frame
from activity_store.utils import first_id      → from activity_serve.core.utils import first_id
from activity_store.backends.memory import ... → from activity_serve.store.backends.memory import ...
from activity_store.query import Query         → from activity_serve.store.query import Query

# Bus
from activity_bus import ActivityBus, when     → from activity_serve.bus import ActivityBus, when
from activity_bus.errors import ...            → from activity_serve.bus.errors import ...

# API (internal)
from app.main import create_app               → from activity_serve.main import create_app
from app.api.auth import User                 → from activity_serve.api.auth import User
from app.core.settings import Settings        → from activity_serve.core.settings import Settings
```

## What Gets Copied vs. Rebuilt via TDD

### Copied as-is (with import path updates)
- `core/ld.py` — from `activity_store/ld.py`
- `core/utils.py` — from `activity_store/utils.py`

These are foundational JSON-LD and utility functions. They get copied over
directly along with their existing tests from the `activity-store` repo.

### Rebuilt via TDD
Everything else is written test-first. The sibling repos (`activity-store`,
`activity-bus`) are reference material for understanding the desired behavior,
but we are not copying implementation code. The process for each module:

1. Write tests that define the behavior we need
2. Run tests, confirm they fail
3. Write minimal code to make them pass
4. Refactor

This applies to:
- `store/` — ActivityStore, backends, query, interfaces, exceptions
- `bus/` — ActivityBus, behaviors, registry, errors

### Not included in iteration 1
- Elasticsearch backend
- Redis cache backend
- Standard note behaviors

## Iteration Plan

### Iteration 0: Fix current tests

The existing tests don't run because `app/api/query.py` has a syntax error
on line 49. Fix this first so we have a green baseline.

**Files to fix:**
- `app/api/query.py` — complete the incomplete `is_subpath` function stub

**Verify:** `uv run pytest` passes all 7 tests.

### Iteration 1: Rename app → activity_serve, establish core (TDD)

Rename the `app/` directory to `activity_serve/`. Update all internal imports.
Then build `core/` as a proper sub-package via TDD — write tests for the
JSON-LD and utility functions, then implement to make them pass.

**Steps:**
1. Rename `app/` → `activity_serve/`
2. Update all imports (`from app.` → `from activity_serve.`)
3. Update `pyproject.toml` paths
4. Update test imports in `conftest.py` and test files
5. Verify existing tests still pass with new import paths

Then establish `core/` sub-package:

6. Copy `ld.py` and `utils.py` from `activity-store` into `activity_serve/core/`
7. Migrate their existing tests from `activity-store/tests/` into `tests/core/`
8. Update imports within `ld.py` and `utils.py`

`settings.py` stays in `core/` as it already lives there.

**Verify:** all core tests pass + existing API tests still pass.

### Iteration 2: Reimplement store sub-package (TDD)

Write tests that define the store behavior we need, then implement to pass.
Use the original `activity-store` repo as reference for desired behavior, but
write fresh implementation code.

**Tests to write** (in `tests/store/`):
- `test_store.py` — store/dereference/cache behavior, context manager
- `test_memory_backends.py` — InMemoryStorageBackend and InMemoryCacheBackend
- `test_query.py` — Query model validation
- `test_tombstone.py` — convert_to_tombstone behavior
- `test_collections.py` — add_to_collection / remove_from_collection

**Implementation files** (created only after tests exist):
- `activity_serve/store/__init__.py`
- `activity_serve/store/store.py`
- `activity_serve/store/query.py`
- `activity_serve/store/interfaces.py`
- `activity_serve/store/exceptions.py`
- `activity_serve/store/logging.py`
- `activity_serve/store/backends/__init__.py`
- `activity_serve/store/backends/memory.py`

**Verify:** all store tests pass + existing API tests still pass.

### Iteration 3: Reimplement bus sub-package (TDD)

Write tests that define the bus behavior we need, then implement to pass.
Use the original `activity-bus` repo as reference for desired behavior, but
write fresh implementation code.

**Tests to write** (in `tests/bus/`):
- `test_bus.py` — submit, process_next, process
- `test_behaviors.py` — @when decorator registration
- `test_registry.py` — BehaviorRegistry operations

**Implementation files** (created only after tests exist):
- `activity_serve/bus/__init__.py`
- `activity_serve/bus/bus.py`
- `activity_serve/bus/behaviors.py`
- `activity_serve/bus/registry.py`
- `activity_serve/bus/errors.py`

**Verify:** all bus tests pass + all store tests pass + existing API tests pass.

### Iteration 4: Update API layer

Update the API routes to use the local store/bus sub-packages instead of the
external libraries. Update `conftest.py` and test helpers.

**Files to update:**
- `activity_serve/api/user.py` — update imports
- `activity_serve/api/query.py` — update imports
- `activity_serve/services/user.py` — update imports
- `activity_serve/services/bootstrap.py` — update imports
- `conftest.py` — use `activity_serve.store.backends.memory`
- `tests/helpers.py` — use `activity_serve.core.ld`

**Verify:** all tests pass. Remove `activity-store` and `activity-bus` from
`pyproject.toml` dependencies and `[tool.uv.sources]`.

### Iteration 5: Clean up

- Remove any remaining references to external packages
- Verify the package is installable: `uv pip install -e .`
- Verify imports work from outside: `from activity_serve.store import ActivityStore`
- Update `pyproject.toml` with correct package metadata

## Dependencies

After consolidation, `pyproject.toml` dependencies change:

**Remove:**
- `activity-store[es,redis]`
- `activity-bus`

**Add (these were transitive through activity-store):**
- `pyld`
- `hishel`
- `orjson`

**Keep:**
- `fastapi[standard]`, `uvicorn`, `pydantic`, `pydantic-settings`
- `structlog`, `nanoid`, `python-jose`, `python-multipart`
- `ruff`, `firebase-admin`

## Current State

- [x] Iteration 0: Fix current tests
- [x] Iteration 1: Rename + establish core
- [x] Iteration 2: Store sub-package (TDD — 40 tests)
- [x] Iteration 3: Bus sub-package (TDD — 21 tests)
- [x] Iteration 4: Update API layer
- [x] Iteration 5: Clean up

Total: 94 tests passing
