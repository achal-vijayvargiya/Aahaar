#!/bin/bash
# Script to create a new Alembic migration

if [ -z "$1" ]; then
    echo "Usage: ./create_migration.sh \"migration message\""
    exit 1
fi

echo "Creating new migration: $1"
alembic revision --autogenerate -m "$1"

echo "Migration created successfully!"
echo "Review the migration file in alembic/versions/"
echo "Then run: alembic upgrade head"

