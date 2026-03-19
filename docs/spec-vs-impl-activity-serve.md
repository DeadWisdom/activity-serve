# Spec vs Implementation: activity-serve

A section-by-section comparison of `SPEC.md` against the actual codebase.

---

## Spec Summary

SPEC.md describes Activity Serve as a modular FastAPI application exposing an HTTP interface to Activity Bus and Activity Store. Key features include: ActivityPub-compatible inbox/outbox endpoints, Google OAuth login via Firebase, identity management, background activity processing, an admin UI shell, structured logging, ID normalization, Docker deployment, and CORS support.

---

## Implemented

### 1. GET `/u/<user-key>/outbox` -- Publicly fetch paged outbox activities

- **File:** `app/api/user.py:35-53`
- Queries the activity store for the user's outbox, supports `sort` and `after` pagination parameters.
- Returns an `OrderedCollection` with `attributedTo` and `audience` fields.
- Tests exist in `tests/test_outbox.py`.

### 2. POST `/u/<user-key>/outbox` -- Submit a new activity

- **File:** `app/api/user.py:56-86`
- Requires auth via Bearer token (`User` dependency).
- Injects `actor` if missing (line 74-75).
- Generates `id` if missing using nanoid (line 82-83).
- Validates actor matches URL user (line 78-79).
- Submits activity to Activity Bus (line 86).
- Tests exist in `tests/test_outbox.py`.

### 3. GET `/u/<user-key>/inbox` -- Publicly fetch inbox

- **File:** `app/api/user.py:22-32`
- Dereferences the inbox from the store.
- Returns 404 if not found.
- Test exists in `tests/test_inbox.py`.

### 4. GET `/admin` -- Public placeholder HTML admin UI

- **File:** `app/api/admin.py:8-51`
- Returns a static HTML page.
- **Deviation:** Spec says "Public placeholder" but implementation does NOT require auth (no `User` dependency on the endpoint). The import of `User` from auth exists but is unused.
- Test exists in `tests/test_admin.py`.

### 5. GET `/healthz` -- Liveness check

- **File:** `app/api/health.py:7-10`
- Returns `"ok"`.
- Test exists in `tests/test_health.py`.

### 6. User object type (`Person`)

- **File:** `app/services/user.py:32-85`
- Creates users with `@context`, `id`, `type` ("Person"), `name`, `preferredUsername`, `image`, `inbox`, `outbox`, `published`.
- All fields from the spec are present.
- Inbox and outbox collections are created automatically.

### 7. Configuration via Pydantic `BaseSettings`

- **File:** `app/core/settings.py:1-25`
- Uses `pydantic-settings` with `.env` support.
- Includes `ACTIVITY_SERVE_BASE_URL` (optional), session cookie settings, `GOOGLE_CLIENT_ID`, `ALLOW_ORIGINS`.
- **Note:** `ACTIVITY_STORE_BACKEND` and `ACTIVITY_STORE_CACHE` from the spec are not in this settings class; they are presumably handled by the `activity-store` library directly via its own env var support.

### 8. Docker deployment

- **File:** `Dockerfile:1-24`
- Python 3.10-slim, installs uv, copies project, runs uvicorn on port 8000.

### 9. CORS -- `*` by default

- **File:** `app/main.py:21-27`, `app/core/settings.py:23`
- `allow_origins=["*"]`, `allow_credentials=True`, all methods and headers allowed.

### 10. Auth via Bearer token

- **File:** `app/api/auth.py:1-77`
- Parses `Authorization: Bearer <token>` header.
- Verifies via Firebase `verify_id_token` or stock tokens (for testing).
- `User` (required) and `UserMaybe` (optional) dependency injection types.

### 11. Actor/ID injection and validation on outbox POST

- **File:** `app/api/user.py:74-83`
- Injects `actor` if missing, validates actor matches URL user, generates `id` if missing.

### 12. Idempotent design (overwrites allowed)

- Spec says "Overwrites allowed for existing IDs." The store is called with `store.store()` which overwrites by ID. This is inherent to the activity-store library.

### 13. ActivityStreamResponse (JSON-LD content type)

- **File:** `app/api/__init__.py:10-11`
- Custom `ORJSONResponse` subclass with media type `application/ld+json; profile="https://www.w3.org/ns/activitystreams"`.

---

## Partially Implemented

### 1. Identity object type

- **Spec:** Stored at `/u/<user-key>/idents/<provider>` with fields `provider`, `sub`, `email`, `name`, `picture`, `hd`, `user`, `published`.
- **Actual:** `app/services/user.py:88-107` -- Identity is created, but:
  - Stored at `/auth/identities/{blake2s_hash}` (line 29), NOT at `/u/<user-key>/idents/<provider>`.
  - Uses `attributedTo` instead of `user` to link back to the Person.
  - Stores raw `claims` dict instead of individual fields like `provider`, `sub`, `email`, `hd`.
  - Missing `provider` field -- the provider is not extracted or stored separately.
  - The `@context` extension namespace uses `"https://example.org/ns/"` (placeholder) instead of `"https://<host>/ns/"`.

