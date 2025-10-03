# 🎬 AI Subtitle Generator with YouTube Support

An advanced AI-powered subtitle generator that supports both video file uploads and YouTube URL processing. Features multi-language subtitle generation, translation, and video embedding capabilities.

## ✨ Features

- **Dual Input Methods**: Upload video files or paste YouTube URLs
- **Multi-language Support**: Generate subtitles in 13+ languages
- **AI Translation**: Translate subtitles to different languages using OpenAI
- **Video Embedding**: Embed soft subtitles directly into video files
- **Flexible Downloads**: Audio-only or full video processing
- **Multiple Resolutions**: Support for 480p, 720p, and 1080p downloads
- **Real-time Progress**: Live status updates during processing
- **Production Ready**: Docker containerization with health checks

## 🚀 Quick Deploy

### Option 1: Docker Deployment (Recommended)

```bash
# Clone or navigate to the project directory
cd subtitle_generator

# Run the deployment script
./deploy.sh  # Linux/Mac
# or
deploy.bat   # Windows

# Access the application
# - Gradio Interface: http://localhost:7860
# - API Backend: http://localhost:8000
```

### Option 2: Manual Docker Setup

```bash
# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Build and start
docker-compose up -d

# Check status
docker-compose ps
```

### Option 3: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start FastAPI backend
cd app && python main.py &

# Start Gradio frontend (in another terminal)
python gradio_app.py

# Access at http://localhost:7860
```

## 📋 Prerequisites

### Required
- **Docker & Docker Compose** (for containerized deployment)
- **Python 3.11+** (for local development)
- **FFmpeg** (for video processing)

### Optional
- **OpenAI API Key** (for translation features)
- **NVIDIA GPU** (for faster Whisper processing)

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# OpenAI API Key (optional - for translation features)
OPENAI_API_KEY=your_openai_api_key_here

# Environment
NODE_ENV=production

# File Storage
MAX_UPLOAD_SIZE=500000000  # 500MB
UPLOAD_DIR=/app/uploads
OUTPUT_DIR=/app/outputs

# YouTube Settings
YOUTUBE_MAX_RESOLUTION=1080
YOUTUBE_RATE_LIMIT=1048576  # 1MB/s
YOUTUBE_MAX_RETRIES=3

# Whisper Settings
WHISPER_MODEL=base  # tiny, base, small, medium, large
WHISPER_DEVICE=cpu  # or cuda for GPU

# Server Settings
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
GRADIO_HOST=0.0.0.0
GRADIO_PORT=7860
```

### Docker Compose Profiles

- **Default**: Basic subtitle generator service
- **Production**: Includes Nginx reverse proxy with SSL support

```bash
# Start with production profile
docker-compose --profile production up -d
```

## 🌐 Production Deployment

### 1. Cloud Deployment (AWS/GCP/Azure)

1. **Launch VM/Container Instance**
   - Minimum: 2 CPU, 4GB RAM
   - Recommended: 4 CPU, 8GB RAM
   - Storage: 20GB+ for temporary files

2. **Clone and Deploy**
   ```bash
   git clone <your-repo>
   cd subtitle_generator
   ./deploy.sh
   ```

3. **Configure Domain (Optional)**
   - Update `nginx.conf` with your domain
   - Add SSL certificates to `./ssl/` directory
   - Restart with production profile

### 2. Local Network Deployment

```bash
# Update CORS origins in .env
CORS_ORIGINS=http://localhost:7860,http://your-local-ip:7860

# Deploy
docker-compose up -d

# Access from other devices
# http://your-local-ip:7860
```

## 📱 Usage

### Web Interface (Gradio)

1. **Upload Video Tab**
   - Upload video files (MP4, AVI, MOV, etc.)
   - Select target language
   - Choose subtitle embedding option

2. **YouTube URL Tab**
   - Paste YouTube URL
   - Select audio-only or video download
   - Choose resolution (480p/720p/1080p)
   - Configure subtitle options

### API Endpoints

- `POST /upload` - Upload video file
- `POST /youtube-download` - Process YouTube URL
- `GET /status/{task_id}` - Check processing status
- `GET /download/{task_id}` - Download subtitle file
- `GET /download-video/{task_id}` - Download video with subtitles
- `GET /health` - Health check

### API Documentation

When running in development mode, access interactive API docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔍 Monitoring & Logs

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f subtitle-generator

# Application logs
tail -f logs/startup.log
```

### Health Checks
```bash
# Check API health
curl http://localhost:8000/health

# Check Gradio accessibility
curl http://localhost:7860
```

### Container Management
```bash
# View running containers
docker-compose ps

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Update and rebuild
git pull
docker-compose build
docker-compose up -d
```

## 🛠️ Troubleshooting

### Common Issues

1. **FFmpeg Not Found**
   ```bash
   # Install FFmpeg (Ubuntu/Debian)
   apt-get update && apt-get install -y ffmpeg
   
   # Install FFmpeg (macOS)
   brew install ffmpeg
   ```

2. **GPU Support for Whisper**
   ```bash
   # Install CUDA-enabled PyTorch
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   
   # Update .env
   WHISPER_DEVICE=cuda
   ```

3. **Large File Uploads**
   ```bash
   # Increase limits in .env
   MAX_UPLOAD_SIZE=1000000000  # 1GB
   
   # Update nginx.conf if using reverse proxy
   client_max_body_size 1000M;
   ```

4. **YouTube Download Issues**
   - Check internet connectivity
   - Verify yt-dlp is up to date
   - Some videos may be restricted

### Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=debug docker-compose up

# Or for local development
export LOG_LEVEL=debug
python -m app.main
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OpenAI Whisper** - Speech-to-text transcription
- **yt-dlp** - YouTube downloading capabilities
- **FastAPI** - High-performance web framework
- **Gradio** - Easy web interface creation
- **FFmpeg** - Video processing capabilities

---

**Happy subtitle generating! 🎬✨**