#!/bin/bash
set -e

# CXR Triage System - Startup Script

echo "=========================================="
echo "CXR Triage System - Starting Services"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    if ! docker compose version &> /dev/null; then
        echo "Error: docker-compose is not installed."
        exit 1
    fi
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p data/uploads data/exports models nginx/ssl

# Check if models exist
if [ ! -f "models/densenet121-res224-all.pth" ]; then
    echo ""
    echo "WARNING: AI models not found!"
    echo "Run: python scripts/download_models.py"
    echo ""
    read -p "Continue without models? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Generate encryption key if not set
if [ -z "$ENCRYPTION_KEY" ]; then
    export ENCRYPTION_KEY=$(openssl rand -base64 32)
    echo "Generated new ENCRYPTION_KEY"
fi

# Generate secret key if not set
if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY=$(openssl rand -hex 32)
    echo "Generated new SECRET_KEY"
fi

# Build and start services
echo ""
echo "Building and starting services..."
$COMPOSE_CMD up --build -d

# Wait for services to be healthy
echo ""
echo "Waiting for services to start..."
sleep 10

# Check service health
echo ""
echo "Checking service health..."

check_service() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo "  ✓ $name is healthy"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "  ✗ $name failed to start"
    return 1
}

check_service "Backend API" "http://localhost:8000/health"
check_service "Inference Service" "http://localhost:8001/health"
check_service "Frontend" "http://localhost:3000"

echo ""
echo "=========================================="
echo "CXR Triage System is ready!"
echo "=========================================="
echo ""
echo "Access the application at:"
echo "  - Frontend:   http://localhost:3000"
echo "  - Backend:    http://localhost:8000"
echo "  - API Docs:   http://localhost:8000/docs"
echo "  - Orthanc:    http://localhost:8042"
echo ""
echo "To stop the system:"
echo "  $COMPOSE_CMD down"
echo ""
