#!/bin/bash

# Deployment script for Subtitle Generator
set -e

echo "🚀 Deploying Subtitle Generator with YouTube Support..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# OpenAI API Key (optional - for translation features)
OPENAI_API_KEY=your_openai_api_key_here

# Environment
NODE_ENV=production

# Logging
LOG_LEVEL=info
EOF
    echo "✅ .env file created. Please edit it with your API keys if needed."
fi

# Create required directories
echo "📁 Creating directories..."
mkdir -p uploads outputs logs ssl

# Build and start services
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ FastAPI backend is healthy"
else
    echo "❌ FastAPI backend health check failed"
    docker-compose logs subtitle-generator
    exit 1
fi

if curl -f http://localhost:7860 > /dev/null 2>&1; then
    echo "✅ Gradio frontend is accessible"
else
    echo "⚠️ Gradio frontend may still be starting up"
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📱 Access your subtitle generator:"
echo "   - Gradio Interface: http://localhost:7860"
echo "   - API Backend: http://localhost:8000"
echo "   - API Documentation: http://localhost:8000/docs"
echo ""
echo "🔧 Management commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Stop services: docker-compose down"
echo "   - Restart: docker-compose restart"
echo ""
echo "💡 Features available:"
echo "   ✅ Video file upload processing"
echo "   ✅ YouTube URL downloading"
echo "   ✅ Multi-language subtitle generation"
echo "   ✅ Subtitle embedding in video"
echo "   ✅ Audio-only processing option"
echo ""

# Show running containers
echo "🐳 Running containers:"
docker-compose ps