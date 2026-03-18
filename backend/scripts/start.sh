#!/bin/bash
# Startup script for the backend service
# Runs migrations (if any) then starts uvicorn
set -e

echo "Starting WWTG Backend..."

# Wait for dependencies
python -c "import time; time.sleep(2)"  # Simple wait for DB/Redis

# Create logs directory
mkdir -p logs

# Start server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
