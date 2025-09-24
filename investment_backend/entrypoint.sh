#!/bin/bash
set -e

# Use PGPASSWORD for automatic authentication
export PGPASSWORD="$POSTGRES_PASSWORD"

echo "Waiting for PostgreSQL..."
until pg_isready -h "$POSTGRES_HOST" -p 5432 -U "$POSTGRES_USER"; do
  sleep 2
done
echo "PostgreSQL is ready"

# Only create tables if the investments table does not exist
TABLE_EXISTS=$(psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$INVESTMENTS_DB" -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='investments'")
if [ "$TABLE_EXISTS" != "1" ]; then
    echo "Creating tables..."
    python3 backend/create_tables.py
else
    echo "Tables already exist, skipping creation"
fi

# Start FastAPI backend in the background
echo "Starting FastAPI backend..."
uvicorn backend.main:investment_api --host 0.0.0.0 --port 3337 --reload &

# Start Next.js frontend in the foreground
echo "Starting Next.js frontend..."
npm --prefix frontend run start
