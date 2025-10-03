@echo off
REM Deployment script for Subtitle Generator (Windows)
echo 🚀 Deploying Subtitle Generator with YouTube Support...

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file...
    (
        echo # OpenAI API Key (optional - for translation features^)
        echo OPENAI_API_KEY=your_openai_api_key_here
        echo.
        echo # Environment
        echo NODE_ENV=production
        echo.
        echo # Logging
        echo LOG_LEVEL=info
    ) > .env
    echo ✅ .env file created. Please edit it with your API keys if needed.
)

REM Create required directories
echo 📁 Creating directories...
if not exist uploads mkdir uploads
if not exist outputs mkdir outputs
if not exist logs mkdir logs
if not exist ssl mkdir ssl

REM Build and start services
echo 🔨 Building Docker image...
docker-compose build

echo 🚀 Starting services...
docker-compose up -d

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 15 /nobreak >nul

REM Check service health
curl -f http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo ❌ FastAPI backend health check failed
    docker-compose logs subtitle-generator
    pause
    exit /b 1
) else (
    echo ✅ FastAPI backend is healthy
)

curl -f http://localhost:7860 >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Gradio frontend may still be starting up
) else (
    echo ✅ Gradio frontend is accessible
)

echo.
echo 🎉 Deployment completed successfully!
echo.
echo 📱 Access your subtitle generator:
echo    - Gradio Interface: http://localhost:7860
echo    - API Backend: http://localhost:8000
echo    - API Documentation: http://localhost:8000/docs
echo.
echo 🔧 Management commands:
echo    - View logs: docker-compose logs -f
echo    - Stop services: docker-compose down
echo    - Restart: docker-compose restart
echo.
echo 💡 Features available:
echo    ✅ Video file upload processing
echo    ✅ YouTube URL downloading
echo    ✅ Multi-language subtitle generation
echo    ✅ Subtitle embedding in video
echo    ✅ Audio-only processing option
echo.

REM Show running containers
echo 🐳 Running containers:
docker-compose ps

pause