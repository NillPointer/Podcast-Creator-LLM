import os
from pydub import AudioSegment
from typing import List
from app.config.settings import settings
from app.logger import setup_logger

logger = setup_logger('audio_stitcher')

class AudioStitcher:
    def __init__(self):
        self.storage_path = settings.AUDIO_STORAGE_PATH
    
    def stitch_audio_segments(self, audio_files: List[str], output_filename: str) -> str:
        """
        Stitch together audio segments into a single podcast file.
        
        Args:
            audio_files: List of file paths to audio segments
            output_filename: Name for the output file
            
        Returns:
            Path to the stitched audio file
            
        Raises:
            Exception: If audio stitching fails
        """
        logger.info(f"Stitching {len(audio_files)} audio segments into {output_filename}")
        try:
            # Ensure storage directory exists
            os.makedirs(self.storage_path, exist_ok=True)
            
            # Create output file path
            output_path = os.path.join(self.storage_path, output_filename)
            
            # Initialize empty audio segment
            combined = AudioSegment.empty()
            
            # Concatenate all audio segments
            for audio_file in audio_files:
                if os.path.exists(audio_file):
                    # Load the audio file
                    audio_segment = AudioSegment.from_mp3(audio_file)
                    combined += audio_segment
                else:
                    raise FileNotFoundError(f"Audio file not found: {audio_file}")
            
            # Export the combined audio
            combined.export(output_path, format="mp3")
            logger.info(f"Successfully stitched audio into {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to stitch audio segments: {str(e)}")
            raise Exception(f"Failed to stitch audio segments: {str(e)}")
