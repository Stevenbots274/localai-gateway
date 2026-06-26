#!/bin/bash
set -e

echo "=== LocalAI Gateway Deployment Script ==="

# Check prerequisites
command -v flyctl >/dev/null 2>&1 || { echo "flyctl is required. Install: https://fly.io/docs/hands-on/install-flyctl/"; exit 1; }

# Set secrets from .env if it exists
if [ -f .env ]; then
    echo "Setting Fly.io secrets from .env..."
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        # Trim whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        if [ -n "$key" ] && [ -n "$value" ]; then
            echo "Setting $key..."
            flyctl secrets set "${key}=${value}" --app localai-gateway || true
        fi
    done < .env
fi

# Deploy
echo "Deploying to Fly.io..."
flyctl deploy --app localai-gateway

echo "Deployment complete!"
echo "Visit: https://localai-gateway.fly.dev"
