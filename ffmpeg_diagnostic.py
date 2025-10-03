#!/usr/bin/env python3
"""
FFmpeg diagnostic script for subtitle generator
"""
import subprocess
import sys
import os

def check_ffmpeg():
    """Check if FFmpeg is installed and working."""
    print("🔍 Checking FFmpeg installation...")

    try:
        # Check FFmpeg version
        result = subprocess.run(['ffmpeg', '-version'],
                              capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            print("✅ FFmpeg is installed")
            # Get first line of version info
            version_line = result.stdout.split('\n')[0]
            print(f"📋 Version: {version_line}")
        else:
            print("❌ FFmpeg command failed")
            print(f"Error: {result.stderr}")
            return False

    except FileNotFoundError:
        print("❌ FFmpeg is not installed or not in PATH")
        print("💡 Install FFmpeg from: https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        print(f"❌ FFmpeg check failed: {e}")
        return False

    return True

def test_basic_functionality():
    """Test basic FFmpeg functionality."""
    print("\n🔧 Testing basic FFmpeg functionality...")

    try:
        # Test with a simple command
        result = subprocess.run([
            'ffmpeg',
            '-f', 'lavfi',  # Use lavfi input
            '-i', 'sine=frequency=1000:duration=1',  # Generate 1 second of 1kHz tone
            '-c:a', 'pcm_s16le',  # PCM 16-bit little-endian
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite output
            'test_audio.wav'  # Output file
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ Basic audio processing works")
            if os.path.exists('test_audio.wav'):
                size = os.path.getsize('test_audio.wav')
                print(f"📁 Test file created: {size} bytes")
                os.remove('test_audio.wav')  # Clean up
            return True
        else:
            print("❌ Basic audio processing failed")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ FFmpeg timed out")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main diagnostic function."""
    print("🎬 Subtitle Generator - FFmpeg Diagnostics")
    print("=" * 50)

    ffmpeg_ok = check_ffmpeg()
    if not ffmpeg_ok:
        print("\n❌ FFmpeg issues detected. Please fix before running subtitle generator.")
        sys.exit(1)

    basic_ok = test_basic_functionality()
    if not basic_ok:
        print("\n❌ FFmpeg functionality test failed.")
        print("💡 This might indicate missing codecs or other issues.")
        sys.exit(1)

    print("\n✅ All FFmpeg tests passed!")
    print("🎉 Your FFmpeg installation should work with the subtitle generator.")

if __name__ == "__main__":
    main()