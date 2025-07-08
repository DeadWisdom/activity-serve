# Activity Serve - PLAN.md

## Setup & Configuration

1. Scaffold FastAPI project with modular layout ✅
2. Add Pydantic `Settings` class for env var config ✅
3. Initialize ActivityStore and ActivityBus from config ✅
4. Normalize base URL (env var or infer from request) ✅
5. Set up CORS (allow all) ✅

## Routing

6. Create `/u/<user-key>/inbox` and `/outbox` GET endpoints ✅
7. Create `/u/<user-key>/outbox` POST endpoint ✅
   - Verify auth
   - Validate actor ownership
   - Inject `actor`, generate `id`, `published`
   - Pass to `bus.submit()`
8. Create `/auth/login` POST endpoint ✅
   - Verify JWT
   - Look up Identity by `provider=sub`
   - If not found: generate user-key, create User + Identity
   - Store in Activity Store
   - Set secure cookie
   - Return User object
9. Create `/admin` placeholder route (HTML shell) ✅
10. Create `/healthz` route (200 OK JSON) ✅

## Middleware

11. Add request logging middleware (structlog) ✅
12. Add auth middleware (cookie/JWT extraction) ✅
13. Normalize all incoming/outgoing IDs ✅

## Object Bootstrapping

14. On startup: ✅

- Create system collections (`/sys/behaviors`, `/ns`, etc.)
- Register custom types under `/ns/`

15. On first login: ✅

- Generate `user-key` (8-char nanoid)
- Create `/u/<user-key>` User object
- Create `/u/<user-key>/inbox|outbox` collections

## Background Worker

16. Create `background.py` with `bus.process_next()` loop ✅
17. Start it on FastAPI startup event ✅

## Testing & Validation

18. Write unit tests using FastAPI `TestClient` ✅
19. Use pytest fixtures for mock store/bus ✅
20. Validate Identity lookup/creation, auth guardrails, activity POST flow ✅

## Deployment

21. Write Dockerfile ✅
22. Add requirements.txt with activity-store\[es,redis], activity-bus, FastAPI, structlog ✅
23. Optional: include example `.env` file ✅
