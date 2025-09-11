#!/usr/bin/env python3
"""
Test script for the Subtitle Generator MVP
"""
import requests
import time
import os
import sys
from pathlib import Path

def test_api_endpoints():
    """Test the API endpoints to ensure they're working."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Subtitle Generator API...")
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check: {health_data['status']}")
            print(f"   Processor ready: {health_data['processor_ready']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the server is running on localhost:8000")
        return False
    
    # Test supported formats endpoint
    try:
        response = requests.get(f"{base_url}/supported-formats")
        if response.status_code == 200:
            formats_data = response.json()
            print(f"✅ Supported formats: {', '.join(formats_data['supported_formats'])}")
        else:
            print(f"❌ Supported formats check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking supported formats: {e}")
    
    # Test main page
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Main page loads successfully")
        else:
            print(f"❌ Main page failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error accessing main page: {e}")
    
    return True

def create_test_video():
    """Create a simple test video file for testing."""
    test_video_path = "test_video.mp4"
    
    try:
        # Create a simple 5-second test video with ffmpeg
        import subprocess
        
        command = [
            "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", "-y", test_video_path
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(test_video_path):
            print(f"✅ Test video created: {test_video_path}")
            return test_video_path
        else:
            print(f"❌ Failed to create test video: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating test video: {e}")
        return None

def test_video_upload(video_path):
    """Test video upload and processing."""
    base_url = "http://localhost:8000"
    
    if not os.path.exists(video_path):
        print(f"❌ Test video not found: {video_path}")
        return False
    
    print(f"🎬 Testing video upload with: {video_path}")
    
    try:
        with open(video_path, 'rb') as f:
            files = {'file': (os.path.basename(video_path), f, 'video/mp4')}
            response = requests.post(f"{base_url}/upload", files=files)
        
        if response.status_code == 200:
            upload_data = response.json()
            task_id = upload_data['task_id']
            print(f"✅ Upload successful. Task ID: {task_id}")
            
            # Monitor processing status
            print("⏳ Monitoring processing status...")
            max_wait = 120  # 2 minutes max
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                status_response = requests.get(f"{base_url}/status/{task_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   Status: {status_data['status']} - {status_data['message']} ({status_data['progress']}%)")
                    
                    if status_data['status'] == 'completed':
                        print("✅ Processing completed successfully!")
                        
                        # Test download
                        download_response = requests.get(f"{base_url}/download/{task_id}")
                        if download_response.status_code == 200:
                            subtitle_filename = f"test_subtitles_{task_id}.srt"
                            with open(subtitle_filename, 'wb') as f:
                                f.write(download_response.content)
                            print(f"✅ Subtitles downloaded: {subtitle_filename}")
                            
                            # Show a preview of the SRT content
                            with open(subtitle_filename, 'r', encoding='utf-8') as f:
                                content = f.read()
                                lines = content.split('\n')[:10]  # First 10 lines
                                print("📝 Subtitle preview:")
                                for line in lines:
                                    print(f"   {line}")
                                if len(content.split('\n')) > 10:
                                    print("   ...")
                            
                            return True
                        else:
                            print(f"❌ Download failed: {download_response.status_code}")
                            return False
                    
                    elif status_data['status'] == 'error':
                        print(f"❌ Processing failed: {status_data['message']}")
                        return False
                
                time.sleep(2)
            
            print("❌ Processing timeout")
            return False
            
        else:
            error_data = response.json()
            print(f"❌ Upload failed: {error_data.get('detail', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error during upload test: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Subtitle Generator MVP Test Suite")
    print("=" * 50)
    
    # Test API endpoints
    if not test_api_endpoints():
        print("\n❌ API tests failed. Please check if the server is running.")
        sys.exit(1)
    
    print("\n📹 Video Processing Tests")
    print("-" * 30)
    
    # Check if we have a test video or need to create one
    test_video = None
    
    # Look for existing video files
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    for ext in video_extensions:
        test_files = list(Path('.').glob(f'*{ext}'))
        if test_files:
            test_video = str(test_files[0])
            print(f"🎬 Found test video: {test_video}")
            break
    
    # Create a test video if none found
    if not test_video:
        print("🔧 No test video found. Creating one...")
        test_video = create_test_video()
    
    if test_video:
        success = test_video_upload(test_video)
        
        # Cleanup created test video
        if test_video == "test_video.mp4" and os.path.exists(test_video):
            os.unlink(test_video)
            print(f"🧹 Cleaned up test video: {test_video}")
        
        if success:
            print("\n🎉 All tests passed! The Subtitle Generator MVP is working correctly.")
        else:
            print("\n❌ Some tests failed. Please check the logs for details.")
            sys.exit(1)
    else:
        print("\n⚠️  Could not create or find a test video. Please test manually by uploading a video through the web interface.")

if __name__ == "__main__":
    main()
