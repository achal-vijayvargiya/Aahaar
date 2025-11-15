#!/bin/bash
# Startup script for the DrAssistent API

echo "Starting DrAssistent API..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Initialize database with sample data if needed
echo "Initializing database..."
python scripts/init_db.py

# Start the application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

