#!/usr/bin/env python3
"""
Test the FastAPI YouTube endpoint
"""

import requests
import time

FASTAPI_URL = "http://localhost:8000"

def test_youtube_endpoint():
    """Test the YouTube download endpoint."""
    
    print("🧪 Testing FastAPI YouTube endpoint...")
    
    # Test URL - a short video
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        # Test health check first
        print("🏥 Checking server health...")
        health_response = requests.get(f"{FASTAPI_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Server is healthy")
        else:
            print(f"❌ Server health check failed: {health_response.status_code}")
            return False
        
        # Submit YouTube download request
        print(f"📥 Submitting YouTube download request...")
        print(f"🎵 URL: {test_url}")
        
        data = {
            'url': test_url,
            'language': 'en',
            'embed_subtitles': 'false',
            'audio_only': True,  # Audio only for faster testing
            'max_resolution': 480,
            'parallel': False
        }
        
        response = requests.post(f"{FASTAPI_URL}/youtube-download", data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            print(f"✅ Request submitted successfully!")
            print(f"🆔 Task ID: {task_id}")
            
            if not task_id:
                print("❌ No task ID received")
                return False
            
            # Poll for completion
            print("⏳ Polling for completion...")
            max_polls = 60  # 3 minutes max
            poll_count = 0
            
            while poll_count < max_polls:
                time.sleep(3)
                poll_count += 1
                
                try:
                    status_response = requests.get(f"{FASTAPI_URL}/status/{task_id}")
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status', 'unknown')
                        progress = status_data.get('progress', 0)
                        message = status_data.get('message', 'Processing...')
                        
                        print(f"📊 Status: {status} ({progress}%) - {message}")
                        
                        if status == 'completed':
                            print("🎉 YouTube download test completed successfully!")
                            print(f"🎵 Title: {status_data.get('video_title', 'Unknown')}")
                            print(f"⏱️ Processing time: {status_data.get('processing_time', 0):.1f}s")
                            print(f"🗂️ Downloaded file: {status_data.get('download_filename', 'Unknown')}")
                            return True
                        
                        elif status == 'error':
                            error_msg = status_data.get('message', 'Unknown error')
                            print(f"❌ Download failed: {error_msg}")
                            return False
                    
                    else:
                        print(f"❌ Status check failed: {status_response.status_code}")
                        return False
                        
                except requests.exceptions.RequestException as e:
                    print(f"❌ Status check error: {e}")
                    return False
            
            # Timeout
            print("⏰ Polling timeout reached")
            return False
                    
        else:
            print(f"❌ Request failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    print("🎬 FastAPI YouTube Endpoint Test")
    print("=" * 50)
    
    success = test_youtube_endpoint()
    
    if success:
        print("\n🎉 All tests passed!")
        print("YouTube download endpoint is working correctly.")
    else:
        print("\n💥 Test failed!")
        print("Check the error messages above.")