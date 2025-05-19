# Activity Serve

A modular FastAPI application that exposes an HTTP interface to the Activity Bus and Activity Store libraries. It supports ActivityPub-compatible endpoints, secure login via Google OAuth, and a pluggable identity system.

## Features

- ActivityPub-compatible inbox/outbox support
- Background processing of submitted activities
- Simple, containerized deployment
- HTML admin UI shell
- Secure auth via Google OAuth JWTs
- Extensible identity and type systems

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/activity-serve.git
cd activity-serve

# Install dependencies using uv
uv pip install -e .
```

## Configuration

Create a `.env` file in the root directory with the following variables:

```
ACTIVITY_SERVE_BASE_URL=http://localhost:8000
ACTIVITY_STORE_BACKEND=memory  # or elasticsearch
ACTIVITY_STORE_CACHE=memory  # or redis
ELASTICSEARCH_URL=http://localhost:9200  # if using elasticsearch backend
REDIS_URL=redis://localhost:6379  # if using redis cache
JWT_SECRET_KEY=your-secret-key
GOOGLE_CLIENT_ID=your-google-client-id
```

## Running the server

```bash
# Development mode
python run.py

# Or with uvicorn directly
uvicorn app.main:app --reload
```

## Testing

```bash
# Run tests
pytest
```

## API Endpoints

- `/u/<user-key>/inbox` (GET): Fetch paged inbox activities
- `/u/<user-key>/outbox` (GET, POST): Fetch or submit outbox activities
- `/auth/login` (POST): Authenticate with Google OAuth JWT
- `/admin` (GET): Simple admin UI shell
- `/healthz` (GET): Health check endpoint

## License

MIT