@echo off
echo Starting Subtitle Generator MVP...

REM Check if we're in the right directory
if not exist "app\main.py" (
    echo Error: Please run this script from the subtitle_generator directory
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo Virtual environment activated
)

REM Install packages if needed
echo Installing/checking requirements...
pip install fastapi uvicorn openai-whisper ffmpeg-python python-multipart jinja2 aiofiles

REM Start the server
echo.
echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop
echo.
cd app
python main.py

pause