### 2. Structlog middleware for request logging

- **Spec:** "Structlog middleware logs all requests with method, path, status, and user-id."
- **Actual:** `app/middleware/logging.py:1-59` -- The `LoggingMiddleware` class is fully implemented and logs `method`, `path`, `status`, `duration_ms`, and optionally `user_id`.
- **Problem:** It is commented out in `app/main.py:30` and therefore NOT active. The middleware exists but is disabled.

### 3. ID normalization

- **Spec:** "All IDs are normalized (scheme, trailing slash, etc.)"
- **Actual:** `app/middleware/normalize.py:1-88` -- `NormalizeMiddleware` is implemented (strips trailing slashes from IDs in JSON responses).
- **Problem:** Commented out in `app/main.py:31`. Disabled.
- **Note:** The normalization only handles trailing slashes, not scheme normalization as the spec mentions.

### 4. Generic path resolver `/u/<user-key>/{path:path}`

- **File:** `app/api/query.py:12-43`
- Partially implemented but has critical bugs:
  - **Syntax error** on line 49: `if not ` is incomplete, making the entire file fail to import. This means the application **cannot start**.
  - `store` variable used on line 17 before the `async with ActivityStore() as store:` block on line 19 (`NameError`).
  - `has_read_access` (lines 53-65) has no `return` for the false case.
  - `populate_collection` (lines 69-76) is stub code with `pass` statements; never actually populates anything.
  - On line 27, when `user` is `None` (unauthenticated), `user["id"]` raises `TypeError`.

### 5. Namespace objects

- **Spec:** "Stored under `/ns/<TypeName>`, used for defining and referencing custom object types."
- **Actual:** `app/services/bootstrap.py:5-50` defines namespace and Identity type creation, but the function starts with `return` on line 6, making all the code unreachable. The bootstrap system is dead code.

### 6. Pydantic models

- **File:** `app/models/__init__.py:1-57`
- `Person`, `Identity`, `Collection`, `OrderedCollection` are defined but never imported or used anywhere in the application. All endpoints work with raw dicts.

---

## Not Implemented

### 1. `POST /auth/login` endpoint

- **Spec:** "Receives a Google OAuth JWT, verifies token, resolves or creates User and Identity, returns User, sets secure httpOnly cookie."
- **Actual:** No `/auth/login` route exists. There is a deprecated file `app/middleware/firebase_auth.py` with stub code for `/auth` POST/DELETE routes, but these are broken and unused. Auth is handled only through Bearer tokens in request headers; there is no login endpoint that sets cookies.

### 2. Cookie-based authentication

- **Spec:** "Only one secure cookie or bearer token required for auth" and "Sets secure httpOnly cookie with JWT."
- **Actual:** Only Bearer token auth is implemented (`app/api/auth.py`). Session cookie settings exist in `app/core/settings.py:12-17` but are never used. No cookie is ever set or read.

### 3. Background processing task loop

- **Spec:** "Background task loops continuously, calling `bus.process_next()`" and "Starts background task loop on boot."
- **Actual:** No background task, no startup event, no `process_next()` call anywhere. Activities are submitted to the bus via `ActivityBus.submit()` on outbox POST, but there is no continuous processing loop.

### 4. User and system collections auto-creation

- **Spec:** "User and system collections are created automatically if missing."
- **Actual:** User inbox/outbox are created in `app/services/user.py:63-83` when a user is first created. However, there is no general "auto-create if missing" behavior for arbitrary collections. System collections (like `/ns`) are in the disabled bootstrap code.

### 5. No tracking metadata

- **Spec:** "No tracking metadata (e.g., IP, user-agent)."
- **Actual:** This is technically "implemented" by absence -- no tracking metadata is stored. However, there is no explicit filtering or policy enforcement to prevent it.

---

## Deviations

### 1. Identity storage path

- **Spec:** `/u/<user-key>/idents/<provider>`
- **Actual:** `/auth/identities/{blake2s_hash}` (`app/services/user.py:29`)

### 2. Identity object structure

- **Spec:** Fields `provider`, `sub`, `email`, `name`, `picture`, `hd`, `user`, `published`
- **Actual:** Fields `attributedTo` (instead of `user`), `claims` (raw dict instead of individual fields), `image` (instead of `picture`), `name`, `published`. Missing: `provider`, `sub`, `email`, `hd` as top-level fields.

### 3. Identity `@context` namespace

- **Spec:** `["https://www.w3.org/ns/activitystreams", "https://<host>/ns/"]`
- **Actual:** `["https://www.w3.org/ns/activitystreams", {"activity-serve": "https://example.org/ns/"}]` (`app/services/user.py:92-95`)

### 4. Admin endpoint auth

