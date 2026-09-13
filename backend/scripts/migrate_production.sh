#!/bin/bash
# Production migration script for Render
# Run this as a one-off job or release command

set -e

echo "==================================="
echo "Running Aahaar Database Migrations"
echo "==================================="

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL environment variable is not set"
    exit 1
fi

echo "Database URL: ${DATABASE_URL:0:30}... (truncated)"
echo ""

# Run Alembic migrations
echo "Running Alembic migrations..."
cd /app
alembic upgrade head

echo ""
echo "Migration completed successfully!"
echo "==================================="
