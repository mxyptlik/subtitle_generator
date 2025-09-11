@echo off
REM Subtitle Generator MVP Startup Script for Windows

echo 🎬 Starting Subtitle Generator MVP...
echo ==================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    pause
    exit /b 1
)

echo ✅ Python found
python --version

REM Check if we're in a virtual environment
if "%VIRTUAL_ENV%"=="" (
    echo ⚠️  No virtual environment detected. Creating one...
    
    REM Create virtual environment
    python -m venv venv
    
    REM Activate virtual environment
    call venv\Scripts\activate.bat
    
    echo ✅ Virtual environment created and activated
) else (
    echo ✅ Virtual environment already active: %VIRTUAL_ENV%
)

REM Install requirements
echo 📦 Installing requirements...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install requirements
    pause
    exit /b 1
)

echo ✅ Requirements installed successfully

REM Check if FFmpeg is available
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FFmpeg not found. Please install FFmpeg for video processing.
    echo    Download from: https://ffmpeg.org/download.html
    echo    Or use package manager: winget install FFmpeg
    echo.
    echo ❓ Continue anyway? The app will fail if FFmpeg is not available. (y/n)
    set /p response=
    if /i not "%response%"=="y" exit /b 1
) else (
    echo ✅ FFmpeg found
)

REM Create necessary directories
if not exist uploads mkdir uploads
if not exist outputs mkdir outputs
if not exist app\templates mkdir app\templates

REM Start the application
echo.
echo 🚀 Starting Subtitle Generator API server...
echo    URL: http://localhost:8000
echo    Press Ctrl+C to stop the server
echo.

cd app
python main.py
