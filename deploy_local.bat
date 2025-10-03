@echo off
REM Local deployment script for Subtitle Generator (Windows - No Docker)
echo 🚀 Deploying Subtitle Generator Locally...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.11+ first.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist .venv (
    echo 📦 Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo 📚 Installing dependencies...
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file...
    copy .env.example .env
    echo ✅ .env file created. Please edit it with your API keys if needed.
)

REM Create required directories
echo 📁 Creating directories...
if not exist uploads mkdir uploads
if not exist outputs mkdir outputs
if not exist logs mkdir logs

REM Start the production script
echo 🚀 Starting Subtitle Generator...
echo.
echo 📱 Your subtitle generator will be available at:
echo    - Gradio Interface: http://localhost:7860
echo    - API Backend: http://localhost:8000
echo.
echo 💡 Features available:
echo    ✅ Video file upload processing
echo    ✅ YouTube URL downloading
echo    ✅ Multi-language subtitle generation
echo    ✅ Subtitle embedding in video
echo    ✅ Audio-only processing option
echo.
echo Press Ctrl+C to stop the services
echo.

python start_production.py

pause