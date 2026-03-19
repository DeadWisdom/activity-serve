# Code Review: activity-store

## Critical Issues

### 1. Shared mutable class-level state in backends

**Files:** `activity_store/backends/memory.py:19-20`, `activity_store/cache/memory.py:22-23`

Both in-memory classes declare storage as **class-level** mutable attributes:

```python
class InMemoryStorageBackend(StorageBackend):
    _objects: Dict[str, Dict[str, Any]] = {}
    _collections: Dict[str, Set[str]] = {}
```

These are shared across ALL instances. Every `InMemoryStorageBackend()` shares the same dicts. Tests contaminate each other unless `teardown()` is explicitly called. The `__init__` methods are empty `pass` statements.

### 2. Typo: "OrderdCollection" in Elasticsearch backend

**File:** `activity_store/backends/elastic.py:420`

```python
"type": "OrderdCollection" if "sort" in es_query else "Collection",
```

Misspelled "OrderedCollection". The integration test at `test_elasticsearch_backend.py:274` enshrines the bug by asserting the misspelled value.

### 3. Variable shadowing in `frame()` causes runtime crash

**File:** `activity_store/ld.py:195-227`

The `frame()` function accepts parameters named `compact` and `normalize` (lines 204-205), which shadow the module-level functions of the same name. When `normalize=True`, line 222 calls `normalize(result, ...)` which is actually `True(result, ...)` — a `TypeError`.

### 4. Malformed timestamp in tombstone creation

**File:** `activity_store/store.py:370`

```python
"deleted": datetime.now(dt.UTC).isoformat() + "Z",
```

`isoformat()` with UTC already produces `+00:00`. Appending `Z` creates `2026-03-17T12:00:00+00:00Z` — invalid ISO 8601. The test regex happens to match it, masking the bug.

### 5. Credentials in `.env` file

**File:** `.env:1-2`

Elasticsearch cloud ID and API key in plaintext. While `.env` is in `.gitignore`, it is present on disk and could be inadvertently committed.

---

## Important Issues

### 6. `SyncActivityStore.__exit__` calls `teardown()` instead of `close()`

**File:** `activity_store/store.py:474-477`

The sync context manager calls `teardown()` while the async `__aexit__` calls `close()`. These have different semantics — `teardown()` doesn't close backend connections, while `close()` doesn't clean up cache. Backend connections leak in sync usage.

### 7. `backend_factory` and `ElasticsearchBackend._create_client` use different env vars

**File:** `activity_store/store.py:171-185` vs `activity_store/backends/elastic.py:88-107`

The factory checks `ELASTICSEARCH_PASSWORD` and uses it as `api_key`. The backend's own `_create_client` checks separate `ELASTICSEARCH_API_KEY` and `ELASTICSEARCH_PASSWORD` vars with different semantics. Also: factory checks `ES_URL`, backend checks `ELASTICSEARCH_URL`.

### 8. `RedisCacheBackend.__init__` ignores `client` parameter

**File:** `activity_store/cache/redis.py:22-38`

Constructor accepts an optional `client` parameter but never uses it. Always creates a new client from URL.

### 9. `ElasticsearchBackend.__init__` ignores `client` parameter

**File:** `activity_store/backends/elastic.py:59-86`

Same issue. The `backend_factory` in `store.py` creates a client and passes it (line 181), but it is silently ignored.

### 10. `store()` mutates the caller's object

**File:** `activity_store/store.py:255-256`

```python
if "@context" not in ld_object:
    ld_object["@context"] = "https://www.w3.org/ns/activitystreams"
```

Modifies the input dict in place before storing. Callers would not expect this side effect.

### 11. Inconsistent default query size between backends

**File:** `activity_store/query.py:34` (default 10) vs `activity_store/backends/elastic.py:400` (default 21)

The Query model defaults to size 10, but the Elasticsearch backend overrides to 21 when extracting from the dict.

### 12. `test_get_nonexistent` assertions are bare expressions

**File:** `tests/unit/test_memory_backends.py:63-64`

```python
await backend.get("nonexistent") is None
await backend.get("nonexistent", "collection") is None
```

These are expressions, not assertions. The result is discarded — they never actually verify anything.

### 13. No upper bound on Query `size`

**File:** `activity_store/query.py:53-59`

Only checks `size > 0`. A caller could pass `size=999999999`, causing memory exhaustion or Elasticsearch failures.

### 14. `test_gold.py` is broken

**File:** `tests/unit/test_gold.py:30-31`

Creates `ActivityStore()` without importing it. Either fails with `NameError` or is never collected.

### 15. Elasticsearch `get()` return type annotation is wrong

**File:** `activity_store/backends/elastic.py:310`

Annotated as `-> Dict[str, Any]` but returns `None` on `NotFoundError` (line 330). Interface correctly says `Dict | None`.

---

## Minor Issues

### 16. `_to_async` uses deprecated `get_event_loop()` and is dead code

**File:** `activity_store/store.py:90`

Deprecated since Python 3.10, emits warnings in 3.12+. Also never called anywhere.

### 17. `_clean_expired()` never called on cache

**File:** `activity_store/cache/memory.py:71-77`

Expired entries are only cleaned on individual `get()` calls. Entries that are never retrieved accumulate forever.

### 18. Monkey-patching `jsonld._is_numeric` is fragile

**File:** `activity_store/ld.py:30`

Patches a private attribute of `pyld`. Any library upgrade could break this silently.

### 19. Mutable default argument in `load_document`

**File:** `activity_store/ld.py:56`

```python
def load_document(url, options={}):
```

Classic Python anti-pattern with mutable default.

### 20. Duplicate/misplaced dependencies in `pyproject.toml`

`redis` and `elasticsearch` are in both main dependencies and optional extras, defeating the purpose of optional deps. `pytest`, `pytest-asyncio`, `pytest-cov` are each listed twice in dev deps. `ruff`, `aiohttp`, and `requests` are in main deps but unused by library code.

### 21. `with_logging` decorator doesn't work with async functions

**File:** `activity_store/logging.py:160-192`

The decorator wraps with a synchronous wrapper. Exception handling on lines 180-190 never catches exceptions from async functions since exceptions happen at `await` time, not coroutine creation.

### 22. No test coverage for `SyncActivityStore`

No tests exist for the synchronous wrapper class.

### 23. `close()` vs `teardown()` lifecycle is confusing

Both exist on `ActivityStore`, `StorageBackend`, and `CacheBackend`. Their relationship is undefined. The ES integration test calls both, but the order matters and is undocumented.

### 24. `SyncActivityStore` not exported in `__init__.py`

Not in `__all__` or imported in the package init. Users cannot discover it through the public API.
