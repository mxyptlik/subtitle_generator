# 🎬 AI Subtitle Generator MVP

An automatic subtitle generator that uses OpenAI's Whisper model to transcribe videos and generate subtitles in SRT format.

## 🚀 Features

- **Video Upload**: Simple drag-and-drop interface for video files
- **AI Transcription**: Uses OpenAI Whisper for accurate speech-to-text conversion
- **Multiple Formats**: Supports MP4, AVI, MOV, MKV, WMV, FLV, WebM
- **SRT Output**: Generates standard SRT subtitle files with precise timing
- **Soft Subtitle Embedding**: Optional video output with embedded soft subtitles
- **Multi-Language Support**: Configurable subtitle languages with proper metadata
- **Real-time Status**: Live progress tracking during processing
- **REST API**: FastAPI-based backend for integration

## 📋 Prerequisites

### Required Software
- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **FFmpeg** - Required for video/audio processing
  - Windows: `winget install FFmpeg` or download from [FFmpeg.org](https://ffmpeg.org/download.html)
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt install ffmpeg`

### System Requirements
- 4GB+ RAM (8GB recommended for longer videos)
- 2GB free disk space
- Internet connection (for initial Whisper model download)

## 🛠️ Installation

### Quick Start (Recommended)

1. **Clone/Download the project**
   ```bash
   cd subtitle_generator
   ```

2. **Run the startup script**
   
   **Windows:**
   ```bash
   start.bat
   ```
   
   **Linux/macOS:**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

3. **Open your browser**
   Navigate to: http://localhost:8000

### Manual Installation

1. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the server**
   ```bash
   cd app
   python main.py
   ```

## 🎯 Usage

### Web Interface

1. **Open** http://localhost:8000 in your browser
2. **Select options:**
   - Choose whether to embed soft subtitles in video
   - Select subtitle language (English, Spanish, French, etc.)
3. **Upload** a video file (drag & drop or click to browse)
4. **Wait** for processing to complete (progress bar shows status)
5. **Download** the generated files:
   - SRT subtitle file (always generated)
   - Video with embedded soft subtitles (if option was selected)

### API Endpoints

#### Upload Video with Options
```http
POST /upload
Content-Type: multipart/form-data

file: <video_file>
embed_subtitles: <boolean> (optional, default: false)
language: <string> (optional, default: "en")
```

#### Download Subtitle File
```http
GET /download/{task_id}
```

#### Download Video with Embedded Subtitles
```http
GET /download-video/{task_id}
```

#### Health Check
```http
GET /health
```

## 📁 Project Structure

```
subtitle_generator/
├── app/
│   ├── main.py              # FastAPI application
│   ├── video_processor.py   # Core processing logic
│   └── templates/
│       └── index.html       # Web interface
├── uploads/                 # Temporary video storage
├── outputs/                 # Generated subtitle files
├── requirements.txt         # Python dependencies
├── start.sh                 # Linux/macOS startup script
├── start.bat               # Windows startup script
├── test_api.py             # API testing script
└── README.md               # This file
```

## 🧪 Testing

### Automated Testing
```bash
# Make sure the server is running first
python test_api.py
```

### Manual Testing
1. Use the web interface at http://localhost:8000
2. Upload a short video file (1-2 minutes recommended for testing)
3. Monitor the processing status
4. Download and verify the SRT file

### Sample Test Videos
- Create test videos with: `ffmpeg -f lavfi -i testsrc=duration=5:size=320x240:rate=30 -f lavfi -i sine=frequency=1000:duration=5 -c:v libx264 -c:a aac -shortest test.mp4`

## ⚙️ Configuration

### Whisper Model Selection
Edit `app/video_processor.py` to change the model:
```python
# Available models: tiny, base, small, medium, large
processor = VideoProcessor(model_name="base")  # Default
```

**Model Comparison:**
- `tiny`: Fastest, least accurate (~39 MB)
- `base`: Good balance (~74 MB) - **Default for MVP**
- `small`: Better accuracy (~244 MB)
- `medium`: High accuracy (~769 MB)
- `large`: Best accuracy (~1550 MB)

### Server Configuration
Edit `app/main.py` to change server settings:
```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🐛 Troubleshooting

### Common Issues

**"FFmpeg not found"**
- Install FFmpeg and ensure it's in your system PATH
- Restart terminal/command prompt after installation

**"Failed to load Whisper model"**
- Check internet connection (first-time download)
- Ensure sufficient disk space (~1GB)
- Try a smaller model (e.g., "tiny" instead of "base")

**"Upload failed" / File format issues**
- Verify file format is supported
- Check file size (recommend <500MB for MVP)
- Ensure file is not corrupted

**High memory usage**
- Use smaller Whisper model
- Process shorter videos
- Close other applications

**Slow processing**
- Use "tiny" or "base" model for faster processing
- Ensure sufficient RAM available
- Consider shorter video clips for testing

### Performance Tips

1. **For faster processing**: Use `tiny` model
2. **For better accuracy**: Use `small` or `medium` model
3. **For development**: Test with short videos (1-2 minutes)
4. **For production**: Consider larger models and more powerful hardware

## 🔧 Development

### Adding New Features

1. **Language Detection**: Modify `transcribe_audio()` in `video_processor.py`
2. **Batch Processing**: Extend the API with queue management
3. **Multiple Languages**: Add language parameter to API
4. **Custom Formatting**: Modify `generate_srt_content()`

### Code Structure

- `video_processor.py`: Core video processing and Whisper integration
- `main.py`: FastAPI application and endpoints
- `index.html`: Frontend interface
- `test_api.py`: Automated testing

## 📊 Performance Metrics

**Typical Processing Times (base model):**
- 1 minute video: ~30-60 seconds
- 5 minute video: ~2-5 minutes
- 10 minute video: ~5-10 minutes

**Memory Usage:**
- Base model: ~1-2GB RAM
- Small model: ~2-3GB RAM
- Medium model: ~3-4GB RAM

## 🔮 Future Enhancements

### Planned Features
- [ ] Multiple language support
- [ ] Batch video processing
- [ ] Speaker diarization
- [ ] Custom subtitle styling
- [ ] Docker containerization
- [ ] Background job queue
- [ ] Progress webhooks
- [ ] Video preview with subtitles

### Scaling Considerations
- Add Redis for job queuing
- Implement background workers (Celery)
- Add database for job persistence
- Implement user authentication
- Add rate limiting
- Consider GPU acceleration for larger deployments

## 📝 License

This project is intended as an MVP/proof-of-concept. Whisper is subject to OpenAI's usage terms.

## 🤝 Contributing

This is an MVP project. For production use, consider:
- Proper error handling and logging
- Security measures
- Scalability improvements
- User authentication
- Rate limiting
- Monitoring and metrics

## 📞 Support

For issues with this MVP:
1. Check the troubleshooting section
2. Verify all prerequisites are installed
3. Test with the provided test script
4. Check server logs for detailed error messages

---

**Built with ❤️ using FastAPI, Whisper, and FFmpeg**
