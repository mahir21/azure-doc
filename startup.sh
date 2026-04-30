#!/usr/bin/env bash
set -e

# App Service sets PORT. Default locally if missing.
export PORT="${PORT:-8000}"

exec gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:$PORT main:app
