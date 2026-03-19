# Spec vs Implementation: activity-store

Comparison of `SPEC.md` against the actual implementation in `/Users/deadwisdom/Projects/activity-store`.

---

## Spec Summary

The spec describes an async-first Python library for storing and retrieving Activity Streams JSON-LD objects and collections. Core concepts include LD-objects (JSON-LD dicts with `@context` and `type`), canonical storage keyed by `id`, collections with partial object membership, and Tombstone-based soft deletion. The library uses pluggable `StorageBackend` and `CacheBackend` ABCs, an `ActivityStore` orchestration layer with async context management and a synchronous wrapper, a structured `Query` model, and utilities for JSON-LD normalization and logging. Packaging targets Python 3.10+ with optional `[es]` and `[redis]` extras.

---

## Implemented

### StorageBackend Interface
- **`add(ld_object, collection)`** - Implemented in `activity_store/interfaces.py:14`. Signature matches spec.
- **`remove(id, collection)`** - Implemented at line 25. Signature matches.
- **`get(id, collection)`** - Implemented at line 36. Signature matches.
- **`query(query: Query)`** - Implemented at line 49. Signature matches.
- **`setup()` (optional)** - Implemented at line 66 as a default no-op.
- **`teardown()` (optional)** - Implemented at line 70 as a default no-op.

### CacheBackend Interface
- **`add(key, value, ttl=3600)`** - Implemented in `activity_store/interfaces.py:79`. Signature matches spec. TTL defaults to 3600 (1 hour) as specified.
- **`get(key)`** - Implemented at line 91. Matches spec.
- **`remove(key)`** - Implemented at line 103. Matches spec.
- **`setup()` / `teardown()` (optional)** - Implemented at lines 117-122 as default no-ops.

### ActivityStore
- **Async-first, context-managed** - Implemented in `activity_store/store.py:96-131`. Supports `async with`.
- **Accepts optional `backend`, `cache`, `namespace`** - Constructor at lines 104-120. Matches spec.
- **Uses `backend_factory()` / `cache_factory()` if none provided** - Lines 118-119 call factory methods when args are `None`.
- **Uses env vars `ACTIVITY_STORE_BACKEND`, `ACTIVITY_STORE_CACHE`, `ACTIVITY_STORE_NAMESPACE`** - Factory methods at lines 148-236 read these env vars.
- **`store(ld_object)`** - Implemented at line 238. Validates `id` and `type`, ensures `@context`, stores in backend and cache.
- **`dereference(id)`** - Implemented at line 271. Cache-first lookup, falls back to backend, updates cache on miss.
- **`add_to_collection(ld_object, collection)`** - Implemented at line 300. Creates partial representation and stores in backend.
- **`remove_from_collection(id, collection)`** - Implemented at line 334. Delegates to `backend.remove()`.
- **`convert_to_tombstone(ld_object)`** - Implemented at line 349. Creates tombstone with `formerType` and `deleted` timestamp.
- **`query(query: Query)`** - Implemented at line 389. Accepts Query, dict, or kwargs.
- **Has synchronous wrapper** - `SyncActivityStore` at line 444.

### Collection Details
- **Partial LD-objects for membership** - `add_to_collection()` at line 315 creates partials with `id`, `type`, and select fields (`name`, `summary`, `published`, `updated`).
- **Duplicate `id`s overwritten** - Both backends use `id` as key, so re-adding overwrites.
- **Elasticsearch keys = hash(collection-id + object-id)** - `_get_collection_id()` at `elastic.py:155-166` uses SHA-256 of `"{collection}-{object_id}"`.
- **`_collection` metadata stripped on read** - `_strip_metadata_fields()` at `elastic.py:210-228` removes `_collection`, `_all_text`, `_id`, `_index`, `_score`.

### Caching
- **Only used for canonical dereferencing** - `dereference()` checks cache first, then backend. Collection operations do not use cache.
- **Keys = raw object `id`** - Cache keys in `store()` and `dereference()` use the object's `id` string directly.
- **TTL = 1 hour** - Default `ttl=3600` in `CacheBackend.add()`.
- **No preloading** - No preloading logic exists.

### Query Model
- **Fields: `text`, `keywords`, `sort`, `size`, `after`, `collection`, `type`** - All present in `activity_store/query.py:10-51`.
- **Structured Query object** - Pydantic `BaseModel` at `query.py:10`.

### Exceptions
- **`ActivityStoreError`** - Defined in `activity_store/exceptions.py:5`. Subclasses `Exception`.
- **`InvalidLDObject`** - Defined at line 11. Subclasses both `ActivityStoreError` and `ValueError`.

### Directory Layout
- All files from the spec layout exist: `__init__.py`, `store.py`, `interfaces.py`, `backends/` (with `__init__.py`, `memory.py`, `elastic.py`), `cache/` (with `__init__.py`, `memory.py`, `redis.py`), `utils.py`, `ld.py`, `exceptions.py`, `query.py`, `logging.py`.

