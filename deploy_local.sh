#!/bin/bash

# Local deployment script for Subtitle Generator (Linux/Mac - No Docker)
set -e

echo "🚀 Deploying Subtitle Generator Locally..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your API keys if needed."
fi

# Create required directories
echo "📁 Creating directories..."
mkdir -p uploads outputs logs

# Start the production script
echo "🚀 Starting Subtitle Generator..."
echo ""
echo "📱 Your subtitle generator will be available at:"
echo "   - Gradio Interface: http://localhost:7860"
echo "   - API Backend: http://localhost:8000"
echo ""
echo "💡 Features available:"
echo "   ✅ Video file upload processing"
echo "   ✅ YouTube URL downloading"
echo "   ✅ Multi-language subtitle generation"
echo "   ✅ Subtitle embedding in video"
echo "   ✅ Audio-only processing option"
echo ""
echo "Press Ctrl+C to stop the services"
echo ""

python start_production.py