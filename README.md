# LocalAI Gateway

An OpenAI-compatible API gateway built with FastAPI, deployed on Fly.io, with Neon PostgreSQL for API key management and usage tracking. Proxies all requests to a LocalAI backend.

## Features

- **OpenAI-compatible API** (`/v1/chat/completions`, `/v1/embeddings`, `/v1/audio/*`, `/v1/images/*`, etc.)
- **API Key Management** with Neon PostgreSQL (create, revoke, rate limit per key)
- **Usage Tracking** (requests, tokens, latency per endpoint)
- **Rate Limiting** (token bucket per API key)
- **Admin Dashboard** endpoints for monitoring
- **Streaming Support** for chat completions
- **Multi-file Upload** support (audio, images, files)

## Architecture

```
Client → Fly.io (FastAPI Gateway) → LocalAI Backend
              ↓
         Neon PostgreSQL (API Keys + Usage Logs)
```

## Quick Start

### 1. Set up Neon Database

1. Go to [neon.tech](https://neon.tech) and create a new project
2. Get your connection string (both pooled and direct)
3. Copy `.env.example` to `.env` and fill in:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host.neon.tech/dbname?sslmode=require
DATABASE_URL_SYNC=postgresql+psycopg2://user:pass@host.neon.tech/dbname?sslmode=require
SECRET_KEY=your-super-secret-key-min-32-chars
ADMIN_API_KEY=your-admin-master-key
LOCALAI_URL=http://your-localai-server:8080
```

### 2. Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
./scripts/start.sh
```

### 3. Deploy to Fly.io

```bash
# Install flyctl if not already
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Create app
flyctl apps create localai-gateway

# Set secrets
flyctl secrets set DATABASE_URL="your-neon-url"   DATABASE_URL_SYNC="your-neon-sync-url"   SECRET_KEY="your-secret"   ADMIN_API_KEY="your-admin-key"   LOCALAI_URL="http://your-localai:8080"

# Deploy
flyctl deploy
```

Or use the deploy script:
```bash
./scripts/deploy.sh
```

## API Usage

### Create an API Key (Admin only)
```bash
curl -X POST https://your-app.fly.dev/auth/keys \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-app","rate_limit_per_minute":120}'
```

### Use the API Key
```bash
# Chat completions
curl -X POST https://your-app.fly.dev/v1/chat/completions \
  -H "Authorization: Bearer localai_xxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role":"user","content":"Hello!"}]
  }'

# Or use X-API-Key header
curl -X POST https://your-app.fly.dev/v1/chat/completions \
  -H "X-API-Key: localai_xxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"Hello!"}]}'
```

### Supported Endpoints

All endpoints require API key authentication via `Authorization: Bearer <key>` or `X-API-Key: <key>`.

| Endpoint | Description |
|----------|-------------|
| `GET /v1/models` | List available models |
| `POST /v1/chat/completions` | Chat completions (streaming supported) |
| `POST /v1/completions` | Legacy completions |
| `POST /v1/embeddings` | Text embeddings |
| `POST /v1/audio/transcriptions` | Speech-to-text |
| `POST /v1/audio/translations` | Audio translation |
| `POST /v1/audio/speech` | Text-to-speech |
| `POST /v1/images/generations` | Image generation |
| `POST /v1/images/edits` | Image editing |
| `POST /v1/files` | File upload |
| `GET /v1/files` | List files |
| `POST /v1/assistants` | Create assistant |
| `POST /v1/threads` | Create thread |
| `POST /v1/fine_tuning/jobs` | Fine-tuning |

### Admin Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /admin/health` | System health check |
| `GET /admin/usage/stats` | Usage statistics |
| `GET /admin/usage/logs` | Recent request logs |
| `GET /admin/localai/models` | LocalAI model list |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Neon async connection string | Required |
| `DATABASE_URL_SYNC` | Neon sync connection string | Required |
| `SECRET_KEY` | JWT signing key | Required |
| `ADMIN_API_KEY` | Master admin key | Required |
| `LOCALAI_URL` | LocalAI server URL | `http://localhost:8080` |
| `LOCALAI_API_KEY` | LocalAI auth key (optional) | "" |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Default rate limit | 60 |
| `RATE_LIMIT_BURST` | Default burst limit | 10 |
| `MAX_UPLOAD_SIZE` | Max file upload bytes | 100MB |

## License

MIT
