#!/usr/bin/env python3
"""
Quick test of the core video processing functionality
"""
import sys
import os
import tempfile
import subprocess

# Add the app directory to the path so we can import our modules
sys.path.insert(0, 'app')

def create_test_audio():
    """Create a simple test audio file with speech."""
    try:
        # Create a 5-second test audio with a simple tone
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_audio.close()
        
        # Use ffmpeg to create a test audio file
        command = [
            'ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
            '-ar', '16000', '-ac', '1', '-y', temp_audio.name
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Test audio created: {temp_audio.name}")
            return temp_audio.name
        else:
            print(f"❌ Failed to create test audio: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating test audio: {e}")
        return None

def test_whisper_import():
    """Test if Whisper can be imported and initialized."""
    try:
        import whisper
        print("✅ Whisper imported successfully")
        
        # Try to load the smallest model
        print("📥 Loading Whisper 'tiny' model (for testing)...")
        model = whisper.load_model("tiny")
        print("✅ Whisper model loaded successfully")
        return model
        
    except Exception as e:
        print(f"❌ Whisper import/load failed: {e}")
        return None

def test_ffmpeg_functionality():
    """Test if FFmpeg works for audio extraction."""
    try:
        import ffmpeg
        print("✅ ffmpeg-python imported successfully")
        
        # Test FFmpeg probe functionality
        test_audio = create_test_audio()
        if test_audio:
            probe = ffmpeg.probe(test_audio)
            duration = float(probe['streams'][0]['duration'])
            print(f"✅ FFmpeg probe works - Duration: {duration:.2f}s")
            
            # Clean up
            os.unlink(test_audio)
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ FFmpeg functionality test failed: {e}")
        return False

def test_video_processor():
    """Test our VideoProcessor class."""
    try:
        from app.video_processor import VideoProcessor
        print("✅ VideoProcessor imported successfully")
        
        # Try to initialize with tiny model (faster for testing)
        processor = VideoProcessor(model_name="tiny")
        print("✅ VideoProcessor initialized successfully")
        
        # Test supported formats
        formats = processor.get_supported_formats()
        print(f"✅ Supported formats: {', '.join(formats)}")
        
        return True
        
    except Exception as e:
        print(f"❌ VideoProcessor test failed: {e}")
        return False

def test_fastapi_import():
    """Test if FastAPI and related packages work."""
    try:
        import fastapi
        import uvicorn
        import jinja2
        import aiofiles
        print("✅ FastAPI and related packages imported successfully")
        return True
    except Exception as e:
        print(f"❌ FastAPI import failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Quick Functionality Test")
    print("=" * 40)
    
    tests = [
        ("FastAPI Import", test_fastapi_import),
        ("FFmpeg Functionality", test_ffmpeg_functionality),
        ("Whisper Import", test_whisper_import),
        ("VideoProcessor", test_video_processor),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}:")
        print("-" * (len(test_name) + 12))
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
    
    print("\n" + "=" * 40)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application should work correctly.")
        print("\nNext steps:")
        print("1. Run: python app/main.py")
        print("2. Open: http://localhost:8000")
        print("3. Upload a video file to test")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please check the issues above.")
        print("\nCommon solutions:")
        print("- Install FFmpeg: https://ffmpeg.org/download.html")
        print("- Check internet connection for Whisper model download")
        print("- Ensure all Python packages are installed correctly")

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")