- **Spec:** "Public placeholder HTML admin UI" (public).
- **Actual:** The endpoint is public (no auth required), which matches the spec. However, the test in `tests/test_admin.py:6` sends auth headers, and the `User` import in `app/api/admin.py:3` is unused, suggesting auth was intended at some point.

### 5. GET outbox is public in spec, but not fully public in implementation

- **Spec:** "GET: Publicly fetch paged outbox activities from Activity Store."
- **Actual:** `app/api/user.py:35-53` -- The GET outbox endpoint does not require auth (no `User` or `UserMaybe` dependency), so it is effectively public. This matches the spec.

### 6. GET inbox spec says public, implementation uses `UserMaybe`

- **Spec:** "GET: Publicly fetch paged inbox activities from Activity Store."
- **Actual:** `app/api/user.py:22-32` -- Injects `UserMaybe` but never uses it for access control. Effectively public, but the `UserMaybe` dependency means an invalid auth header will cause a 401 (rather than being ignored).

### 7. `get_or_create_user` type annotation

- **File:** `app/services/user.py:110`
- Signature says `claims: str` but the body treats it as a `dict` (calls `.get("sub")`).

### 8. `parse_auth_token` return type annotation

- **File:** `app/api/auth.py:24`
- Signature says `-> str` but returns a tuple `(scheme, token)`.

### 9. Bearer scheme check is case-sensitive

- **File:** `app/api/auth.py:30`
- `scheme != "Bearer"` rejects `bearer` (lowercase). RFC 7235 requires case-insensitive comparison.

### 10. Firebase `initialize_app()` at import time

- **File:** `app/services/firebase.py:4`
- Runs at module level. If Firebase credentials are not configured, the import chain crashes. This is not mentioned in the spec and creates a hard dependency on Firebase configuration even for development.

---

## Implementation Beyond Spec

### 1. GET `/me` endpoint

- **File:** `app/api/user.py:14-19`
- Returns the authenticated user's Person object. Not mentioned in the spec.

### 2. GET `/u/{user_key}/{path:path}` generic query endpoint

- **File:** `app/api/query.py:12-43`
- A catch-all path resolver for arbitrary user sub-paths. The spec only mentions inbox and outbox, not a generic query endpoint. (This endpoint is broken and non-functional, but it represents design intent beyond the spec.)

### 3. `has_audience` access control function

- **File:** `app/api/query.py:79-99`
- Checks whether a user matches an audience property, including support for `Public`, `as:Public`, and `https://www.w3.org/ns/activitystreams#Public`. Not mentioned in the spec.

### 4. Stock token system for testing

- **File:** `app/api/auth.py:9-13`
- `_STOCK_TOKENS` dict with `add_stock_token()` function provides a token bypass. No environment guard limits it to test/dev.

### 5. `package.json` / frontend tooling

- **File:** `package.json`
- Bun-based TypeScript setup with `zero-md` dependency and `ui/index.ts` entry point. Not mentioned in the spec.

### 6. Pydantic models

- **File:** `app/models/__init__.py`
- `ActivityBase`, `Person`, `Identity`, `Collection`, `OrderedCollection` models are defined. The spec describes object types but does not specify Pydantic validation models. These models are unused.

### 7. `EZTestClient` in conftest

- **File:** `conftest.py:70-74`
- Custom test client subclass that accepts `PurePosixPath` URLs. Testing infrastructure beyond spec scope.

---

## Summary Table

| Spec Feature | Status | Notes |
|---|---|---|
| GET `/u/<key>/outbox` | Implemented | `app/api/user.py:35-53` |
| POST `/u/<key>/outbox` | Implemented | `app/api/user.py:56-86` |
| GET `/u/<key>/inbox` | Implemented | `app/api/user.py:22-32` |
| POST `/auth/login` | Not Implemented | No login endpoint exists |
| GET `/admin` | Implemented | `app/api/admin.py:8-51` |
| GET `/healthz` | Implemented | `app/api/health.py:7-10` |
| User (Person) type | Implemented | `app/services/user.py:32-85` |
| Identity type | Partially Implemented | Wrong path, wrong fields |
| Namespace objects | Not Implemented | Bootstrap disabled |
| Background worker | Not Implemented | No processing loop |
| Cookie-based auth | Not Implemented | Settings exist, never used |
| Bearer token auth | Implemented | `app/api/auth.py` |
| Structlog logging middleware | Partially Implemented | Code exists, disabled |
| ID normalization middleware | Partially Implemented | Code exists, disabled |
| CORS `*` default | Implemented | `app/main.py:21-27` |
| Docker deployment | Implemented | `Dockerfile` |
| Pydantic BaseSettings config | Implemented | `app/core/settings.py` |
| Actor injection + validation | Implemented | `app/api/user.py:74-79` |
| ID generation if missing | Implemented | `app/api/user.py:82-83` |
| Idempotent overwrites | Implemented | Via activity-store |
| Auto-create collections | Partially Implemented | Only on user creation |
