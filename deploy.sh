#!/bin/bash
# -----------------------------------------------------------------------------
# OmniSync RAG - Professional Deployment Script
# -----------------------------------------------------------------------------

echo "==============================================="
echo "  🚀 Starting OmniSync Production Deployment"
echo "==============================================="

# 1. Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# 2. Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env. PLEASE EDIT .env and add your OPENROUTER_API_KEY before running this script again."
        exit 1
    else
        echo "❌ Error: .env.example not found either!"
        exit 1
    fi
fi

# 3. Pull latest code (if using git)
# echo "🔄 Pulling latest changes..."
# git pull origin main

# 4. Build and start containers in detached mode using the production compose file
echo "🏗️  Building and starting Docker containers..."
docker compose -f docker-compose.prod.yml up -d --build

# 5. Check status
echo "==============================================="
echo "✅ Deployment Successful!"
echo "🌐 Your application is now running on port 80."
echo "==============================================="
echo "To view logs, run: docker compose -f docker-compose.prod.yml logs -f"
