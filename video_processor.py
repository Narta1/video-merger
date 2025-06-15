import os
import logging
import subprocess
import json
from pathlib import Path

class VideoProcessor:
    """Class to handle video processing using FFmpeg"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error("FFmpeg not found. Please install FFmpeg.")
            return False
    
    def get_audio_duration(self, audio_path):
        """Get audio duration in seconds"""
        try:
            # Use ffprobe directly via subprocess for more reliable results
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_format', '-show_streams', audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)
            
            # Try to get duration from format first, then from streams
            if 'format' in probe_data and 'duration' in probe_data['format']:
                duration = float(probe_data['format']['duration'])
                return duration
            elif 'streams' in probe_data and len(probe_data['streams']) > 0:
                for stream in probe_data['streams']:
                    if 'duration' in stream:
                        duration = float(stream['duration'])
                        return duration
            
            self.logger.error("Could not find duration in probe data")
            return None
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"ffprobe command failed: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing ffprobe output: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting audio duration: {str(e)}")
            return None
    
    def get_image_dimensions(self, image_path):
        """Get image dimensions"""
        try:
            # Use ffprobe directly via subprocess for more reliable results
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_streams', image_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)
            
            # Look for video stream (images are treated as single-frame video)
            if 'streams' in probe_data:
                for stream in probe_data['streams']:
                    if stream.get('codec_type') == 'video':
                        width = int(stream.get('width', 0))
                        height = int(stream.get('height', 0))
                        if width > 0 and height > 0:
                            return width, height
            
            self.logger.error("Could not find valid dimensions in probe data")
            return None, None
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"ffprobe command failed for image: {e}")
            return None, None
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing ffprobe output for image: {e}")
            return None, None
        except Exception as e:
            self.logger.error(f"Error getting image dimensions: {str(e)}")
            return None, None
    
    def create_video(self, image_path, audio_path, output_path, video_codec='libx264', audio_codec='aac'):
        """
        Create video by combining image and audio
        
        Args:
            image_path: Path to input image
            audio_path: Path to input audio
            output_path: Path to output video
            video_codec: Video codec to use (default: libx264)
            audio_codec: Audio codec to use (default: aac)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Check if FFmpeg is available
            if not self.check_ffmpeg():
                return False, "FFmpeg is not installed or not available"
            
            # Validate input files
            if not os.path.exists(image_path):
                return False, f"Image file not found: {image_path}"
            
            if not os.path.exists(audio_path):
                return False, f"Audio file not found: {audio_path}"
            
            # Get audio duration
            duration = self.get_audio_duration(audio_path)
            if duration is None:
                return False, "Could not determine audio duration"
            
            self.logger.info(f"Creating video with duration: {duration} seconds")
            
            # Get image dimensions for scaling
            width, height = self.get_image_dimensions(image_path)
            if width is None or height is None:
                # Use default dimensions if cannot determine
                width, height = 1280, 720
                self.logger.warning(f"Could not determine image dimensions, using default: {width}x{height}")
            
            # Ensure dimensions are even (required for some codecs)
            width = width - (width % 2)
            height = height - (height % 2)
            
            self.logger.info(f"Using dimensions: {width}x{height}")
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Build FFmpeg command using subprocess
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file if exists
                '-loop', '1',  # Loop the image
                '-i', image_path,  # Input image
                '-i', audio_path,  # Input audio
                '-c:v', video_codec,  # Video codec
                '-c:a', audio_codec,  # Audio codec
                '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                '-r', '25',  # Frame rate
                '-vf', f'scale={width}:{height}',  # Scale video
                '-t', str(duration),  # Duration (match audio length)
                '-shortest',  # Stop when shortest input ends
                output_path
            ]
            
            # Run the FFmpeg command
            self.logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = f"FFmpeg failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # Verify output file was created
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                self.logger.info(f"Video created successfully: {output_path}")
                return True, "Video created successfully"
            else:
                return False, "Output file was not created or is empty"
        
        except subprocess.CalledProcessError as e:
            error_message = f"FFmpeg process error: {e}"
            self.logger.error(f"FFmpeg process failed: {e}")
            return False, error_message
        
        except Exception as e:
            self.logger.error(f"Unexpected error in create_video: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
    
    def cleanup_file(self, file_path):
        """Safely remove a file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"Cleaned up file: {file_path}")
                return True
        except Exception as e:
            self.logger.error(f"Error cleaning up file {file_path}: {str(e)}")
        return False
