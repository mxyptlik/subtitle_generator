#!/usr/bin/env python3
"""
Test FastAPI server with YouTube download endpoint (without whisper dependency)
"""

from fastapi import FastAPI, BackgroundTasks, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import uuid
import time
import logging
from pathlib import Path
from typing import Dict

# Import our YouTube downloader
from youtube_downloader import YouTubeDownloader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app  
app = FastAPI(title="YouTube Subtitle Generator Test", description="Test YouTube download functionality")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7860"],  # Gradio's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up directories
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
UPLOAD_DIR = os.path.join(project_root, "uploads")
OUTPUT_DIR = os.path.join(project_root, "outputs")

# Create directories
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Storage for processing status
processing_status: Dict[str, Dict] = {}

async def process_youtube_task(task_id: str, url: str, parallel: bool = False, audio_only: bool = False, 
                              max_resolution: int = 1080, embed_subtitles: bool = False, language: str = "en"):
    """Test background task to download YouTube video."""
    
    logger.info(f"=== YOUTUBE TEST TASK DEBUG ===")
    logger.info(f"Task ID: {task_id}")
    logger.info(f"URL: {url}")
    logger.info(f"Audio only: {audio_only}")
    logger.info(f"Language: {language}")
    logger.info(f"=== END DEBUG ===")
    
    downloader = None
    video_path = None
    
    try:
        # Create YouTube downloader
        downloader = YouTubeDownloader(
            download_dir=UPLOAD_DIR,
            parallel=parallel,
            audio_only=audio_only, 
            max_resolution=max_resolution,
            rate_limit=1048576,  # 1MB/s
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
        result = downloader.download_video(url)
        
        if not result.get("success"):
            raise Exception(f"Download failed: {result.get('error', 'Unknown error')}")
        
        video_path = result.get("file_path")
        if not video_path or not os.path.exists(video_path):
            raise Exception("Download failed - no video file created")
        
        logger.info(f"YouTube download completed: {video_path}")
        
        # Update status to completed (for testing, we skip subtitle generation)
        processing_time = time.time() - processing_status[task_id]["start_time"]
        
        result_data = {
            "status": "completed",
            "progress": 100,
            "message": "YouTube video downloaded successfully (subtitle generation skipped in test mode)",
            "download_path": video_path,
            "download_filename": os.path.basename(video_path),
            "processing_time": processing_time,
            "video_title": result.get("title", "Unknown")
        }
        
        processing_status[task_id].update(result_data)
        
        logger.info(f"YouTube test completed for task {task_id}. Time: {processing_time:.2f}s")
        
    except Exception as e:
        logger.error(f"YouTube test failed for task {task_id}: {e}")
        processing_status[task_id].update({
            "status": "error",
            "progress": 0,
            "message": f"YouTube download failed: {str(e)}"
        })
    finally:
        # Clean up downloaded video file (for testing)
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
async def youtube_download_test(background_tasks: BackgroundTasks,
                               url: str = Form(...),
                               parallel: bool = Form(False),
                               audio_only: bool = Form(False),
                               max_resolution: int = Form(1080),
                               embed_subtitles: str = Form("false"),
                               language: str = Form("en")):
    """Test YouTube download endpoint."""
    
    # Convert embed_subtitles string to boolean
    embed_subtitles_bool = embed_subtitles.lower() in ('true', '1', 'yes', 'on')
    
    logger.info(f"=== YOUTUBE TEST REQUEST DEBUG ===")
    logger.info(f"URL: {url}")
    logger.info(f"Audio only: {audio_only}")
    logger.info(f"Max resolution: {max_resolution}")
    logger.info(f"Language: {language}")
    logger.info(f"Embed subtitles: {embed_subtitles_bool}")
    logger.info(f"=== END DEBUG ===")
    
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
    
    logger.info(f"YouTube test download started: {url}, Task ID: {task_id}")
    
    return {
        "task_id": task_id,
        "url": url,
        "status": "downloading",
        "audio_only": audio_only,
        "max_resolution": max_resolution,
        "embed_subtitles": embed_subtitles_bool,
        "language": language,
        "message": "YouTube download started (test mode - no subtitle generation)."
    }

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Get processing status for a task."""
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = processing_status[task_id].copy()
    
    # Don't expose internal file paths
    if "download_path" in status:
        del status["download_path"]
    
    return status

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "YouTube download test server is running",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    logger.info("Starting YouTube download test server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)