### Packaging
- **Python 3.10+** - `pyproject.toml` line 6: `requires-python = ">=3.10"`.
- **`pyproject.toml` with extras `[es]`, `[redis]`** - Present at lines 23-30.
- **Minimal public API via `__init__.py`** - Exports `ActivityStore`, `Query`, `ActivityStoreError`, `InvalidLDObject`.

### Testing
- **pytest** - Configured in `pyproject.toml` lines 39-42.
- **In-memory implementations for both backends** - `InMemoryStorageBackend` and `InMemoryCacheBackend` exist and are used in tests.

### Utilities
- **Normalize to list-based format** - `normalize()` in `ld.py:135-169` compacts with `compactArrays=False` and expands `type` to list.
- **Convert to Tombstone** - `convert_to_tombstone()` in `store.py:349-387`.
- **Structured logger** - `StructuredLogger` in `logging.py:12-114` with `get_logger()` factory.

---

## Partially Implemented

### Synchronous Wrapper
The spec says ActivityStore "has synchronous wrapper." `SyncActivityStore` exists (`store.py:444-521`) but:
- It is **not exported** in `__init__.py`'s `__all__` (line 12-17). Users cannot discover it through the public API.
- `__exit__` calls `teardown()` (line 476) while `__aexit__` calls `close()` (line 130). These have different semantics: `close()` closes backend/cache connections, while `teardown()` cleans up data but does not close connections.
- No test coverage exists for `SyncActivityStore`.

### Pagination (Collections)
The spec says: "Pagination via `next`, `prev`, `items`, `totalItems`; not stored." The Elasticsearch backend provides `next` cursors via `search_after` (`elastic.py:426-430`), but:
- `prev` is never provided.
- The in-memory backend does not implement cursor-based pagination at all (`memory.py:150-151` ignores the `after` field).

### Overridable Logger Adapter
The spec mentions "Structured logger with overridable adapter." `StructuredLogger` exists and wraps Python's standard `logging.Logger`, but there is no explicit adapter pattern or documented way to swap in a different logging backend. The `with_logging` decorator (`logging.py:142-196`) does not work with async functions (it wraps with a synchronous wrapper that cannot catch exceptions from coroutines).

### Collections May Have Canonical Representations
The spec says "Collections may have canonical representations, but it's optional." There is no mechanism to store or retrieve a collection's own metadata (e.g., a collection object with `type: Collection`, `name`, etc.). Collections exist only as implicit groupings in the backend.

---

## Not Implemented

### Compacted JSON-LD Storage
The spec says "Store all LD-objects as compacted JSON-LD." The `store()` method (`store.py:238-269`) does **not** compact objects before storage. It only adds `@context` if missing. The `compact()` function exists in `ld.py:172-192` but is never called during storage. Objects are stored as-is.

### LD-Object Requires `@context`
The spec defines an LD-object as "A JSON-LD dictionary with a `@context` and `type`." The implementation only requires `id` and `type` (`_require_id` and `_require_type` in `store.py:28-74`). The `@context` is silently added if missing rather than being validated as a required property.

### Dereferencing TTL Behavior
The spec says "Dereferencing uses cache first, then backend, with TTL of 1 hour." While the TTL default is 1 hour, the `store()` method calls `cache.add(object_id, ld_object)` without specifying a TTL explicitly (line 262), relying on the default. The `dereference()` method similarly calls `cache.add(id, obj)` without explicit TTL (line 296). This works correctly by coincidence (the default is 3600), but no test verifies TTL expiration behavior in the context of dereferencing.

### `elasticsearch-dsl` Usage
The `[es]` extra includes `elasticsearch-dsl` (`pyproject.toml:26`), but the Elasticsearch backend (`elastic.py`) builds queries manually with raw dicts rather than using `elasticsearch-dsl`. The dependency is declared but unused.

---

## Deviations

### `store()` Mutates Caller's Object
`store.py:255-256` modifies the input dict in place by adding `@context` if missing. The spec implies LD-objects should be stored as compacted copies; the implementation mutates the original reference.

### Malformed Tombstone Timestamp
`store.py:370`: `datetime.now(dt.UTC).isoformat() + "Z"` produces an invalid ISO 8601 string like `2026-03-17T12:00:00+00:00Z`. Python's `isoformat()` with a UTC timezone already appends `+00:00`; appending `Z` creates a double suffix. The spec says tombstones should have a `deleted` timestamp but doesn't specify format; the implementation produces an invalid one.

### Elasticsearch Backend Ignores `client` Parameter
`elastic.py:59-79`: The constructor accepts an optional `client` parameter but never uses it. It always creates a new client via `_create_client()`. The `backend_factory()` in `store.py:181` passes a constructed client, but it is silently discarded.

### Redis Cache Backend Ignores `client` Parameter
`cache/redis.py:22-38`: Same issue. Constructor accepts `client` but always creates a new client from `redis_url` at line 38.

