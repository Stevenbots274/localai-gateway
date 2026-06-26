#!/bin/bash
set -e

echo "Starting LocalAI Gateway..."

# Run database migrations if alembic is available
if command -v alembic &> /dev/null; then
    echo "Running database migrations..."
    alembic upgrade head || echo "Migration skipped (tables will be auto-created)"
fi

# Start the FastAPI application
echo "Starting Uvicorn server..."
exec uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --access-log \
    --proxy-headers
