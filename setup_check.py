#!/usr/bin/env python3
"""
Simple installation and dependency check for Subtitle Generator MVP
"""
import sys
import subprocess
import importlib
import os

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.8+")
        return False

def check_package(package_name, import_name=None):
    """Check if a package is installed and can be imported."""
    if import_name is None:
        import_name = package_name.replace('-', '_')
    
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✅ {package_name}: {version}")
        return True
    except ImportError:
        print(f"❌ {package_name}: Not installed")
        return False

def check_ffmpeg():
    """Check if FFmpeg is available."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg: {version_line}")
            return True
        else:
            print("❌ FFmpeg: Not working properly")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        print("❌ FFmpeg: Not found or not in PATH")
        print("   Please install FFmpeg:")
        print("   - Windows: Download from https://ffmpeg.org/download.html")
        print("   - Or use: winget install FFmpeg")
        return False

def install_packages():
    """Install required packages."""
    packages = [
        'fastapi',
        'uvicorn[standard]',
        'openai-whisper',
        'ffmpeg-python',
        'python-multipart',
        'jinja2',
        'aiofiles'
    ]
    
    print("📦 Installing packages...")
    try:
        for package in packages:
            print(f"   Installing {package}...")
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', package],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print(f"   ❌ Failed to install {package}")
                print(f"   Error: {result.stderr}")
                return False
        print("✅ All packages installed successfully")
        return True
    except Exception as e:
        print(f"❌ Error installing packages: {e}")
        return False

def main():
    """Main setup function."""
    print("🎬 Subtitle Generator MVP - Setup Check")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    print("\n📋 Checking Dependencies:")
    print("-" * 30)
    
    # Check if packages are installed
    required_packages = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('openai-whisper', 'whisper'),
        ('ffmpeg-python', 'ffmpeg'),
        ('python-multipart', 'multipart'),
        ('jinja2', 'jinja2'),
        ('aiofiles', 'aiofiles')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        if not check_package(package_name, import_name):
            missing_packages.append(package_name)
    
    # Install missing packages
    if missing_packages:
        print(f"\n📦 Installing {len(missing_packages)} missing packages...")
        if not install_packages():
            return False
        
        # Re-check packages
        print("\n🔄 Re-checking packages:")
        for package_name, import_name in required_packages:
            check_package(package_name, import_name)
    
    # Check FFmpeg
    print("\n🎥 Checking FFmpeg:")
    print("-" * 20)
    ffmpeg_ok = check_ffmpeg()
    
    print("\n📁 Checking Project Structure:")
    print("-" * 35)
    
    # Check project files
    required_files = [
        'app/main.py',
        'app/video_processor.py',
        'app/templates/index.html',
        'requirements.txt'
    ]
    
    all_files_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
            all_files_exist = False
    
    # Create directories if they don't exist
    for directory in ['uploads', 'outputs']:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Created directory: {directory}")
        else:
            print(f"✅ {directory}/")
    
    print("\n" + "=" * 50)
    
    if all_files_exist and ffmpeg_ok:
        print("🎉 Setup complete! Ready to start the application.")
        print("\nTo start the server:")
        print("   cd app")
        print("   python main.py")
        print("\nThen open: http://localhost:8000")
        return True
    elif all_files_exist:
        print("⚠️  Setup mostly complete, but FFmpeg is missing.")
        print("   The application will not work without FFmpeg.")
        print("   Please install FFmpeg and try again.")
        return False
    else:
        print("❌ Setup incomplete. Please check the missing files.")
        return False

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")
