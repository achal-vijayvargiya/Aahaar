#!/bin/bash

# Database Import Script
# Imports data from local PostgreSQL database to Docker container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration - EDIT THESE VALUES
LOCAL_DB_HOST="${LOCAL_DB_HOST:-localhost}"
LOCAL_DB_PORT="${LOCAL_DB_PORT:-5432}"
LOCAL_DB_USER="${LOCAL_DB_USER:-postgres}"
LOCAL_DB_NAME="${LOCAL_DB_NAME:-drassistent}"
DOCKER_CONTAINER="${DOCKER_CONTAINER:-drassistent-db}"
DOCKER_DB_NAME="${DOCKER_DB_NAME:-drassistent}"
DOCKER_DB_USER="${DOCKER_DB_USER:-postgres}"

# Backup file name with timestamp
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
DUMP_FORMAT="${DUMP_FORMAT:-plain}"  # plain or custom

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Database Import Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Docker container is running
echo -e "${YELLOW}[1/5] Checking Docker container...${NC}"
if ! docker ps | grep -q "$DOCKER_CONTAINER"; then
    echo -e "${RED}Error: Docker container '$DOCKER_CONTAINER' is not running!${NC}"
    echo "Start it with: docker-compose up -d db"
    exit 1
fi
echo -e "${GREEN}✓ Docker container is running${NC}"
echo ""

# Check if local database is accessible
echo -e "${YELLOW}[2/5] Checking local database connection...${NC}"
if ! pg_isready -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -U "$LOCAL_DB_USER" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to local database!${NC}"
    echo "Please check:"
    echo "  - Database is running"
    echo "  - Host: $LOCAL_DB_HOST"
    echo "  - Port: $LOCAL_DB_PORT"
    echo "  - User: $LOCAL_DB_USER"
    exit 1
fi
echo -e "${GREEN}✓ Local database is accessible${NC}"
echo ""

# Export from local database
echo -e "${YELLOW}[3/5] Exporting from local database...${NC}"
if [ "$DUMP_FORMAT" = "custom" ]; then
    BACKUP_FILE="${BACKUP_FILE%.sql}.dump"
    pg_dump -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" -F c -f "$BACKUP_FILE"
else
    pg_dump -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" -f "$BACKUP_FILE"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file was not created!${NC}"
    exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo -e "${GREEN}✓ Backup created: $BACKUP_FILE (${BACKUP_SIZE})${NC}"
echo ""

# Copy to Docker container
echo -e "${YELLOW}[4/5] Copying backup to Docker container...${NC}"
docker cp "$BACKUP_FILE" "$DOCKER_CONTAINER:/tmp/$BACKUP_FILE"
echo -e "${GREEN}✓ Backup copied to container${NC}"
echo ""

# Import into Docker database
echo -e "${YELLOW}[5/5] Importing into Docker database...${NC}"
echo "This may take a while depending on database size..."
echo ""

if [ "$DUMP_FORMAT" = "custom" ]; then
    docker exec -i "$DOCKER_CONTAINER" pg_restore -U "$DOCKER_DB_USER" -d "$DOCKER_DB_NAME" -c "/tmp/$BACKUP_FILE"
else
    docker exec -i "$DOCKER_CONTAINER" psql -U "$DOCKER_DB_USER" -d "$DOCKER_DB_NAME" -f "/tmp/$BACKUP_FILE"
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Import completed successfully!${NC}"
else
    echo -e "${RED}✗ Import failed!${NC}"
    exit 1
fi
echo ""

# Cleanup
echo -e "${YELLOW}Cleaning up...${NC}"
docker exec "$DOCKER_CONTAINER" rm -f "/tmp/$BACKUP_FILE"
rm -f "$BACKUP_FILE"
echo -e "${GREEN}✓ Cleanup completed${NC}"
echo ""

# Verify import
echo -e "${YELLOW}Verifying import...${NC}"
docker exec -i "$DOCKER_CONTAINER" psql -U "$DOCKER_DB_USER" -d "$DOCKER_DB_NAME" -c "
SELECT 
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC
LIMIT 10;
"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Import completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
