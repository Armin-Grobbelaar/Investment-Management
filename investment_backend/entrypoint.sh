#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
python3 -c "
import psycopg2, time, os
host = os.environ.get('POSTGRES_HOST', 'localhost')
port = int(os.environ.get('POSTGRES_PORT', '5432'))
user = os.environ.get('POSTGRES_USER', 'postgres')
pwd = os.environ.get('POSTGRES_PASSWORD', 'changeme')
db = os.environ.get('INVESTMENTS_DB', 'investments_app')

for _ in range(30):
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=pwd, dbname='postgres')
        conn.close()
        print('PostgreSQL engine is ready')
        break
    except Exception as e:
        print('Waiting for DB connection...', str(e))
        time.sleep(2)
"

echo "Initializing central multi-tenant database..."
python3 create_central_db.py

# Start FastAPI backend in the background
echo "Starting FastAPI backend..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
(
    while true; do
        if uvicorn investment_backend_fastapi:investment_api --host 0.0.0.0 --port 3337; then
            echo "[entrypoint] Backend stopped cleanly, restarting in 5 seconds..."
        else
            code=$?
            echo "[entrypoint] Backend crashed (exit code $code), restarting in 5 seconds..."
        fi
        sleep 5
    done
) &

# Start Next.js frontend in the foreground
echo "Starting Next.js frontend..."
if [ -f "frontend/server.js" ]; then
    cd frontend && node server.js
else
    npm --prefix frontend run start
fi
