#!/usr/bin/env python3
"""
YouTube downloader integration for FastAPI
Extracted from downloader.py for subtitle generator integration
"""

import os
import re
import tempfile
import time
from multiprocessing import Process, Queue
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger(__name__)

# try import yt-dlp (install if missing)
try:
    from yt_dlp import YoutubeDL
    import yt_dlp
    # Check if yt-dlp version is recent enough to avoid type comparison issues
    version = getattr(yt_dlp, '__version__', '0.0.0')
    major, minor = map(int, version.split('.')[:2])
    if major < 2023 or (major == 2023 and minor < 10):
        logger.warning(f"yt-dlp version {version} may have compatibility issues. Consider updating.")
except ImportError:
    logger.error("yt-dlp not found. Please install: pip install yt-dlp")
    raise ImportError("yt-dlp is required for YouTube downloading")

class YouTubeDownloader:
    """YouTube downloader with configurable options for subtitle generator."""
    
    def __init__(self, 
                 download_dir: str = None,
                 parallel: bool = False,
                 audio_only: bool = False,
                 max_retries: int = 3,
                 rate_limit: int = 1048576,  # 1MB/sec
                 per_video_timeout: int = 1800,  # 30 minutes
                 max_resolution: int = 1080):
        """
        Initialize YouTube downloader.
        
        Args:
            download_dir: Directory to save downloads (temp dir if None)
            parallel: Whether to download in parallel (not used for single videos)
            audio_only: Download audio only (mp3) vs video (mp4)
            max_retries: Number of retry attempts
            rate_limit: Download rate limit in bytes/sec
            per_video_timeout: Timeout per video in seconds
            max_resolution: Maximum video resolution
        """
        self.download_dir = download_dir or tempfile.mkdtemp(prefix="youtube_dl_")
        self.parallel = parallel
        self.audio_only = audio_only
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self.per_video_timeout = per_video_timeout
        self.max_resolution = max_resolution
        
        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
        logger.info(f"YouTube downloader initialized: {self.download_dir}")
    
    def sanitize_name(self, name: str) -> str:
        """Sanitize filename for safe file system usage."""
        name = re.sub(r'[^\w\s-]', '', name)  # Remove special chars
        name = re.sub(r'\s+', '_', name)      # Replace spaces with underscores
        name = re.sub(r"_+", "_", name).strip("_")
        return name[:200]  # Limit length
    
    def safe_progress_hook(self, d):
        """Progress hook that handles type mismatches safely."""
        try:
            if d['status'] == 'downloading':
                # Ensure all numeric values are properly typed
                if 'downloaded_bytes' in d:
                    d['downloaded_bytes'] = float(d['downloaded_bytes']) if d['downloaded_bytes'] is not None else 0.0
                if 'total_bytes' in d:
                    d['total_bytes'] = float(d['total_bytes']) if d['total_bytes'] is not None else 0.0
                if 'total_bytes_estimate' in d:
                    d['total_bytes_estimate'] = float(d['total_bytes_estimate']) if d['total_bytes_estimate'] is not None else 0.0
        except (ValueError, TypeError, KeyError):
            # Ignore type conversion errors to prevent crashes
            pass
    
    def download_worker(self, url: str, dl_opts: dict, q: Queue):
        """Worker function for downloading in subprocess."""
        try:
            # Add progress hook to handle type issues
            dl_opts_safe = dl_opts.copy()
            dl_opts_safe['progress_hooks'] = [self.safe_progress_hook]
            
            # Additional safety options for type comparison issues
            dl_opts_safe.update({
                'socket_timeout': 30,
                'http_chunk_size': 10485760,  # 10MB chunks
            })
            
            with YoutubeDL(dl_opts_safe) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Get the downloaded file path
                if info:
                    if info.get('_type') == 'playlist':
                        # For playlists, get the first video
                        entries = info.get('entries', [])
                        if entries:
                            filename = ydl.prepare_filename(entries[0])
                        else:
                            filename = None
                    else:
                        filename = ydl.prepare_filename(info)
                    
                    # Handle audio extraction case - change extension to mp3
                    if dl_opts_safe.get('extractaudio') and dl_opts_safe.get('audioformat') == 'mp3':
                        if filename:
                            # Replace the extension with .mp3
                            base_name = os.path.splitext(filename)[0]
                            filename = f"{base_name}.mp3"
                    
                    q.put((True, filename, info.get('title', 'Unknown')))
                else:
                    q.put((False, None, "No video info extracted"))
                    
        except Exception as e:
            error_msg = str(e)
            if "'>' not supported between instances of 'float' and 'str'" in error_msg:
                q.put((False, None, "Type comparison issue - yt-dlp compatibility problem"))
            else:
                q.put((False, None, f"{type(e).__name__}: {e}"))
    
    def download_video(self, url: str) -> dict:
        """
        Download a single video from YouTube URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            dict with keys: success, file_path, title, error
        """
        logger.info(f"Starting download: {url}")
        
        # Build download options
        format_template = f"bv*[height<={self.max_resolution}]+ba/bv+ba/b[ext=mp4]/best"
        
        dl_opts = {
            "outtmpl": os.path.join(self.download_dir, "%(title)s.%(ext)s"),
            "noplaylist": True,           # Download single video only
            "continuedl": True,           # Resume partial downloads
            "ratelimit": self.rate_limit,
            "quiet": False,
            "no_warnings": True,
            "ignoreerrors": False,        # Don't ignore errors for single video
            "retries": self.max_retries,
            "fragment_retries": self.max_retries,
            "extractor_retries": self.max_retries,
        }
        
        if self.audio_only:
            dl_opts.update({
                "format": "bestaudio/best",
                "extractaudio": True,
                "audioformat": "mp3",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            })
        else:
            dl_opts.update({
                "format": format_template,
                "merge_output_format": "mp4"
            })
        
        # Retry loop with timeout
        delay = 2
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Download attempt {attempt}/{self.max_retries}")
            
            q = Queue()
            p = Process(target=self.download_worker, args=(url, dl_opts, q), daemon=True)
            p.start()
            p.join(self.per_video_timeout)
            
            if p.is_alive():
                # Worker hung - kill and retry
                try:
                    p.terminate()
                    p.join(5)
                except Exception:
                    pass
                logger.warning(f"Timeout reached for {url}; attempt {attempt}/{self.max_retries}")
                
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    return {
                        "success": False,
                        "file_path": None,
                        "title": None,
                        "error": f"Download timeout after {self.per_video_timeout}s"
                    }
            else:
                # Process ended - check result
                try:
                    success, file_path, title_or_error = q.get_nowait()
                    if success:
                        # Verify file exists and has content
                        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                            logger.info(f"Download successful: {file_path}")
                            return {
                                "success": True,
                                "file_path": file_path,
                                "title": title_or_error,
                                "error": None
                            }
                        else:
                            error_msg = "Downloaded file not found or empty"
                            logger.error(error_msg)
                            if attempt < self.max_retries:
                                time.sleep(delay)
                                delay *= 2
                                continue
                            else:
                                return {
                                    "success": False,
                                    "file_path": None,
                                    "title": None,
                                    "error": error_msg
                                }
                    else:
                        error_msg = title_or_error
                        logger.error(f"Download failed: {error_msg}")
                        if attempt < self.max_retries:
                            time.sleep(delay)
                            delay *= 2
                            continue
                        else:
                            return {
                                "success": False,
                                "file_path": None,
                                "title": None,
                                "error": error_msg
                            }
                except Exception:
                    error_msg = "No result from download worker"
                    logger.error(error_msg)
                    if attempt < self.max_retries:
                        time.sleep(delay)
                        delay *= 2
                        continue
                    else:
                        return {
                            "success": False,
                            "file_path": None,
                            "title": None,
                            "error": error_msg
                        }
        
        return {
            "success": False,
            "file_path": None,
            "title": None,
            "error": "All download attempts failed"
        }
    
    def cleanup(self):
        """Clean up temporary download directory."""
        try:
            if os.path.exists(self.download_dir):
                import shutil
                shutil.rmtree(self.download_dir)
                logger.info(f"Cleaned up download directory: {self.download_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup download directory: {e}")