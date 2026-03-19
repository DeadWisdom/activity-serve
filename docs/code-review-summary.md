# Code Review Summary

Cross-project review covering activity-store, activity-bus, and activity-serve.
Individual project reviews are in the companion documents.

## Issue Counts

| Severity | activity-store | activity-bus | activity-serve | Total |
|----------|---------------|--------------|----------------|-------|
| Critical | 5 | 5 | 5 | 15 |
| Important | 10 | 7 | 8 | 25 |
| Minor | 9 | 6 | 6 | 21 |
| **Total** | **24** | **18** | **19** | **61** |

## Blockers — Nothing Runs

Two of three projects have showstopper issues:

1. **activity-bus**: 5 of 30 tests fail. ID generation and scope validation are marked complete in PLAN but never implemented. `_extract_user_id` method referenced by tests doesn't exist.

2. **activity-serve**: `app/api/query.py` has a Python syntax error (incomplete `if` statement). Since it's imported at startup, the entire FastAPI app crashes before serving any request.

3. **activity-store**: Tests pass but contain silent bugs (bare expressions instead of assertions, broken `test_gold.py`).

## Cross-Project Patterns

### Shared mutable state
The in-memory backends in activity-store use class-level dicts shared across all instances. This affects activity-bus and activity-serve tests that rely on isolated store instances.

### `close()` vs `teardown()` confusion
activity-store defines both with overlapping semantics. The sync wrapper calls `teardown()` while the async wrapper calls `close()`. activity-serve's test fixtures call `teardown()` before yielding. The lifecycle contract is undefined.

### Env var inconsistency
activity-store has two code paths for creating Elasticsearch connections (`backend_factory` vs `ElasticsearchBackend._create_client`) that check different environment variable names.

### Constructor parameters silently ignored
Both `ElasticsearchBackend` and `RedisCacheBackend` accept `client` parameters that are never used. `backend_factory` creates and passes clients that are discarded.

### Plan/spec drift
All three projects have PLAN.md files marking features as complete that are not implemented:

| Feature | Project | PLAN Status | Reality |
|---------|---------|-------------|---------|
| ID generation | activity-bus | Complete | Missing |
| Scope validation | activity-bus | Complete | Missing |
| Behavior storage in `/sys/behaviors` | activity-bus | Complete | Not implemented |
| Background worker | activity-serve | Complete | Missing |
| Logging middleware | activity-serve | Complete | Commented out |
| Normalize middleware | activity-serve | Complete | Commented out |
| Login endpoint | activity-serve | In SPEC | Missing |
| Cookie auth | activity-serve | In SPEC | Missing |

### Input mutation
activity-store's `store()` modifies the caller's dict in place (`@context` injection). activity-bus's `submit()` does a shallow copy that doesn't protect nested objects. Callers across all three projects may experience unexpected side effects.

### Type annotation errors
- activity-store: `ElasticsearchBackend.get()` says `-> Dict` but returns `None`
- activity-bus: None found
- activity-serve: `parse_auth_token` says `-> str` but returns tuple; `get_or_create_user` says `claims: str` but treats it as dict

## Top Priorities

### Immediate (app won't start)
1. Fix syntax error in `activity-serve/app/api/query.py`
2. Implement ID generation in `activity-bus/bus.py`
3. Implement scope validation in `activity-bus/bus.py`
4. Add `_extract_user_id` method to `ActivityBus`

### High (correctness bugs)
5. Move class-level dicts to instance-level in activity-store memory backends
6. Fix `frame()` parameter shadowing in `activity-store/ld.py`
7. Fix tombstone timestamp double-suffix in `activity-store/store.py`
8. Fix "OrderdCollection" typo in `activity-store/backends/elastic.py`
9. Add null guards for `claims.get()` calls in `activity-serve/services/user.py`
10. Fix bare expression assertions in `activity-store/tests/unit/test_memory_backends.py`

### Medium (security/design)
11. Add environment guard to stock token mechanism in activity-serve
12. Fix CORS `*` + credentials combination in activity-serve
13. Guard against `None` user in query endpoint audience check
14. Fix Firebase `initialize_app()` at import time
15. Align `close()`/`teardown()` lifecycle across activity-store
