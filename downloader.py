#!/usr/bin/env python3
"""
Robust YouTube playlist downloader
- Base folder: youtube_downloads/
- Playlist folders use sanitized snake_case names
- Retries, resume, rate limit, per-video timeout, logging
"""

import os
import re
import sys
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Process, Queue

# try import yt-dlp (install if missing)
try:
    from yt_dlp import YoutubeDL
    import yt_dlp
    # Check if yt-dlp version is recent enough to avoid type comparison issues
    version = getattr(yt_dlp, '__version__', '0.0.0')
    major, minor = map(int, version.split('.')[:2])
    if major < 2023 or (major == 2023 and minor < 10):
        print(f"yt-dlp version {version} may have compatibility issues. Updating...")
        os.system(f"{sys.executable} -m pip install --upgrade yt-dlp")
except ImportError:
    print("yt-dlp not found. Installing...")
    os.system(f"{sys.executable} -m pip install --upgrade yt-dlp")
    from yt_dlp import YoutubeDL

# ==============================
# CONFIGURATION (tweak here)
# ==============================
BASE_DIR = "youtube_downloads"   # base folder
parallel = True                 # default sequential (set True if you know your bandwidth)
max_workers = 2                  # used when parallel=True
audio_only = False               # True => download audio (mp3), False => video (mp4)
max_retries = 5                  # number of retry attempts per URL
initial_retry_delay = 2          # seconds; exponential backoff multiplier
rate_limit = 1048576              # 1MB/sec in bytes (1M causes type comparison issues)
per_video_timeout = 4 * 3600     # seconds: 4 hours per video (safety kill for hangs)

LOG_FILE = os.path.join(BASE_DIR, "download_log.txt")
FAILED_FILE = os.path.join(BASE_DIR, "failed_urls.txt")

# quality strategy
MAX_RES = 1080       # maximum desired resolution cap
# format strategy (prefer single-file mp4 up to MAX_RES, then fallback)
FORMAT_TEMPLATE = f"bv*[height<={MAX_RES}]+ba/bv+ba/b[ext=mp4]/best"

# ==============================
# Utilities
# ==============================
def ensure_base_dir():
    os.makedirs(BASE_DIR, exist_ok=True)

def log(msg: str):
    ensure_base_dir()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def sanitize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "untitled"

def safe_progress_hook(d):
    """
    Progress hook that handles type mismatches safely.
    """
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

# ==============================
# Worker that runs inside its own process
# ==============================
def yt_download_worker(url: str, dl_opts: dict, q: Queue):
    """
    Worker to run inside a separate process (prevents hangs from freezing main program).
    It performs the download and puts a (success_bool, message) in queue.
    """
    try:
        # Add progress hook to handle type issues
        dl_opts_safe = dl_opts.copy()
        dl_opts_safe['progress_hooks'] = [safe_progress_hook]
        
        # Additional safety options for type comparison issues
        dl_opts_safe.update({
            'socket_timeout': 30,
            'http_chunk_size': 10485760,  # 10MB chunks to avoid string/float comparisons
        })
        
        with YoutubeDL(dl_opts_safe) as ydl:
            ydl.download([url])
        q.put((True, f"SUCCESS: {url}"))
    except Exception as e:
        error_msg = str(e)
        # Handle the specific type comparison error
        if "'>' not supported between instances of 'float' and 'str'" in error_msg:
            q.put((False, f"ERROR: {url} | Type comparison issue - try updating yt-dlp"))
        else:
            q.put((False, f"ERROR: {url} | {type(e).__name__}: {e}"))

