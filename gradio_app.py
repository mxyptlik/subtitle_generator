# gradio_app.py - Updated with proper download buttons for Gradio 4.x

import gradio as gr
import requests
import os
import tempfile
import time
from pathlib import Path

# Gradio will call your existing FastAPI backend
FASTAPI_URL = "http://localhost:8000"

def process_youtube_gradio(youtube_url, target_language, embed_subtitles, audio_only, max_resolution):
    """Process YouTube URL through FastAPI backend."""
    if not youtube_url or not youtube_url.strip():
        return "❌ Please provide a YouTube URL", None, None, None, None
    
    try:
        print(f"🎬 Processing YouTube URL: {youtube_url}")
        print(f"🌍 Language parameter: {target_language}")
        print(f"🎵 Audio only: {audio_only}")
        print(f"📺 Max resolution: {max_resolution}")
        
        # Prepare data for FastAPI
        data = {
            'url': youtube_url.strip(),
            'language': target_language,
            'embed_subtitles': embed_subtitles,
            'audio_only': audio_only,
            'max_resolution': max_resolution,
            'parallel': False  # Not used for single video
        }
        
        # Call FastAPI YouTube endpoint
        response = requests.post(
            f"{FASTAPI_URL}/youtube-download",
            data=data,
            timeout=30  # Initial request timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            
            if not task_id:
                return "❌ YouTube request failed - no task ID received", None, None, None, None
            
            # Poll every 3 seconds for up to 15 minutes (YouTube downloads take longer)
            max_polls = 300
            poll_count = 0
            
            while poll_count < max_polls:
                time.sleep(3)
                poll_count += 1
                
                try:
                    status_response = requests.get(f"{FASTAPI_URL}/status/{task_id}")
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status', 'unknown')
                        
                        if status == 'completed':
                            # Processing completed successfully
                            success_msg = f"🎉 YouTube video processed successfully!\nTask ID: {task_id}\nTotal time: {poll_count * 3} seconds"
                            
                            # Download the files
                            srt_file = download_srt_file(task_id)
                            video_file = download_video_file(task_id) if status_data.get('embed_subtitles') else None
                            
                            return (
                                success_msg,
                                task_id,
                                srt_file,
                                video_file,
                                gr.Button("📄 Download SRT", visible=True) if srt_file else gr.Button(visible=False)
                            )
                        
                        elif status == 'error':
                            error_msg = status_data.get('message', 'Unknown error')
                            return f"❌ YouTube processing failed: {error_msg}", task_id, None, None, gr.Button(visible=False)
                        
                        elif status in ['downloading', 'processing']:
                            elapsed = poll_count * 3
                            progress = status_data.get('progress', 0)
                            message = status_data.get('message', 'Processing...')
                            status_msg = f"⏳ {message}\nProgress: {progress}% ({elapsed}s elapsed)\nTask ID: {task_id}"
                        
                        else:
                            status_msg = f"⏳ Status: {status} ({poll_count * 3}s elapsed)\nTask ID: {task_id}"
                    
                    else:
                        return f"❌ Status check failed: {status_response.text}", task_id, None, None, gr.Button(visible=False)
                        
                except requests.exceptions.RequestException as e:
                    return f"❌ Status check error: {str(e)}", task_id, None, None, gr.Button(visible=False)
            
            # Timeout reached
            return f"⏰ Processing timeout (15 minutes). Task ID: {task_id}", task_id, None, None, gr.Button(visible=False)
                    
        else:
            return f"❌ YouTube request failed: {response.text}", None, None, None, gr.Button(visible=False)
            
    except Exception as e:
        return f"❌ Error: {str(e)}", None, None, None, gr.Button(visible=False)

def process_video_gradio(video_file, target_language, embed_subtitles):
    """Gradio interface that calls your FastAPI backend and polls for completion."""
    if video_file is None:
        return "❌ Please upload a video file", None, None, None, None
    
    try:
        # Handle different types that Gradio might return
        if hasattr(video_file, 'name'):
            video_path = video_file.name
            print(f"📁 Gradio file object, path: {video_path}")
        else:
            video_path = video_file
            print(f"📁 Gradio path string: {video_path}")
        
        # Debug the language parameter
        print(f"🌍 Language parameter received: {target_language}")
        
        # Check if the path exists
        if not os.path.exists(video_path):
            return f"❌ Video file not found: {video_path}", None, None, None, None
        
        # Get file size for logging
        file_size = os.path.getsize(video_path)
        print(f"📦 File size: {file_size} bytes ({file_size / (1024*1024):.1f} MB)")
        
        # Open and read the file content
        with open(video_path, 'rb') as f:
            file_content = f.read()
        
        print(f"📤 Read {len(file_content)} bytes from file")
        print(f"📤 Sending to FastAPI with language: {target_language}")
        
        # Prepare the file for upload to FastAPI
        filename = os.path.basename(video_path) if os.path.basename(video_path) != video_path else "video.mp4"
        files = {'file': (filename, file_content, 'video/mp4')}
        data = {
            'language': target_language,
            'embed_subtitles': embed_subtitles
        }
        
        # Call your existing FastAPI endpoint
        response = requests.post(
            f"{FASTAPI_URL}/upload",
            files=files,
            data=data,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            
            if not task_id:
                return "❌ Upload failed - no task ID received", None, None, None, None
            
            # Poll every 2 seconds for up to 10 minutes
            max_polls = 300
            poll_count = 0
            
            while poll_count < max_polls:
                time.sleep(2)
                poll_count += 1
                
                try:
                    status_response = requests.get(f"{FASTAPI_URL}/status/{task_id}")
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status', 'unknown')
                        
                        if status == 'completed':
                            # Processing completed successfully
                            success_msg = f"🎉 Processing completed successfully!\nTask ID: {task_id}\nProcessing time: {poll_count * 2} seconds"
                            
                            # Download the files to make them available for download buttons
                            srt_file = download_srt_file(task_id)
                            video_file = download_video_file(task_id) if status_data.get('embed_subtitles') else None
                            
                            return (
                                success_msg,
                                task_id,
                                srt_file,
                                video_file,
                                gr.Button("📄 Download SRT", visible=True) if srt_file else gr.Button(visible=False)
                            )
                        
                        elif status == 'failed':
                            error_msg = status_data.get('error', 'Unknown error')
                            return f"❌ Processing failed: {error_msg}", task_id, None, None, gr.Button(visible=False)
                        
                        elif status == 'processing':
                            elapsed = poll_count * 2
                            status_msg = f"⏳ Processing video... ({elapsed}s elapsed)\nTask ID: {task_id}\nStatus: {status}"
                        
                        else:
                            status_msg = f"⏳ Status: {status} ({poll_count * 2}s elapsed)\nTask ID: {task_id}"
                    
                    else:
                        return f"❌ Status check failed: {status_response.text}", task_id, None, None, gr.Button(visible=False)
                        
                except requests.exceptions.RequestException as e:
                    return f"❌ Status check error: {str(e)}", task_id, None, None, gr.Button(visible=False)
            
            # Timeout reached
            return f"⏰ Processing timeout (10 minutes). Task ID: {task_id}", task_id, None, None, gr.Button(visible=False)
                    
        else:
            return f"❌ Upload failed: {response.text}", None, None, None, gr.Button(visible=False)
            
    except Exception as e:
        return f"❌ Error: {str(e)}", None, None, None, gr.Button(visible=False)

def download_srt_file(task_id):
    """Download SRT file and return local path for Gradio download."""
    try:
        response = requests.get(f"{FASTAPI_URL}/download/{task_id}")
        if response.status_code == 200:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.srt', prefix=f'subtitles_{task_id}_')
            temp_file.write(response.content)
            temp_file.close()
            print(f"📄 Downloaded SRT file: {temp_file.name}")
            return temp_file.name
        else:
            print(f"❌ SRT download failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ SRT download error: {str(e)}")
        return None

def download_video_file(task_id):
    """Download video file and return local path for Gradio download."""
    try:
        response = requests.get(f"{FASTAPI_URL}/download-video/{task_id}")
        if response.status_code == 200:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4', prefix=f'video_{task_id}_')
            temp_file.write(response.content)
            temp_file.close()
            print(f"🎬 Downloaded video file: {temp_file.name}")
            return temp_file.name
        else:
            print(f"❌ Video download failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Video download error: {str(e)}")
        return None

def check_status_manual(task_id):
    """Manual status check."""
    if not task_id:
        return "No task ID provided", None, None, gr.Button(visible=False)
    
    try:
        response = requests.get(f"{FASTAPI_URL}/status/{task_id}")
        
        if response.status_code == 200:
            status_data = response.json()
            status = status_data.get('status', 'unknown')
            
            if status == 'completed':
                srt_file = download_srt_file(task_id)
                video_file = download_video_file(task_id) if status_data.get('embed_subtitles') else None
                
                return (
                    "✅ Processing completed!",
                    srt_file,
                    video_file,
                    gr.Button("📄 Download SRT", visible=True) if srt_file else gr.Button(visible=False)
                )
            elif status == 'failed':
                return f"❌ Processing failed: {status_data.get('error', 'Unknown error')}", None, None, gr.Button(visible=False)
            else:
                return f"⏳ Status: {status}", None, None, gr.Button(visible=False)
        else:
            return f"❌ Status check failed: {response.text}", None, None, gr.Button(visible=False)
            
    except Exception as e:
        return f"❌ Status check error: {str(e)}", None, None, gr.Button(visible=False)

# Gradio Interface for version 4.x with Upload and YouTube Options
with gr.Blocks(title="AI Subtitle Generator", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎬 AI Subtitle Generator")
    gr.Markdown("Generate AI-powered subtitles from uploaded videos or YouTube URLs!")
    
    with gr.Row():
        with gr.Column():
            # Tab interface for different input methods
            with gr.Tab("📁 Upload Video"):
                video_input = gr.File(
                    label="Upload Video File",
                    file_types=[".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]
                )
                
                upload_language_dropdown = gr.Dropdown(
                    choices=[
                        ("English", "en"),
                        ("Spanish", "es"), 
                        ("French", "fr"),
                        ("German", "de"),
                        ("Italian", "it"),
                        ("Portuguese", "pt"),
                        ("Russian", "ru"),
                        ("Japanese", "ja"),
                        ("Korean", "ko"),
                        ("Chinese", "zh"),
                        ("Arabic", "ar"),
                        ("Hindi", "hi"),
                        ("Yoruba", "yo")
                    ],
                    value="en",
                    label="Target Language"
                )
                
                upload_embed_checkbox = gr.Checkbox(
                    label="Create video with embedded soft subtitles",
                    value=False
                )
                
                upload_process_btn = gr.Button("🎬 Generate Subtitles from Upload", variant="primary", size="lg")
            
            with gr.Tab("🎥 YouTube URL"):
                youtube_url_input = gr.Textbox(
                    label="YouTube URL",
                    placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/...",
                    lines=1
                )
                
                with gr.Row():
                    youtube_language_dropdown = gr.Dropdown(
                        choices=[
                            ("English", "en"),
                            ("Spanish", "es"), 
                            ("French", "fr"),
                            ("German", "de"),
                            ("Italian", "it"),
                            ("Portuguese", "pt"),
                            ("Russian", "ru"),
                            ("Japanese", "ja"),
                            ("Korean", "ko"),
                            ("Chinese", "zh"),
                            ("Arabic", "ar"),
                            ("Hindi", "hi"),
                            ("Yoruba", "yo")
                        ],
                        value="en",
                        label="Target Language"
                    )
                    
                    max_resolution_dropdown = gr.Dropdown(
                        choices=[
                            ("480p", 480),
                            ("720p", 720),
                            ("1080p", 1080)
                        ],
                        value=720,
                        label="Max Resolution"
                    )
                
                with gr.Row():
                    youtube_embed_checkbox = gr.Checkbox(
                        label="Create video with embedded soft subtitles",
                        value=False
                    )
                    
                    audio_only_checkbox = gr.Checkbox(
                        label="Download audio only (MP3)",
                        value=False
                    )
                
                youtube_process_btn = gr.Button("🎥 Generate Subtitles from YouTube", variant="secondary", size="lg")
        
        with gr.Column():
            status_output = gr.Textbox(
                label="Status", 
                interactive=False,
                lines=6
            )
            
            task_id_output = gr.Textbox(
                label="Task ID",
                interactive=False
            )
            
            # File outputs for download buttons
            srt_file_output = gr.File(
                label="📄 SRT File",
                visible=True,
                interactive=False
            )
            
            video_file_output = gr.File(
                label="🎬 Video with Subtitles",
                visible=True,
                interactive=False
            )
    
    # Manual status check section
    gr.Markdown("---")
    gr.Markdown("### 🔍 Manual Status Check")
    with gr.Row():
        task_id_input = gr.Textbox(
            label="Task ID",
            placeholder="Enter task ID to check status manually"
        )
        status_check_btn = gr.Button("Check Status")
    
    # Event handlers
    upload_process_btn.click(
        fn=process_video_gradio,
        inputs=[video_input, upload_language_dropdown, upload_embed_checkbox],
        outputs=[status_output, task_id_output, srt_file_output, video_file_output, upload_process_btn]
    )
    
    youtube_process_btn.click(
        fn=process_youtube_gradio,
        inputs=[youtube_url_input, youtube_language_dropdown, youtube_embed_checkbox, audio_only_checkbox, max_resolution_dropdown],
        outputs=[status_output, task_id_output, srt_file_output, video_file_output, youtube_process_btn]
    )
    
    status_check_btn.click(
        fn=check_status_manual,
        inputs=[task_id_input],
        outputs=[status_output, srt_file_output, video_file_output, status_check_btn]
    )

if __name__ == "__main__":
    demo.launch(server_port=7860)