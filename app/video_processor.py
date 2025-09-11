import whisper
import ffmpeg
import tempfile
import os
import uuid
from pathlib import Path
from typing import Tuple, Dict, List
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self, model_name: str = "base"):
        """Initialize the VideoProcessor with a Whisper model."""
        try:
            logger.info(f"Loading Whisper model: {model_name}")
            self.model = whisper.load_model(model_name)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def extract_audio(self, video_path: str) -> Tuple[str, float]:
        """
        Extract audio from video file and convert to WAV format.
        
        Args:
            video_path: Path to the input video file
            
        Returns:
            Tuple of (audio_file_path, duration_in_seconds)
        """
        try:
            # Create temporary file for audio
            temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio_path = temp_audio.name
            temp_audio.close()
            
            logger.info(f"Extracting audio from {video_path}")
            
            # Extract audio using ffmpeg
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Get duration
            probe = ffmpeg.probe(video_path)
            duration = float(probe['streams'][0]['duration'])
            
            logger.info(f"Audio extracted successfully. Duration: {duration:.2f}s")
            return audio_path, duration
            
        except Exception as e:
            logger.error(f"Failed to extract audio: {e}")
            # Clean up temp file if it exists
            if 'audio_path' in locals() and os.path.exists(audio_path):
                os.unlink(audio_path)
            raise
    
    def transcribe_audio(self, audio_path: str) -> Dict:
        """
        Transcribe audio using Whisper model.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Whisper transcription result with segments
        """
        try:
            logger.info(f"Transcribing audio: {audio_path}")
            
            # Transcribe audio using Whisper (always get English transcription first)
            result = self.model.transcribe(audio_path, task="translate", verbose=False)
            detected_language = result.get('language', 'unknown')
            logger.info(f"Detected language: {detected_language}")
            logger.info(f"Transcription completed. Found {len(result['segments'])} segments")
            return result
            
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            raise
    
    def translate_srt_content(self, srt_content: str, target_language: str) -> str:
        """
        Translate SRT subtitle content to target language using OpenAI GPT.
        
        Args:
            srt_content: Original SRT content in English
            target_language: Target language code (e.g., 'fr', 'de', 'es')
            
        Returns:
            Translated SRT content
        """
        if target_language == "en":
            logger.info("Target language is English, no translation needed")
            return srt_content  # No translation needed for English
            
        logger.info(f"Starting translation process. Target language: {target_language}")
        logger.info(f"SRT content length: {len(srt_content)} characters")
            
        try:
            # Language mapping for better GPT understanding
            language_names = {
                'es': 'Spanish',
                'fr': 'French', 
                'de': 'German',
                'it': 'Italian',
                'pt': 'Portuguese',
                'ru': 'Russian',
                'ja': 'Japanese',
                'ko': 'Korean',
                'zh': 'Chinese',
                'ar': 'Arabic',
                'hi': 'Hindi',
                'nl': 'Dutch',
                'sv': 'Swedish',
                'pl': 'Polish',
                'tr': 'Turkish',
                'yo': 'Yoruba'
            }
            
            target_lang_name = language_names.get(target_language, target_language)
            logger.info(f"Translating SRT content to {target_lang_name}")
            
            # Extract just the text lines from SRT (preserve numbers and timestamps)
            lines = srt_content.strip().split('\n')
            translated_lines = []
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Check if this is a subtitle number
                if line.isdigit():
                    translated_lines.append(line)  # Keep subtitle number
                    i += 1
                    
                    # Next line should be timestamp
                    if i < len(lines) and '-->' in lines[i]:
                        translated_lines.append(lines[i])  # Keep timestamp
                        i += 1
                        
                        # Collect all text lines for this subtitle
                        text_lines = []
                        while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                            text_lines.append(lines[i].strip())
                            i += 1
                        
                        # Translate the text if we have any
                        if text_lines:
                            original_text = ' '.join(text_lines)
                            translated_text = self._translate_with_gpt(original_text, target_lang_name)
                            translated_lines.append(translated_text)
                        
                        # Add empty line between subtitles
                        translated_lines.append('')
                    else:
                        i += 1
                else:
                    # Empty line or other content
                    if not line:
                        translated_lines.append('')
                    i += 1
            
            return '\n'.join(translated_lines)
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return srt_content  # Return original if translation fails
    
    def _translate_with_gpt(self, text: str, target_language: str) -> str:
        """
        Translate a single text using OpenAI GPT.
        """
        try:
            import openai
            
            # Get API key from environment variable
            api_key = os.getenv('OPENAI_API_KEY')
            logger.info(f"API Key available: {bool(api_key and api_key != 'your-api-key-here')}")
            
            if not api_key or api_key == 'your-api-key-here':
                logger.warning("OpenAI API key not set. Please set OPENAI_API_KEY in .env file")
                return text  # Return original text if no API key
            
            logger.info(f"Attempting to translate: '{text}' to {target_language}")
            
            client = openai.OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",  # Best current model for translation
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are a professional translator. Translate the given text to {target_language}. Return ONLY the translated text, no explanations or additional content."
                    },
                    {
                        "role": "user", 
                        "content": f"Translate this text to {target_language}: {text}"
                    }
                ],
                max_completion_tokens=200,
                temperature=0.1
            )
            
            translated_text = response.choices[0].message.content.strip()
            logger.info(f"Translation successful: '{text}' -> '{translated_text}'")
            return translated_text
            
        except Exception as e:
            logger.error(f"GPT translation failed for text: '{text}'. Error: {e}")
            logger.error(f"Error type: {type(e)}")
            return text  # Return original text if translation fails
    
    def format_srt_timestamp(self, seconds: float) -> str:
        """
        Convert seconds to SRT timestamp format (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def generate_srt_content(self, transcription_result: Dict) -> str:
        """
        Generate SRT subtitle content from Whisper transcription result.
        
        Args:
            transcription_result: Whisper transcription result
            
        Returns:
            SRT formatted subtitle content
        """
        srt_content = []
        
        for i, segment in enumerate(transcription_result['segments'], 1):
            start_time = self.format_srt_timestamp(segment['start'])
            end_time = self.format_srt_timestamp(segment['end'])
            text = segment['text'].strip()
            
            # Create SRT entry
            srt_entry = f"{i}\n{start_time} --> {end_time}\n{text}\n\n"
            srt_content.append(srt_entry)
        
        return ''.join(srt_content)
    
    def generate_subtitles(self, video_file_path: str, output_dir: str = "outputs") -> str:
        """
        Main processing method to generate subtitles from video.
        
        Args:
            video_file_path: Path to the input video file
            output_dir: Directory to save the subtitle file
            
        Returns:
            Path to the generated SRT file
        """
        audio_path = None
        try:
            # Generate unique filename for output
            video_name = Path(video_file_path).stem
            output_filename = f"{video_name}_{uuid.uuid4().hex[:8]}.srt"
            output_path = os.path.join(output_dir, output_filename)
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            logger.info(f"Starting subtitle generation for {video_file_path}")
            
            # Step 1: Extract audio
            audio_path, duration = self.extract_audio(video_file_path)
            
            # Step 2: Transcribe audio
            transcription_result = self.transcribe_audio(audio_path)
            
            # Step 3: Generate SRT content
            srt_content = self.generate_srt_content(transcription_result)
            
            # Step 4: Save SRT file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            logger.info(f"Subtitle file generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate subtitles: {e}")
            raise
        finally:
            # Clean up temporary audio file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                    logger.info("Temporary audio file cleaned up")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")
    
    def embed_soft_subtitles(self, video_path: str, srt_path: str, output_dir: str, language: str = "en") -> str:
        """
        Embed SRT subtitles as soft subtitles in video file.
        
        Args:
            video_path: Path to the input video file
            srt_path: Path to the SRT subtitle file
            output_dir: Directory to save the output video
            language: Language code for the subtitle track (e.g., 'en', 'es', 'fr')
            
        Returns:
            Path to the output video with embedded soft subtitles
        """
        try:
            # Generate output filename
            video_name = Path(video_path).stem
            video_ext = Path(video_path).suffix
            output_filename = f"{video_name}_with_subtitles{video_ext}"
            output_path = os.path.join(output_dir, output_filename)
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            logger.info(f"Embedding soft subtitles into {video_path}")
            
            # Use ffmpeg to embed soft subtitles
            # This creates a video with embedded subtitle track that can be toggled on/off
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    vcodec='copy',  # Copy video stream without re-encoding (faster)
                    acodec='copy',  # Copy audio stream without re-encoding
                    scodec='mov_text',  # Subtitle codec for MP4
                    **{f'metadata:s:s:0': f'language={language}'}
                )
                .run(overwrite_output=True, quiet=True)
            )
            
            logger.info(f"Soft subtitles embedded successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to embed soft subtitles: {e}")
            # Try alternative method for different containers
            try:
                logger.info("Trying alternative embedding method...")
                # Alternative method using command line approach
                video_input = ffmpeg.input(video_path)
                subtitle_input = ffmpeg.input(srt_path)
                
                output = ffmpeg.output(
                    video_input['v'], video_input['a'], subtitle_input,
                    output_path,
                    vcodec='copy',
                    acodec='copy', 
                    scodec='srt',
                    **{f'metadata:s:s:0': f'language={language}'}
                )
                ffmpeg.run(output, overwrite_output=True, quiet=True)
                
                logger.info(f"Soft subtitles embedded successfully (alternative method): {output_path}")
                return output_path
                
            except Exception as e2:
                logger.error(f"Alternative embedding method also failed: {e2}")
                raise Exception(f"Failed to embed subtitles: {e}")

    def generate_subtitles_with_video(self, video_file_path: str, output_dir: str = "outputs", 
                                    embed_subtitles: bool = False, language: str = "en") -> tuple:
        """
        Enhanced method to generate subtitles with optional video embedding and translation.
        
        Args:
            video_file_path: Path to the input video file
            output_dir: Directory to save output files
            embed_subtitles: Whether to create video with embedded soft subtitles
            language: Target language code for subtitles
            
        Returns:
            Tuple of (srt_file_path, video_with_subtitles_path or None)
        """
        audio_path = None
        try:
            # Generate unique filename for output
            video_name = Path(video_file_path).stem
            output_filename = f"{video_name}_{uuid.uuid4().hex[:8]}.srt"
            srt_output_path = os.path.join(output_dir, output_filename)
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            logger.info(f"Starting subtitle generation for {video_file_path} (target language: {language})")
            
            # Step 1: Extract audio
            audio_path, duration = self.extract_audio(video_file_path)
            
            # Step 2: Transcribe audio (always get English transcription first)
            transcription_result = self.transcribe_audio(audio_path)
            
            # Step 3: Generate SRT content (in English)
            srt_content = self.generate_srt_content(transcription_result)
            
            # Step 4: Translate SRT content if target language is not English
            if language != "en":
                logger.info(f"Translating subtitles from English to {language}")
                logger.info(f"Original SRT content preview: {srt_content[:200]}...")
                srt_content = self.translate_srt_content(srt_content, language)
                logger.info(f"Translated SRT content preview: {srt_content[:200]}...")
            else:
                logger.info("No translation needed - target language is English")
            
            # Step 5: Save SRT file
            with open(srt_output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            logger.info(f"SRT subtitle file generated successfully: {srt_output_path}")
            
            # Step 6: Optionally embed soft subtitles in video
            video_output_path = None
            if embed_subtitles:
                try:
                    video_output_path = self.embed_soft_subtitles(
                        video_file_path, srt_output_path, output_dir, language
                    )
                    logger.info(f"Video with embedded subtitles created: {video_output_path}")
                except Exception as e:
                    logger.warning(f"Failed to embed subtitles in video: {e}")
                    # Continue without embedded video - user still gets SRT file
            
            return srt_output_path, video_output_path
            
        except Exception as e:
            logger.error(f"Failed to generate subtitles: {e}")
            raise
        finally:
            # Clean up temporary audio file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                    logger.info("Temporary audio file cleaned up")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported video formats.
        
        Returns:
            List of supported file extensions
        """
        return ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    
    def validate_video_file(self, file_path: str) -> bool:
        """
        Validate if the file is a supported video format.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            True if file is supported, False otherwise
        """
        file_extension = Path(file_path).suffix.lower()
        return file_extension in self.get_supported_formats()
