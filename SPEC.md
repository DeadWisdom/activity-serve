# Activity Serve - SPEC.md

## Overview

**Activity Serve** is a modular FastAPI application that exposes an HTTP interface to the Activity Bus and Activity Store libraries. It supports ActivityPub-compatible endpoints, secure login via Google OAuth, and a pluggable identity system. The system is idempotent, JSON-LD compliant, and ready for future extensibility.

## Design Goals

- Simple, containerized deployment
- Built on `activity-store` and `activity-bus`
- ActivityPub-compatible inbox/outbox support
- Background processing of submitted activities
- HTML admin UI shell
- Secure auth via Google OAuth JWTs
- Extensible identity and type systems

---

## Endpoints

### `/u/<user-key>/outbox` (GET, POST)

- **GET**: Publicly fetch paged outbox activities from Activity Store
- **POST**: Submit a new activity

  - Requires auth via JWT or secure cookie
  - Injects `actor` and generates `id` if missing
  - Validates actor matches URL
  - Passes activity to Activity Bus

### `/u/<user-key>/inbox` (GET)

- **GET**: Publicly fetch paged inbox activities from Activity Store

### `/auth/login` (POST)

- Receives a Google OAuth JWT
- Verifies token
- Resolves or creates:

  - A `User` object at `/u/<user-key>`
  - An `Identity` object at `/u/<user-key>/idents/google`

- Returns the `User` object
- Sets secure httpOnly cookie with JWT

### `/admin` (GET)

- Public placeholder HTML admin UI

### `/healthz` (GET)

- Simple liveness check

---

## Object Types

### User (`type: Person`)

- Stored at: `/u/<user-key>`
- Fields:

  - `@context`: `https://www.w3.org/ns/activitystreams`
  - `id`, `type`, `name`, `preferredUsername`, `image`
  - `inbox`, `outbox`
  - `published`

### Identity (`type: Identity`)

- Stored at: `/u/<user-key>/idents/<provider>`
- Fields:

  - `@context`: `["https://www.w3.org/ns/activitystreams", "https://<host>/ns/"]`
  - `id`, `type`, `provider`, `sub`, `email`, `name`, `picture`, `hd`, `user`, `published`

### Namespace Objects

- Stored under `/ns/<TypeName>`
- Used for defining and referencing custom object types

---

## Behaviors

- Activities are stored and enqueued immediately via Activity Bus
- Background task loops continuously, calling `bus.process_next()`
- User and system collections are created automatically if missing
- All IDs are normalized (scheme, trailing slash, etc.)
- Auth required for POST to outbox; actor must match URL
- Structlog middleware logs all requests with method, path, status, and user-id
- Only one secure cookie or bearer token required for auth
- No tracking metadata (e.g., IP, user-agent)
- Overwrites allowed for existing IDs (idempotent design)

---

## Configuration

Via Pydantic `BaseSettings`, with `.env` support:

- `ACTIVITY_SERVE_BASE_URL` (optional)
- `ACTIVITY_STORE_BACKEND` (default: memory)
- `ACTIVITY_STORE_CACHE` (default: memory)
- `ELASTICSEARCH_URL`, `REDIS_URL` if backends used

---

## Logging

- Uses `structlog`
- Logs all HTTP requests
- Structured logging with `method`, `path`, `status`, `duration`, optional `user_id`

---

## Deployment

- Modular FastAPI app structure
- Runs as a Docker container
- Starts background task loop on boot
- Public, CORS-`*` by default
- Does not handle remote delivery (yet)
