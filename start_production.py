#!/bin/bash
"""
Production startup script for Subtitle Generator
Runs both FastAPI backend and Gradio frontend
"""

import os
import sys
import time
import signal
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('startup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def start_service(self, name, command, cwd=None):
        """Start a service with the given command."""
        try:
            logger.info(f"Starting {name}...")
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes[name] = process
            logger.info(f"{name} started with PID {process.pid}")
            return process
        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
            return None
    
    def check_services(self):
        """Check if all services are running."""
        for name, process in self.processes.items():
            if process.poll() is not None:
                logger.warning(f"{name} has stopped (exit code: {process.returncode})")
                # Restart the service
                if name == "fastapi":
                    self.start_fastapi()
                elif name == "gradio":
                    self.start_gradio()
    
    def start_fastapi(self):
        """Start FastAPI backend."""
        return self.start_service(
            "fastapi",
            [sys.executable, "-m", "app.main"],
            cwd=os.getcwd()
        )
    
    def start_gradio(self):
        """Start Gradio frontend."""
        return self.start_service(
            "gradio", 
            [sys.executable, "gradio_app.py"],
            cwd=os.getcwd()
        )
    
    def stop_all(self):
        """Stop all services."""
        logger.info("Stopping all services...")
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=10)
                logger.info(f"{name} stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {name}")
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.stop_all()
        sys.exit(0)
    
    def run(self):
        """Main run loop."""
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Start services
        self.start_fastapi()
        time.sleep(5)  # Give FastAPI time to start
        self.start_gradio()
        
        logger.info("All services started. Monitoring...")
        
        # Monitor services
        while self.running:
            try:
                time.sleep(30)  # Check every 30 seconds
                self.check_services()
            except KeyboardInterrupt:
                break
        
        self.stop_all()

if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    
    # Create directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Start service manager
    manager = ServiceManager()
    manager.run()