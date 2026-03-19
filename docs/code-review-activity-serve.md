# Code Review: activity-serve

## Critical Issues

### 1. `app/api/query.py` has a syntax error — app cannot start

**File:** `app/api/query.py:46-50`

`is_subpath` contains an incomplete `if` statement:

```python
def is_subpath(uri: str, base: str) -> bool:
    if not uri or not base:
        return False
    if not
```

This is a `SyntaxError`. Since `query.py` is imported by `app/api/__init__.py` which is imported by `app/main.py`, the application will crash on startup.

### 2. `NameError` — `store` used before definition

**File:** `app/api/query.py:16-17`

```python
if user and user['id'] != f"/u/{user_key}":
    item = await store.dereference(f"/u/{user_key}/{path}")
```

`store` is referenced before the `async with ActivityStore() as store:` block on line 19. Raises `NameError` at runtime.

### 3. `has_read_access` and `populate_collection` are empty stubs

**File:** `app/api/query.py:53-76`

`has_read_access` has no return for the false case (returns `None`). `populate_collection` is all `pass` statements, always returns `None` or `False`. The query endpoint calls both expecting real behavior.

### 4. Firebase `initialize_app()` runs at import time

**File:** `app/services/firebase.py:4`

Called at module level. If Firebase credentials aren't configured, this crashes the entire import chain. Tests work only because the stock-token bypass short-circuits before `verify_id_token` is reached.

### 5. `TypeError` on unauthenticated query requests

**File:** `app/api/query.py:27`

When `user` is `None` (from `UserMaybe`), `user["id"]` raises `TypeError: 'NoneType' object is not subscriptable`.

---

## Important Issues

### 6. `parse_auth_token` return type annotation is wrong

**File:** `app/api/auth.py:33`

Signature says `-> str` but returns a tuple `(scheme, token)`. Caller on line 45 destructures as `_, token = parse_auth_token(...)`.

### 7. `verify_auth_token` catches `Exception` too broadly

**File:** `app/api/auth.py:52`

All exceptions from `verify_id_token` become 401 responses. Programming errors, import errors, and connection errors are silently swallowed.

### 8. Bearer scheme check is case-sensitive

**File:** `app/api/auth.py:30`

`if scheme != "Bearer"` rejects `bearer` (lowercase). RFC 7235 specifies case-insensitive comparison.

### 9. `get_or_create_user` type annotation says `str`, body treats as `dict`

**File:** `app/services/user.py:112`

Signature: `async def get_or_create_user(claims: str)`. Body: `claims.get("sub")`.

### 10. Null guard missing on claims fields

**File:** `app/services/user.py:112`

`claims.get("sub").strip()` — if `sub` is missing, `.strip()` on `None` raises `AttributeError`.

**File:** `app/services/user.py:25-27`

`claims.get("sub").encode()` and `claims.get("iss").encode()` — same issue with `get_identity_id`.

### 11. `get_inbox` accepts `UserMaybe` but never checks authorization

**File:** `app/api/user.py:23`

The inbox endpoint injects `UserMaybe` but never uses it for access control. Inbox is fully public.

### 12. `app/services/bootstrap.py` is dead code

**File:** `app/services/bootstrap.py:5-6`

Function body starts with `return`, making everything after unreachable. Bootstrap system is disabled.

### 13. Middleware commented out in `app/main.py`

**File:** `app/main.py:30-31`

Both `LoggingMiddleware` and `NormalizeMiddleware` are commented out. PLAN marks these as complete.

---

## Security Concerns

### 14. Stock tokens have no environment guard

**File:** `app/api/auth.py:9-13`

`_STOCK_TOKENS` is a module-level dict providing an auth bypass. No check ensures this is only used in test/dev. If `add_stock_token` were called in production, it creates a permanent authentication bypass.

### 15. CORS allows all origins with credentials

**File:** `app/core/settings.py:23`, `app/main.py:24`

`allow_origins=["*"]` combined with `allow_credentials=True`. This combination means any website can make credentialed requests to the API.

---

## Test Issues

### 16. No tests for `app/api/query.py`

Zero test coverage for the query endpoint. No `test_query.py` exists.

### 17. Debug `print` in test helper

**File:** `tests/helpers.py:15`

`print(response.json(), expected)` pollutes test output on every assertion.

### 18. `auth_headers` fixture uses unregistered token

**File:** `conftest.py:80-83`

Returns `"Bearer test-token"` which is not in `_STOCK_TOKENS`. Any test using this gets 401.

### 19. `storage` fixture calls teardown before yielding

**File:** `conftest.py:57`

`await store.teardown()` is called immediately after creation, before the test runs. Backwards lifecycle.

### 20. `app` fixture ignores `settings` and `storage` parameters

**File:** `conftest.py:62-63`

Takes `settings` and `storage` as parameters but `create_app()` doesn't receive them. The app creates its own independent instances.

---

## Code Quality

### 21. Pydantic models defined but never used

**File:** `app/models/__init__.py`

`ActivityBase`, `Person`, `Identity`, `Collection`, `OrderedCollection` are defined but never imported anywhere in the application. All endpoints work with raw dicts.

### 22. Empty file: `app/services/store.py`

File exists but contains nothing.

### 23. Deprecated dead code: `app/middleware/firebase_auth.py`

Contains broken imports, invalid syntax, and would cause import errors if referenced. Comment says to ignore it.

### 24. Catch-all route conflicts with explicit routes

**File:** `app/api/query.py:12`

`"/u/{user_key}/{path:path}"` matches anything under `/u/{key}/`, overlapping with the explicit inbox/outbox routes. Works only because router include order in `app/api/__init__.py` puts `user_router` first.

### 25. No pagination parameter validation

**File:** `app/api/user.py:36`, `app/api/query.py:13`

`after: Any=None` and `sort: str` accept arbitrary values with no validation. Passed directly to store.

---

## Plan vs Implementation Gaps

| PLAN Item | Status | Reality |
|-----------|--------|---------|
| Background worker (items 16-17) | Marked complete | Does not exist |
| Middleware (items 11-13) | Marked complete | Commented out |
| `POST /auth/login` | In SPEC | Not implemented |
| Identity path `/u/<key>/idents/<provider>` | In SPEC | Stored at `/auth/identities/{hash}` instead |
| Cookie-based auth | In SPEC | Not implemented, only Bearer tokens |