# ==============================
# Download routine with retries, resume, timeout
# ==============================
def download_url(url: str) -> str:
    """
    High-level download for a single URL (playlist or video).
    Uses a child process and a timeout to prevent hangs.
    Retries up to max_retries with exponential backoff.
    Returns a status string starting with '✅' or '❌' to indicate result.
    """
    # First: attempt to extract metadata to determine playlist title (quietly)
    base_metadata_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ratelimit": rate_limit,
    }
    playlist_subdir = None
    try:
        with YoutubeDL(base_metadata_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # info may be playlist or video; detect playlist title
            if info:
                if info.get("_type") == "playlist":
                    title = info.get("title")
                    playlist_subdir = sanitize_name(title) if title else None
                else:
                    # For video within playlist, some extractors set "playlist_title"
                    playlist_title = info.get("playlist_title") or info.get("playlist")
                    if playlist_title:
                        playlist_subdir = sanitize_name(playlist_title)
    except Exception as e:
        log(f"⚠️ Metadata extraction failed for {url}: {e} — will attempt download anyway")

    # Build download options
    outtmpl = os.path.join(playlist_subdir, "%(title)s.%(ext)s") if playlist_subdir else "%(title)s.%(ext)s"
    dl_opts = {
        "outtmpl": outtmpl,
        "paths": {"home": BASE_DIR},  # put all downloads under BASE_DIR
        "noplaylist": False,          # allow playlists
        "continuedl": True,           # resume partial downloads
        "ratelimit": rate_limit,
        "quiet": False,
        "no_warnings": True,
        "ignoreerrors": True,         # don't abort entire playlist if one item fails
        "retries": 3,                 # internal yt-dlp retries
        "fragment_retries": 3,        # retry fragments
        "extractor_retries": 3,       # retry extractor calls
    }

    # Format selection: prefer single-file mp4 up to MAX_RES, but fall back
    dl_opts["format"] = FORMAT_TEMPLATE

    if audio_only:
        # prefer m4a for efficiency, convert to mp3 if desired — user chose mp3 earlier, so we'll set mp3 postprocessor
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
        # ensure we do not force merging/muxing unnecessary extra steps
        dl_opts.update({
            # format already set above
            "merge_output_format": "mp4"  # safe fallback if merger is needed
        })

    # Retry loop
    delay = initial_retry_delay
    for attempt in range(1, max_retries + 1):
        q = Queue()
        p = Process(target=yt_download_worker, args=(url, dl_opts, q), daemon=True)
        p.start()
        p.join(per_video_timeout)  # wait up to per_video_timeout seconds

        if p.is_alive():
            # Worker hung — kill and retry
            try:
                p.terminate()
                p.join(5)
            except Exception:
                pass
            log(f"⚠️ Timeout (>{per_video_timeout}s) reached for {url}; attempt {attempt}/{max_retries}")
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            else:
                log(f"❌ FAILED after timeout: {url}")
                return f"❌ Failed: {url} (timeout)"
        else:
            # Process ended; check result in queue
            try:
                success, message = q.get_nowait()
            except Exception:
                # If queue empty for some reason, treat as failure
                success = False
                message = f"ERROR: {url} (no result from worker)"
            if success:
                log(f"✅ SUCCESS: {url}")
                return f"✅ Downloaded: {url}"
            else:
                log(f"⚠️ Attempt {attempt}/{max_retries} failed for {url}: {message}")
                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    log(f"❌ FAILED after {max_retries} attempts: {url}")
                    return f"❌ Failed: {url}"

# ==============================
# Main
# ==============================
def main():
    if len(sys.argv) < 2:
        print("Usage: python downloader.py urls.txt")
        sys.exit(1)

    list_path = sys.argv[1]
    try:
        with open(list_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ File not found: {list_path}")
        sys.exit(1)

    ensure_base_dir()
    log("\n" + "=" * 80)
    log(f"📥 Loaded {len(urls)} URL(s) from {list_path}")
    log(f"📁 Base folder: {BASE_DIR}")
    log(f"⚙️ Mode: {'Parallel' if parallel else 'Sequential'} | "
        f"{'Audio' if audio_only else 'Video'} | "
        f"Retries: {max_retries} | Rate: {rate_limit} | MaxRes: {MAX_RES}")
    log("=" * 80 + "\n")

    results = []
    if parallel:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(download_url, u) for u in urls]
            for fut in as_completed(futures):
                results.append(fut.result())
    else:
        for u in urls:
            res = download_url(u)
            results.append(res)
            # small cooldown between downloads to be polite
            time.sleep(1)

    # Summary + failed list
    failures = [u for u, r in zip(urls, results) if r.startswith("❌")]
    log("\n" + "-" * 72)
    log("📊 SUMMARY")
    log(f"   Total: {len(urls)}")
    log(f"   Success: {len(urls) - len(failures)}")
    log(f"   Failed: {len(failures)}")
    if failures:
        with open(FAILED_FILE, "w", encoding="utf-8") as f:
            for u in failures:
                f.write(u + "\n")
        log(f"   ❗ Failed URLs written to: {FAILED_FILE}")
    log("-" * 72 + "\n")

if __name__ == "__main__":
    main()