### Inconsistent Environment Variable Names
The `backend_factory()` (`store.py:172-173`) checks `ELASTICSEARCH_PASSWORD` and uses it as `api_key`. The `ElasticsearchBackend._create_client()` (`elastic.py:88-107`) checks separate `ELASTICSEARCH_API_KEY` and `ELASTICSEARCH_PASSWORD` vars with different semantics. The factory uses `ES_URL` (line 184) while the backend uses `ELASTICSEARCH_URL` (line 98).

### Inconsistent Default Query Size
`query.py:34` defaults `size` to 10. The Elasticsearch backend (`elastic.py:400`) overrides to 21 when extracting from the query dict: `size = query_dict.get("size", 21)`. This means that the `to_dict()` method filters `None` values, but `size` always has a value (10), so this fallback to 21 is dead code. However, the two different defaults signal a design inconsistency.

### "OrderdCollection" Typo
`elastic.py:420`: `"OrderdCollection"` is misspelled (should be `"OrderedCollection"`). The integration test at `test_elasticsearch_backend.py` asserts the misspelled value, enshrining the bug.

### Shared Mutable Class-Level State in In-Memory Backends
`backends/memory.py:19-20` and `cache/memory.py:20`: Storage dicts are declared as **class-level** attributes, not instance-level. All instances of `InMemoryStorageBackend` share the same `_objects` and `_collections` dicts. Same for `InMemoryCacheBackend._cache`. This means tests contaminate each other unless `teardown()` is explicitly called between them.

### `close()` Not Implemented on In-Memory Backends
The interfaces define `close()` as a no-op default (`interfaces.py:62-64, 113-115`). `ActivityStore.__aexit__` calls `close()`, which calls `backend.close()` and `cache.close()`. Neither in-memory backend overrides `close()`, and neither has a `teardown()` call in `close()`. The `InMemoryCacheBackend` has no `teardown()` method at all, so data is never cleaned up through the `close()` path.

### `frame()` Variable Shadowing Bug
`ld.py:195-227`: The `frame()` function accepts parameters named `compact` and `normalize` (lines 203-204), which shadow the module-level functions `compact()` and `normalize()`. When `normalize=True`, line 222 calls `normalize(result, ...)` which is actually `True(result, ...)`, causing a `TypeError` at runtime.

---

## Implementation Beyond Spec

### `_to_async` Helper
`store.py:77-93`: A `_to_async` function exists that wraps sync functions using `asyncio.get_event_loop()`. It is never called anywhere and uses a deprecated API (`get_event_loop()` deprecated since Python 3.10).

### `_require_id` and `_require_type` Validation Functions
`store.py:28-74`: Standalone validation functions that check for `id` (must be a string) and `type` (must be a string or list). The spec mentions validation implicitly but does not specify these as separate utility functions.

### `ld.py` JSON-LD Processing Module
The spec mentions "Normalize to list-based format" under Utilities, but `ld.py` provides a much richer set of JSON-LD functions: `expand()`, `compact()`, `normalize()`, `frame()`, `map_property()`, `compact_property()`, `expand_property()`, plus document loader customization with `hishel` HTTP caching and `pyld` monkey-patching. These are not referenced in the spec's interface definitions. Notably, none of these are used by the core `ActivityStore` class.

### `utils.py` Helper Functions
`chain()`, `chain_ids()`, `chain_urls()`, `first()`, `first_id()`, `gather()`, `gather_urls()` are implemented. The spec mentions "Utilities" but only lists "Normalize to list-based format", "Convert to Tombstone", and "Structured logger". These chain/gather utilities are used by `ld.py` but are beyond the spec.

### `close()` Method on Interfaces and Store
The spec lists `setup()` and `teardown()` as optional interface methods. The implementation adds a separate `close()` method on both `StorageBackend` (`interfaces.py:62`) and `CacheBackend` (`interfaces.py:113`), and on `ActivityStore` (`store.py:132`). This creates a confusing lifecycle with both `close()` and `teardown()` having overlapping but different purposes.

### Query Accepts Dict and Kwargs
`ActivityStore.query()` (`store.py:389-441`) accepts not just a `Query` object but also a `dict` or keyword arguments, which it merges. The spec only mentions `query(query: Query)`.

### `refresh_on_write` on Elasticsearch Backend
`elastic.py:67`: The Elasticsearch backend has a `refresh_on_write` parameter not mentioned in the spec, used for testing to ensure immediate index refresh after writes.

### Dependencies Beyond Spec
`pyproject.toml` includes `aiohttp`, `ruff`, and `requests` in main dependencies. `ruff` is a linter (should be dev-only), `aiohttp` and `requests` are not used by library code. `redis` and `elasticsearch` are in both main deps and optional extras, defeating the purpose of optional dependencies.

### `with_logging` Decorator
`logging.py:142-196`: A decorator for adding logging to functions. Not mentioned in the spec. Also does not work with async functions.

### `any_none()` Utility in `ld.py`
`ld.py:74-86`: Checks if any value in a document is `None`. Used by `frame()` for `require_match` support. Not in spec.
