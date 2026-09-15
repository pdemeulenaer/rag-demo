#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🚀 Starting Hybrid RAG Stack verification..."

# 1. Build and Start
# docker compose up -d --build
make compose

echo "⏳ Waiting for containers to become healthy (this may take 30-60s)..."

# 2. Function to check health status
check_status() {
    docker inspect --format='{{.State.Health.Status}}' "$1" 2>/dev/null
}

# 3. Wait Loop
MAX_RETRIES=12
COUNT=0
SERVICES=("redis" "api" "ingestion-worker")

while [ $COUNT -lt $MAX_RETRIES ]; do
    ALL_HEALTHY=true
    for SERVICE in "${SERVICES[@]}"; do
        STATUS=$(check_status "rag-solution-$SERVICE-1") # Adjust prefix if your folder name differs
        if [ "$STATUS" != "healthy" ]; then
            ALL_HEALTHY=false
            echo " - $SERVICE is still: ${STATUS:-starting}"
        fi
    done

    if [ "$ALL_HEALTHY" = true ]; then
        echo -e "\n${GREEN}✅ ALL SYSTEMS GO!${NC}"
        echo "---------------------------------------"
        echo "Frontend: http://localhost:8501"
        echo "Backend Health: http://localhost:8000/health"
        echo "---------------------------------------"
        exit 0
    fi

    sleep 5
    ((COUNT++))
done

echo -e "\n${RED}❌ Timeout reached. Some services are not healthy.${NC}"
docker compose ps
exit 1