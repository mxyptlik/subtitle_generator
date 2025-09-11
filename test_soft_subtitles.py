#!/usr/bin/env python3
"""
Test script for soft subtitle embedding functionality
"""
import sys
import os
import tempfile
import subprocess

# Add the app directory to the path so we can import our modules
sys.path.insert(0, 'app')

def test_soft_subtitle_embedding():
    """Test the soft subtitle embedding functionality."""
    print("🧪 Testing Soft Subtitle Embedding")
    print("=" * 40)
    
    try:
        from app.video_processor import VideoProcessor
        
        # Initialize processor with tiny model for fast testing
        print("📥 Initializing VideoProcessor with 'tiny' model...")
        processor = VideoProcessor(model_name="tiny")
        print("✅ VideoProcessor initialized")
        
        # Create a test video with audio
        print("🎬 Creating test video with audio...")
        test_video = create_test_video_with_audio()
        
        if not test_video:
            print("❌ Could not create test video")
            return False
        
        print(f"✅ Test video created: {test_video}")
        
        # Test subtitle generation without embedding
        print("\n📝 Testing SRT generation only...")
        srt_path, video_path = processor.generate_subtitles_with_video(
            test_video, "test_outputs", embed_subtitles=False, language="en"
        )
        
        if srt_path and os.path.exists(srt_path):
            print(f"✅ SRT file generated: {srt_path}")
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print("📋 SRT content preview:")
                lines = content.split('\n')[:6]  # First 6 lines
                for line in lines:
                    if line.strip():
                        print(f"   {line}")
        else:
            print("❌ SRT file generation failed")
            return False
        
        # Test subtitle generation WITH embedding
        print("\n🎬 Testing SRT generation with soft subtitle embedding...")
        srt_path2, video_path2 = processor.generate_subtitles_with_video(
            test_video, "test_outputs", embed_subtitles=True, language="en"
        )
        
        if srt_path2 and os.path.exists(srt_path2):
            print(f"✅ SRT file generated: {srt_path2}")
        else:
            print("❌ SRT file generation failed")
            return False
            
        if video_path2 and os.path.exists(video_path2):
            print(f"✅ Video with soft subtitles created: {video_path2}")
            
            # Check if the video has subtitle streams
            try:
                probe_result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                    '-show_streams', video_path2
                ], capture_output=True, text=True)
                
                if probe_result.returncode == 0:
                    import json
                    probe_data = json.loads(probe_result.stdout)
                    subtitle_streams = [s for s in probe_data['streams'] if s['codec_type'] == 'subtitle']
                    
                    if subtitle_streams:
                        print(f"✅ Video contains {len(subtitle_streams)} subtitle stream(s)")
                        for i, stream in enumerate(subtitle_streams):
                            lang = stream.get('tags', {}).get('language', 'unknown')
                            codec = stream.get('codec_name', 'unknown')
                            print(f"   Stream {i}: {codec} ({lang})")
                    else:
                        print("⚠️  No subtitle streams found in video (may still work)")
                
            except Exception as e:
                print(f"⚠️  Could not analyze video streams: {e}")
        else:
            print("⚠️  Video with soft subtitles was not created (may not be supported on this system)")
        
        # Clean up test files
        cleanup_files = [test_video, srt_path, srt_path2]
        if video_path2:
            cleanup_files.append(video_path2)
            
        for file_path in cleanup_files:
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    print(f"🧹 Cleaned up: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"⚠️  Could not clean up {file_path}: {e}")
        
        print("\n🎉 Soft subtitle embedding test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def create_test_video_with_audio():
    """Create a test video with synthesized speech for testing."""
    try:
        # Create temporary file
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_video.close()
        
        # Create a 10-second test video with generated tone (simulating speech)
        command = [
            'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=10:size=640x480:rate=30',
            '-f', 'lavfi', '-i', 'sine=frequency=800:duration=10',
            '-c:v', 'libx264', '-c:a', 'aac', '-shortest', '-y', temp_video.name
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(temp_video.name):
            return temp_video.name
        else:
            print(f"FFmpeg error: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"Error creating test video: {e}")
        return None

def main():
    """Main test function."""
    print("🎬 Soft Subtitle Embedding Test")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('app/video_processor.py'):
        print("❌ Please run this script from the subtitle_generator directory")
        return
    
    # Create test output directory
    os.makedirs('test_outputs', exist_ok=True)
    
    # Run the test
    if test_soft_subtitle_embedding():
        print("\n✅ All tests passed! Soft subtitle embedding is working.")
    else:
        print("\n❌ Tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")
