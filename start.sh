#!/bin/bash

# Subtitle Generator MVP Startup Script

echo "🎬 Starting Subtitle Generator MVP..."
echo "=================================="

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or not in PATH"
    exit 1
fi

echo "✅ Python found: $(python --version)"

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  No virtual environment detected. Creating one..."
    
    # Create virtual environment
    python -m venv venv
    
    # Activate virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    echo "✅ Virtual environment created and activated"
else
    echo "✅ Virtual environment already active: $VIRTUAL_ENV"
fi

# Install requirements
echo "📦 Installing requirements..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install requirements"
    exit 1
fi

echo "✅ Requirements installed successfully"

# Check if FFmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg not found. Please install FFmpeg for video processing."
    echo "   Download from: https://ffmpeg.org/download.html"
    echo "   Or use package manager:"
    echo "     - Windows: winget install FFmpeg"
    echo "     - macOS: brew install ffmpeg"
    echo "     - Ubuntu: sudo apt install ffmpeg"
    echo ""
    echo "❓ Continue anyway? The app will fail if FFmpeg is not available. (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ FFmpeg found: $(ffmpeg -version | head -n1)"
fi

# Create necessary directories
mkdir -p uploads outputs app/templates

# Start the application
echo ""
echo "🚀 Starting Subtitle Generator API server..."
echo "   URL: http://localhost:8000"
echo "   Press Ctrl+C to stop the server"
echo ""

cd app && python main.py
