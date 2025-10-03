#!/usr/bin/env python3
"""
Test script for YouTube downloader functionality
"""

import os
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

from youtube_downloader import YouTubeDownloader

def test_youtube_downloader():
    """Test YouTube downloader with a short video"""
    
    # Create test output directory
    test_dir = Path(__file__).parent / "test_downloads"
    test_dir.mkdir(exist_ok=True)
    
    print("🧪 Testing YouTube Downloader...")
    
    # Test URL - a short video for testing
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll (short, reliable)
    
    try:
        # Create downloader instance
        downloader = YouTubeDownloader(
            download_dir=str(test_dir),
            parallel=False,
            audio_only=True,  # Download audio only for faster testing
            max_resolution=480,  # Lower resolution for speed
            rate_limit=500*1024,  # 500KB/s rate limit in bytes
            max_retries=2
        )
        
        print(f"📥 Downloading: {test_url}")
        print("⏳ This may take a moment...")
        
        # Download the video
        result = downloader.download_video(test_url)
        
        if result.get("success") and result.get("file_path"):
            result_path = result["file_path"]
            if os.path.exists(result_path):
                file_size = os.path.getsize(result_path)
                print(f"✅ Download successful!")
                print(f"📁 File: {result_path}")
                print(f"🎵 Title: {result.get('title', 'Unknown')}")
                print(f"📦 Size: {file_size / (1024*1024):.1f} MB")
                
                # Clean up
                try:
                    os.unlink(result_path)
                    print("🧹 Cleaned up test file")
                except Exception as e:
                    print(f"⚠️ Cleanup warning: {e}")
                    
                return True
            else:
                print("❌ Download failed - file not found")
                return False
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ Download failed: {error}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        # Clean up downloader
        try:
            downloader.cleanup()
        except:
            pass

if __name__ == "__main__":
    print("🎬 YouTube Downloader Test")
    print("=" * 40)
    
    success = test_youtube_downloader()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("YouTube downloader is working correctly.")
    else:
        print("\n💥 Test failed!")
        print("Check the error messages above.")