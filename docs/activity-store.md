# activity-store

Async-first Python library for storing and retrieving Activity Streams JSON-LD objects and collections. Provides pluggable storage backends and cache layers.

**Location:** `../activity-store`
**Version:** 0.1.0
**Python:** >=3.10 (targets 3.13)

## Directory Structure

```
activity_store/
├── __init__.py              # Exports: ActivityStore, SyncActivityStore, Query, exceptions
├── store.py                 # Core ActivityStore class (async context manager)
├── interfaces.py            # ABCs: StorageBackend, CacheBackend
├── exceptions.py            # ActivityStoreError, InvalidLDObject
├── query.py                 # Query model (Pydantic BaseModel)
├── logging.py               # StructuredLogger with metadata support
├── ld.py                    # JSON-LD processing (expand, normalize, compact, frame)
├── utils.py                 # Helpers: chain, first, gather, chain_ids, chain_urls
├── backends/
│   ├── __init__.py          # Conditional exports based on elasticsearch availability
│   ├── memory.py            # InMemoryStorageBackend
│   └── elastic.py           # ElasticsearchBackend (two indices, cursor pagination)
└── cache/
    ├── __init__.py          # Conditional exports based on redis availability
    ├── memory.py            # InMemoryCacheBackend (TTL-based)
    └── redis.py             # RedisCacheBackend (namespaced keys, JSON serialization)

tests/
├── conftest.py              # Fixtures: sample objects, backends, store instances
├── env.py                   # Environment variable loading
├── utils.py                 # Test helpers: create_test_ld_object, capture_logs
├── unit/
│   ├── test_store.py        # ActivityStore core tests
│   ├── test_query.py        # Query model validation
│   ├── test_memory_backends.py  # In-memory backend + cache tests
│   ├── test_logging.py      # Logging tests
│   ├── test_ld.py           # JSON-LD utility tests
│   ├── test_tombstone.py    # Tombstone conversion tests
│   └── test_gold.py         # Gold standard reference tests
└── integration/
    ├── test_elasticsearch_backend.py
    └── test_redis_cache.py
```

## Module Dependencies

```
__init__.py
├── store.py
│   ├── interfaces.py
│   │   └── query.py (Query)
│   ├── backends/memory.py (InMemoryStorageBackend)
│   ├── cache/memory.py (InMemoryCacheBackend)
│   ├── exceptions.py
│   ├── logging.py
│   └── query.py
├── query.py
└── exceptions.py

ld.py (standalone)
├── pyld.jsonld
├── hishel (HTTP caching for context loading)
└── orjson

utils.py (standalone, no internal deps)

backends/elastic.py
├── interfaces.py
├── query.py
├── exceptions.py
└── logging.py

cache/redis.py
├── interfaces.py
└── logging.py
```

## External Dependencies

| Package | Purpose |
|---------|---------|
| `pyld` | JSON-LD processing (expand, compact, frame) |
| `orjson` | Fast JSON serialization |
| `hishel` | HTTP caching for JSON-LD context document loading |
| `pydantic` | Query model validation |
| `elasticsearch` | Elasticsearch client (optional, `[es]` extra) |
| `elasticsearch-dsl` | Elasticsearch query DSL (optional, `[es]` extra) |
| `redis` | Redis client (optional, `[redis]` extra) |
| `aiohttp` | Async HTTP client |
| `python-dotenv` | Environment variable loading |

## Key APIs

### ActivityStore

```python
async with ActivityStore() as store:
    await store.store(ld_object)                    # Store object (must have id + type)
    obj = await store.dereference(id)               # Retrieve by ID (cache-first)
    await store.add_to_collection(obj, collection)  # Add to named collection
    await store.remove_from_collection(id, col)     # Remove from collection
    await store.convert_to_tombstone(obj)            # Soft-delete
    results = await store.query(query)              # Structured query
```

### Query Model

Fields: `text`, `keywords`, `sort`, `size`, `after` (cursor), `collection`, `type`

### Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `ACTIVITY_STORE_BACKEND` | `memory` | `memory` or `elasticsearch` |
| `ACTIVITY_STORE_CACHE` | `memory` | `memory` or `redis` |
| `ACTIVITY_STORE_NAMESPACE` | `activity_store` | Key/index namespace |
| `ELASTICSEARCH_CLOUD_ID` | — | Elastic Cloud deployment ID |
| `ELASTICSEARCH_API_KEY` | — | Elastic Cloud API key |
| `ELASTICSEARCH_URL` / `ES_URL` | — | Direct Elasticsearch URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |

## Design Notes

- Objects must have `id` (string) and `type` (string or list)
- Cache TTL: 1 hour (3600s), only canonical objects cached
- Elasticsearch backend maintains two indices: main objects + collection membership
- All backends return deep copies to prevent external mutation
- Factory methods (`backend_factory`, `cache_factory`) select implementation via env vars
