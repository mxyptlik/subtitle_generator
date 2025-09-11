from fastapi import FastAPI, File, UploadFile, HTTPException, Request, BackgroundTasks, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import uuid
import json
import time
from pathlib import Path
from typing import Dict, Optional
import aiofiles
import logging

from .video_processor import VideoProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Subtitle Generator", description="AI-powered video subtitle generator")

# Get the current directory and set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

logger.info(f"Current directory: {current_dir}")
logger.info(f"Project root: {project_root}")

# Initialize templates - check if running from app directory or project root
templates_path = os.path.join(current_dir, "templates")
if os.path.exists(templates_path):
    # Running from app directory or project root - templates are in app/templates
    logger.info(f"Using templates from: {templates_path}")
    templates = Jinja2Templates(directory=templates_path)
    UPLOAD_DIR = os.path.join(project_root, "uploads")
    OUTPUT_DIR = os.path.join(project_root, "outputs")
else:
    # Fallback - try relative path
    logger.info("Using fallback template path: app/templates")
    templates = Jinja2Templates(directory="app/templates")
    UPLOAD_DIR = "uploads"
    OUTPUT_DIR = "outputs"

# Initialize video processor
try:
    processor = VideoProcessor(model_name="base")
    
    # Check if FFmpeg is available
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("FFmpeg is available and working")
        else:
            logger.warning("FFmpeg found but not working properly")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        logger.error("⚠️ FFmpeg is not installed or not accessible!")
        logger.error("Please install FFmpeg from https://ffmpeg.org/download.html")
        logger.error("Video processing will fail until FFmpeg is installed.")
        
except Exception as e:
    logger.error(f"Failed to initialize VideoProcessor: {e}")
    processor = None

