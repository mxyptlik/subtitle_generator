#!/usr/bin/env python3
"""
Test script to verify translation functionality
"""
import sys
import os
sys.path.append('.')

from app.video_processor import VideoProcessor

def test_translation():
    """Test the translation functionality"""
    print("Testing translation functionality...")
    
    # Create a sample SRT content
    sample_srt = """1
00:00:01,000 --> 00:00:03,000
Hello, how are you today?

2
00:00:04,000 --> 00:00:06,000
This is a test subtitle.

3
00:00:07,000 --> 00:00:09,000
The weather is nice today.

"""
    
    processor = VideoProcessor()
    
    # Test translation to French
    print("\n--- Testing French Translation ---")
    french_srt = processor.translate_srt_content(sample_srt, "fr")
    print("Original:")
    print(sample_srt)
    print("Translated to French:")
    print(french_srt)
    
    # Test translation to Spanish
    print("\n--- Testing Spanish Translation ---")
    spanish_srt = processor.translate_srt_content(sample_srt, "es")
    print("Translated to Spanish:")
    print(spanish_srt)

if __name__ == "__main__":
    test_translation()
