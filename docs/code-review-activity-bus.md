# Code Review: activity-bus

## Critical Issues

### 1. Five tests are failing — build is broken

Running `uv run pytest` produces 5 failures out of 30 tests. The codebase is in a non-functional state.

### 2. `_extract_user_id` method does not exist

**File:** `tests/test_bus.py:283-313`

Three tests call `bus._extract_user_id(...)`, but `ActivityBus` in `activity_bus/bus.py` has no such method. All three fail with `AttributeError`.

### 3. ID generation is missing — spec says generate, code requires

**File:** `activity_bus/bus.py:73`

`submit()` raises `InvalidActivityError("Activity must have an 'id'")` when `id` is absent. But:
- SPEC.md (line 21): "If `id` is not present, it is generated: `/users/<user-id>/outbox/<nanoid>`"
- PLAN.md (line 38): marks "ID check/generation using nanoid" as complete
- `nanoid` is declared as a dependency but never imported or used
- `uuid` is imported on line 8 but never used
- `test_submit_valid_activity` fails because it submits without `id`, expecting auto-generation

### 4. Scope validation is missing

**File:** `activity_bus/bus.py`

No code validates that the activity ID is scoped under the actor's URI. SPEC.md (line 23) requires this. PLAN.md marks it complete. `ActivityIdError` exists in `errors.py` but is never raised. `test_submit_invalid_id_scope` fails.

### 5. Dual behavior execution on reply notes

**File:** `activity_bus/standard/notes.py`

`create_note` (line 11) matches `{"type": "Create", "object": {"type": "Note"}}`. `create_reply` (line 95) matches `{"type": "Create", "object": {"type": "Note", "inReplyTo": {"@exists": True}}}`. When a reply note is submitted, **both** behaviors match and execute. There is no mechanism to prevent this overlap or documentation that it's intentional.

---

## Important Issues

### 6. Behaviors not stored in ActivityStore per spec

SPEC.md (line 68) and PLAN.md (line 48) say behaviors should be stored in `/sys/behaviors` via ActivityStore. The `@when` decorator only registers in the in-memory `BehaviorRegistry`. `process()` in `bus.py:134` reads only from the in-memory registry.

### 7. Tombstone conversion loses error result data

**File:** `activity_bus/bus.py:174-199`

When an error occurs, the code appends error info to `activity["result"]`, then calls `store.convert_to_tombstone(activity)`. The tombstone is a new dict that does not preserve the `result` field. Error information is discarded.

### 8. `process()` re-raises into its own outer catch block

**File:** `activity_bus/bus.py:156-167`

When a behavior raises, the inner `except` appends to `result` and raises `BehaviorExecutionError`. This is immediately caught by the outer `except Exception` (line 174). Every behavior failure becomes a tombstone, and no further behaviors execute after the first failure. The double-catch is needlessly convoluted.

### 9. Returned Notification from `create_reply` is missing required fields

**File:** `activity_bus/standard/notes.py:130-138`

The Notification activity has no `id` field. Since ID generation isn't implemented (issue 3), this will fail when submitted. It also embeds the entire parent activity as `"object": activity`.

### 10. `asyncio` listed as pip dependency

**File:** `pyproject.toml:10`

`asyncio` is a standard library module, not a pip package. The ancient PyPI package by that name is for Python 3.3 and is unnecessary.

### 11. Dev dependencies mixed with runtime deps

**File:** `pyproject.toml:12-15`

`uv`, `pytest`, `pytest-asyncio`, and `ruff` are listed as project `dependencies` rather than dev dependencies. Anyone installing this library gets the test runner and linter.

### 12. `pyyaml` declared but never used

**File:** `pyproject.toml:8`

No source file imports `yaml` or `pyyaml` anywhere.

---

## Minor Issues

### 13. Global mutable registry — test isolation risk

**File:** `activity_bus/registry.py:52`

Module-level singleton. `@when` decorators in `standard/notes.py` register at import time. Test fixtures clear the registry, but import order makes this fragile.

### 14. Shallow copy in `submit()` doesn't protect nested objects

**File:** `activity_bus/bus.py:61`

`activity = activity.copy()` is shallow. Nested dicts (like `object`) are still shared references. Mutations inside `process()` modify the caller's nested objects.

### 15. No async behavior support

**File:** `activity_bus/bus.py:143`

`result = function(activity)` calls behaviors synchronously. Async behaviors would return a coroutine object instead of executing. SPEC.md lists async rule processing as a design goal.

### 16. No behavior ordering or priority mechanism

Behaviors are stored in a plain dict and iterated in insertion order. No way to specify priority. When both `create_note` and `create_reply` match (issue 5), order depends on import/registration order.

### 17. No integration tests with real ActivityStore

All tests in `test_bus.py` use `AsyncMock` for the store. No end-to-end tests verify actual storage and retrieval.

### 18. `when` decorator shadows builtin `id`

**File:** `activity_bus/behaviors.py:13`

Parameter `id: str | None = None` shadows Python's builtin `id()` function.