# Storage for processing status
processing_status: Dict[str, Dict] = {}

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    """Serve the main upload page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_video(background_tasks: BackgroundTasks, 
                      file: UploadFile = File(...),
                      embed_subtitles: bool = Form(False),
                      language: str = Form("en")):
    """
    Upload video file and start subtitle generation process.
    
    Args:
        file: Video file to process
        embed_subtitles: Whether to create video with embedded soft subtitles
        language: Language code for subtitles (e.g., 'en', 'es', 'fr')
    
    Returns:
        JSON response with task_id for status checking
    """
    
    logger.info(f"=== UPLOAD REQUEST DEBUG ===")
    logger.info(f"Received language parameter: '{language}'")
    logger.info(f"Embed subtitles: {embed_subtitles}")
    logger.info(f"File: {file.filename}")
    logger.info(f"=== END DEBUG ===")
    logger.info(f"Received language parameter: '{language}'")
    logger.info(f"Embed subtitles: {embed_subtitles}")
    logger.info(f"File: {file.filename}")
    logger.info(f"=== END DEBUG ===")
    
    if not processor:
        raise HTTPException(status_code=500, detail="Video processor not initialized")
    
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in processor.get_supported_formats():
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Supported formats: {', '.join(processor.get_supported_formats())}"
        )
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Save uploaded file
    file_path = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")
    
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Initialize processing status
        processing_status[task_id] = {
            "status": "uploaded",
            "filename": file.filename,
            "file_path": file_path,
            "start_time": time.time(),
            "progress": 0,
            "message": "File uploaded successfully",
            "embed_subtitles": embed_subtitles,
            "language": language
        }
        
        # Start background processing
        background_tasks.add_task(process_video_task, task_id, file_path, embed_subtitles, language)
        
        logger.info(f"File uploaded successfully: {file.filename}, Task ID: {task_id}, Embed: {embed_subtitles}")
        
        return {
            "task_id": task_id,
            "filename": file.filename,
            "status": "uploaded",
            "embed_subtitles": embed_subtitles,
            "language": language,
            "message": "File uploaded successfully. Processing started."
        }
        
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        # Clean up file if it exists
        if os.path.exists(file_path):
            os.unlink(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

async def process_video_task(task_id: str, file_path: str, embed_subtitles: bool = False, language: str = "en"):
    """
    Background task to process video and generate subtitles.
    
    Args:
        task_id: Unique task identifier
        file_path: Path to the uploaded video file
        embed_subtitles: Whether to create video with embedded soft subtitles
        language: Language code for subtitles
    """
    logger.info(f"=== PROCESS TASK DEBUG ===")
    logger.info(f"Task ID: {task_id}")
    logger.info(f"Language received in process_video_task: '{language}'")
    logger.info(f"Embed subtitles: {embed_subtitles}")
    logger.info(f"=== END PROCESS DEBUG ===")
    
    try:
        # Update status to processing
        processing_status[task_id].update({
            "status": "processing",
            "progress": 25,
            "message": "Extracting audio from video..."
        })
        
        logger.info(f"Starting processing for task {task_id} (embed: {embed_subtitles})")
        
        # Generate subtitles (and optionally video with embedded subtitles)
        srt_path, video_path = processor.generate_subtitles_with_video(
            file_path, OUTPUT_DIR, embed_subtitles, language
        )
        
        # Update status to completed
        processing_time = time.time() - processing_status[task_id]["start_time"]
        
        result_data = {
            "status": "completed",
            "progress": 100,
            "message": "Subtitles generated successfully",
            "srt_path": srt_path,
            "srt_filename": os.path.basename(srt_path),
            "processing_time": processing_time
        }
        
        # Add video info if embedding was successful
        if video_path:
            result_data.update({
                "video_path": video_path,
                "video_filename": os.path.basename(video_path),
                "message": "Subtitles and video with embedded subtitles generated successfully"
            })
        
        processing_status[task_id].update(result_data)
        
        logger.info(f"Processing completed for task {task_id}. Time: {processing_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Processing failed for task {task_id}: {e}")
        processing_status[task_id].update({
            "status": "error",
            "progress": 0,
            "message": f"Processing failed: {str(e)}"
        })
    finally:
        # Clean up uploaded video file
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up uploaded file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up uploaded file: {e}")

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """
    Get processing status for a task.
    
    Args:
        task_id: Task identifier
        
    Returns:
        JSON response with current status
    """
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = processing_status[task_id].copy()
    
    # Don't expose internal file paths in the response
    if "file_path" in status:
        del status["file_path"]
    if "subtitle_path" in status:
        del status["subtitle_path"]
    
    return status

@app.get("/download/{task_id}")
async def download_subtitles(task_id: str):
    """
    Download generated subtitle file.
    
    Args:
        task_id: Task identifier
        
    Returns:
        File response with SRT file
    """
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = processing_status[task_id]
    
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Subtitles not ready yet")
    
    if "srt_path" not in status or not os.path.exists(status["srt_path"]):
        raise HTTPException(status_code=404, detail="Subtitle file not found")
    
    srt_path = status["srt_path"]
    filename = status["srt_filename"]
    
    return FileResponse(
        path=srt_path,
        filename=filename,
        media_type="application/x-subrip"
    )

@app.get("/download-video/{task_id}")
async def download_video_with_subtitles(task_id: str):
    """
    Download video file with embedded soft subtitles.
    
    Args:
        task_id: Task identifier
        
    Returns:
        File response with video file containing embedded subtitles
    """
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = processing_status[task_id]
    
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready yet")
    
    if "video_path" not in status or not os.path.exists(status["video_path"]):
        raise HTTPException(status_code=404, detail="Video with subtitles not found or was not requested")
    
    video_path = status["video_path"]
    filename = status["video_filename"]
    
    # Determine media type based on file extension
    file_ext = Path(video_path).suffix.lower()
    media_type_map = {
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska',
        '.wmv': 'video/x-ms-wmv',
        '.flv': 'video/x-flv',
        '.webm': 'video/webm'
    }
    media_type = media_type_map.get(file_ext, 'video/mp4')
    
    return FileResponse(
        path=video_path,
        filename=filename,
        media_type=media_type
    )

@app.get("/health")
async def health_check():
    """Health check endpoint with system requirements status."""
    import subprocess
    
    # Check FFmpeg availability
    ffmpeg_status = False
    ffmpeg_version = "Not installed"
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            ffmpeg_status = True
            # Extract version from first line
            first_line = result.stdout.split('\n')[0]
            ffmpeg_version = first_line.split(' ')[2] if len(first_line.split(' ')) > 2 else "Unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        ffmpeg_status = False
    
    return {
        "status": "healthy" if processor and ffmpeg_status else "degraded",
        "processor_ready": processor is not None,
        "ffmpeg_available": ffmpeg_status,
        "ffmpeg_version": ffmpeg_version,
        "timestamp": time.time(),
        "message": "All systems operational" if processor and ffmpeg_status else 
                  "FFmpeg not found - video processing will fail" if not ffmpeg_status else
                  "Video processor not initialized"
    }

@app.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported video formats."""
    if not processor:
        raise HTTPException(status_code=500, detail="Video processor not initialized")
    
    return {
        "supported_formats": processor.get_supported_formats()
    }

# Cleanup old status entries (keep only last 100)
@app.on_event("startup")
async def startup_event():
    logger.info("Subtitle Generator API started")
    if processor:
        logger.info("Video processor initialized successfully")
    else:
        logger.warning("Video processor failed to initialize")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Subtitle Generator API shutting down")
    # Clean up any remaining files
    try:
        for task_id, status in processing_status.items():
            if "file_path" in status and os.path.exists(status["file_path"]):
                os.unlink(status["file_path"])
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
