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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from video_processor import VideoProcessor
from youtube_downloader import YouTubeDownloader
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Get configuration from environment
ENVIRONMENT = os.getenv("NODE_ENV", "development")
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:7860").split(",")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "500000000"))  # 500MB default

# Initialize FastAPI app
app = FastAPI(
    title="Subtitle Generator", 
    description="AI-powered video subtitle generator with YouTube support",
    version="2.0.0",
    docs_url="/docs" if ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if ENVIRONMENT == "development" else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

def _validate_video_file(content: bytes, file_extension: str) -> bool:
    """
    Validate that the file content matches the expected video format by checking magic bytes.
    
    Args:
        content: File content as bytes
        file_extension: File extension (e.g., '.mp4', '.avi')
        
    Returns:
        True if file appears to be valid video format, False otherwise
    """
    if len(content) < 12:  # Need at least 12 bytes for most video headers
        return False
    
    # MP4/MOV magic bytes (starts with ftyp box)
    if file_extension in ['.mp4', '.mov', '.m4v']:
        # Check for ftyp box (typical MP4 signature)
        if len(content) >= 8 and content[4:8] == b'ftyp':
            return True
        # Alternative: check for moov box at beginning (some MP4 files)
        if len(content) >= 4 and content[0:4] in [b'moov', b'mdat']:
            return True
    
    # AVI magic bytes
    elif file_extension == '.avi':
        if len(content) >= 12 and content[0:4] == b'RIFF' and content[8:12] == b'AVI ':
            return True
    
    # MKV/WebM magic bytes
    elif file_extension in ['.mkv', '.webm']:
        if len(content) >= 4 and content[0:4] == b'\x1a\x45\xdf\xa3':
            return True
    
    # WMV (ASF) magic bytes
    elif file_extension == '.wmv':
        if len(content) >= 16 and content[0:16].startswith(b'\x30\x26\xb2\x75\x8e\x66\xcf\x11'):
            return True
    
    # FLV magic bytes
    elif file_extension == '.flv':
        if len(content) >= 3 and content[0:3] == b'FLV':
            return True
    
    # For other formats, do basic validation - ensure it's not obviously text or other format
    # Check if it looks like a text file
    try:
        text_content = content[:100].decode('utf-8', errors='ignore')
        # If more than 50% of characters are printable ASCII, it might be a text file
        printable_chars = sum(1 for c in text_content if c.isprintable() or c in '\n\r\t')
        if printable_chars / len(text_content) > 0.5:
            return False
    except:
        pass
    
    # If we can't definitively validate but it's not obviously wrong, accept it
    # The actual FFmpeg processing will catch real format issues
    return True

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
                      embed_subtitles: str = Form("false"),
                      language: str = Form("en")):
    """
    Upload video file and start subtitle generation process.
    
    Args:
        file: Video file to process
        embed_subtitles: Whether to create video with embedded soft subtitles (as string)
        language: Language code for subtitles (e.g., 'en', 'es', 'fr')
    
    Returns:
        JSON response with task_id for status checking
    """
    # Convert embed_subtitles string to boolean
    embed_subtitles_bool = embed_subtitles.lower() in ('true', '1', 'yes', 'on')
    
    logger.info(f"=== UPLOAD REQUEST DEBUG ===")
    logger.info(f"Received language parameter: '{language}'")
    logger.info(f"Embed subtitles: {embed_subtitles_bool}")
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
    
    # Read file content once to validate and save
    content = await file.read()
    
    # DEBUG: Log file details
    logger.info(f"=== FILE UPLOAD DEBUG ===")
    logger.info(f"File name: {file.filename}")
    logger.info(f"File content type: {file.content_type}")
    logger.info(f"File size from headers: {getattr(file, 'size', 'Not available')}")
    logger.info(f"Content length read: {len(content)} bytes")
    logger.info(f"Content preview (first 100 bytes): {content[:100]}")
    logger.info(f"=== END FILE DEBUG ===")
    
    # Validate file size (minimum 1KB for any video file)
    min_file_size = 1024  # 1KB minimum
    if len(content) < min_file_size:
        raise HTTPException(
            status_code=400, 
            detail=f"File too small ({len(content)} bytes). Video files must be at least {min_file_size} bytes."
        )
    
    # Validate file is actually a video file by checking magic bytes
    if not _validate_video_file(content, file_extension):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file format. The file doesn't appear to be a valid video file."
        )
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Save uploaded file using the content we already read
    file_path = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")
    
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Initialize processing status
        processing_status[task_id] = {
            "status": "uploaded",
            "filename": file.filename,
            "file_path": file_path,
            "start_time": time.time(),
            "progress": 0,
            "message": "File uploaded successfully",
            "embed_subtitles": embed_subtitles_bool,
            "language": language
        }
        
        # Start background processing
        background_tasks.add_task(process_video_task, task_id, file_path, embed_subtitles_bool, language)
        
        logger.info(f"File uploaded successfully: {file.filename}, Task ID: {task_id}, Embed: {embed_subtitles_bool}")
        
        return {
            "task_id": task_id,
            "filename": file.filename,
            "status": "uploaded",
            "embed_subtitles": embed_subtitles_bool,
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

async def process_youtube_task(task_id: str, url: str, parallel: bool = False, audio_only: bool = False, 
                              max_resolution: int = 1080, embed_subtitles: bool = False, language: str = "en"):
    """
    Background task to download YouTube video and process it for subtitles.
    
    Args:
        task_id: Unique task identifier
        url: YouTube URL to download
        parallel: Enable parallel processing (not used for single video)
        audio_only: Download audio only (mp3) vs video (mp4) 
        max_resolution: Maximum video resolution (480, 720, 1080)
        embed_subtitles: Whether to create video with embedded soft subtitles
        language: Language code for subtitles
    """
    logger.info(f"=== YOUTUBE PROCESS TASK DEBUG ===")
    logger.info(f"Task ID: {task_id}")
    logger.info(f"URL: {url}")
    logger.info(f"Audio only: {audio_only}")
    logger.info(f"Language: {language}")
    logger.info(f"Embed subtitles: {embed_subtitles}")
    logger.info(f"=== END YOUTUBE PROCESS DEBUG ===")
    
    downloader = None
    video_path = None
    
    try:
        # Create YouTube downloader with user settings
        downloader = YouTubeDownloader(
            download_dir=UPLOAD_DIR,
            parallel_downloads=parallel,
            audio_only=audio_only, 
            max_resolution=max_resolution,
            rate_limit="1M",  # 1MB/s rate limit
            max_retries=3
        )
        
        # Update status to downloading
        processing_status[task_id].update({
            "status": "downloading",
            "progress": 10,
            "message": "Downloading from YouTube..."
        })
        
        # Download video
        logger.info(f"Starting YouTube download for task {task_id}")
        video_path = downloader.download_video(url)
        
        if not video_path or not os.path.exists(video_path):
            raise Exception("Download failed - no video file created")
        
        logger.info(f"YouTube download completed: {video_path}")
        
        # Update status to processing
        processing_status[task_id].update({
            "status": "processing", 
            "progress": 50,
            "message": "YouTube download complete. Generating subtitles...",
            "downloaded_file": os.path.basename(video_path)
        })
        
        # Generate subtitles (and optionally video with embedded subtitles)
        srt_path, processed_video_path = processor.generate_subtitles_with_video(
            video_path, OUTPUT_DIR, embed_subtitles, language
        )
        
        # Update status to completed
        processing_time = time.time() - processing_status[task_id]["start_time"]
        
        result_data = {
            "status": "completed",
            "progress": 100,
            "message": "YouTube video processed and subtitles generated successfully",
            "srt_path": srt_path,
            "srt_filename": os.path.basename(srt_path),
            "processing_time": processing_time,
            "downloaded_file": os.path.basename(video_path)
        }
        
        # Add processed video info if embedding was successful
        if processed_video_path:
            result_data.update({
                "video_path": processed_video_path,
                "video_filename": os.path.basename(processed_video_path), 
                "message": "YouTube video processed - subtitles and video with embedded subtitles generated successfully"
            })
        
        processing_status[task_id].update(result_data)
        
        logger.info(f"YouTube processing completed for task {task_id}. Time: {processing_time:.2f}s")
        
    except Exception as e:
        logger.error(f"YouTube processing failed for task {task_id}: {e}")
        processing_status[task_id].update({
            "status": "error",
            "progress": 0,
            "message": f"YouTube processing failed: {str(e)}"
        })
    finally:
        # Clean up downloaded video file
        try:
            if video_path and os.path.exists(video_path):
                os.unlink(video_path)
                logger.info(f"Cleaned up downloaded file: {video_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up downloaded file: {e}")
        
        # Clean up downloader
        if downloader:
            try:
                downloader.cleanup()
            except Exception as e:
                logger.warning(f"Failed to cleanup downloader: {e}")

@app.post("/youtube-download")
async def youtube_download(background_tasks: BackgroundTasks,
                          url: str = Form(...),
                          parallel: bool = Form(False),
                          audio_only: bool = Form(False),
                          max_resolution: int = Form(1080),
                          embed_subtitles: str = Form("false"),
                          language: str = Form("en")):
    """
    Download video from YouTube URL and generate subtitles.
    
    Args:
        url: YouTube URL
        parallel: Enable parallel processing (not used for single video)
        audio_only: Download audio only (mp3) vs video (mp4)
        max_resolution: Maximum video resolution (480, 720, 1080)
        embed_subtitles: Whether to embed subtitles in video (as string)
        language: Target language for subtitles
    
    Returns:
        JSON response with task_id for status checking
    """
    # Convert embed_subtitles string to boolean
    embed_subtitles_bool = embed_subtitles.lower() in ('true', '1', 'yes', 'on')
    
    logger.info(f"=== YOUTUBE DOWNLOAD REQUEST DEBUG ===")
    logger.info(f"URL: {url}")
    logger.info(f"Audio only: {audio_only}")
    logger.info(f"Max resolution: {max_resolution}")
    logger.info(f"Language: {language}")
    logger.info(f"Embed subtitles: {embed_subtitles_bool}")
    logger.info(f"=== END DEBUG ===")
    
    if not processor:
        raise HTTPException(status_code=500, detail="Video processor not initialized")
    
    # Validate YouTube URL
    if not (("youtube.com" in url.lower()) or ("youtu.be" in url.lower())):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL. Must contain 'youtube.com' or 'youtu.be'")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Initialize processing status
    processing_status[task_id] = {
        "status": "downloading",
        "url": url,
        "start_time": time.time(),
        "progress": 0,
        "message": "Downloading video from YouTube...",
        "embed_subtitles": embed_subtitles_bool,
        "language": language,
        "audio_only": audio_only,
        "max_resolution": max_resolution
    }
    
    # Start background processing
    background_tasks.add_task(
        process_youtube_task, 
        task_id, url, parallel, audio_only, max_resolution, embed_subtitles_bool, language
    )
    
    logger.info(f"YouTube download started: {url}, Task ID: {task_id}")
    
    return {
        "task_id": task_id,
        "url": url,
        "status": "downloading",
        "audio_only": audio_only,
        "max_resolution": max_resolution,
        "embed_subtitles": embed_subtitles_bool,
        "language": language,
        "message": "YouTube download started. Processing will begin after download completes."
    }

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
