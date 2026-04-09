#!/bin/bash
# ZettelForge TypeDB Setup
# Starts TypeDB container and loads STIX 2.1 schema

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== ZettelForge TypeDB Setup ==="

# Start container
echo "[1/3] Starting TypeDB container..."
docker compose -f "$PROJECT_DIR/docker/docker-compose.yml" up -d

# Wait for health
echo "[2/3] Waiting for TypeDB to be ready..."
for i in $(seq 1 30); do
    if docker compose -f "$PROJECT_DIR/docker/docker-compose.yml" exec -T typedb curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "  TypeDB is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ERROR: TypeDB did not become ready in 30s"
        exit 1
    fi
    sleep 1
done

echo "[3/3] TypeDB running on localhost:1729 (gRPC) and localhost:8000 (HTTP)"
echo ""
echo "To load schema:"
echo "  python3 -c 'from zettelforge.typedb_client import TypeDBKnowledgeGraph; kg = TypeDBKnowledgeGraph(); kg._ensure_database(); kg._load_schema()'"
echo ""
echo "To stop:"
echo "  docker compose -f $PROJECT_DIR/docker/docker-compose.yml down"
