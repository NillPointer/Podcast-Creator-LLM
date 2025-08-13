import os
from pydub import AudioSegment
from typing import List
from app.config.settings import settings
from app.logger import setup_logger

logger = setup_logger('audio_stitcher')

class AudioStitcher:
    def __init__(self):
        self.storage_path = settings.AUDIO_STORAGE_PATH
    
    def normalize_audio(self, audio_segment: AudioSegment, reference_audio: AudioSegment = None) -> AudioSegment:
        """
        Normalize audio segment to match reference audio characteristics.
        
        Args:
            audio_segment: The audio segment to normalize
            reference_audio: The reference audio segment to match against (if None, use first segment)
            
        Returns:
            Normalized audio segment
        """
        try:
            # If no reference provided, use the audio segment itself as reference
            if reference_audio is None:
                reference_audio = audio_segment
            
            # Normalize loudness to match reference
            # Get the loudness of the reference audio
            reference_loudness = reference_audio.dBFS
            
            # Get the loudness of the current audio
            current_loudness = audio_segment.dBFS
            
            # Calculate the difference
            loudness_diff = reference_loudness - current_loudness
            
            # Apply gain to match reference loudness
            normalized_audio = audio_segment.apply_gain(loudness_diff)
            
            # Additional normalization: ensure sample rate consistency
            if normalized_audio.frame_rate != reference_audio.frame_rate:
                normalized_audio = normalized_audio.set_frame_rate(reference_audio.frame_rate)
            
            # Ensure number of channels consistency
            if normalized_audio.channels != reference_audio.channels:
                if reference_audio.channels == 1:  # Reference is mono
                    normalized_audio = normalized_audio.set_channels(1)
                elif reference_audio.channels == 2:  # Reference is stereo
                    normalized_audio = normalized_audio.set_channels(2)
            
            logger.debug(f"Normalized audio: loudness adjusted by {loudness_diff:.2f}dB, "
                        f"sample rate: {normalized_audio.frame_rate}Hz, "
                        f"channels: {normalized_audio.channels}")
            
            return normalized_audio
            
        except Exception as e:
            logger.warning(f"Failed to normalize audio: {str(e)}. Using original audio.")
            return audio_segment
    
    def stitch_audio_segments(self, audio_files: List[str], output_filename: str) -> str:
        """
        Stitch together audio segments into a single podcast file with normalization.
        
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
            
            # Load first audio file to use as reference
            reference_audio = None
            if audio_files:
                first_file = audio_files[0]
                if os.path.exists(first_file):
                    reference_audio = AudioSegment.from_file(file=first_file, format="wav")
                    combined += reference_audio
                    logger.debug(f"Using {first_file} as reference for normalization")
                else:
                    raise FileNotFoundError(f"Audio file not found: {first_file}")
            
            # Process remaining audio files with normalization
            for audio_file in audio_files[1:]:
                if os.path.exists(audio_file):
                    # Load the audio file
                    audio_segment = AudioSegment.from_file(file=audio_file, format="wav")
                    
                    # Normalize the audio segment to match reference
                    normalized_segment = self.normalize_audio(audio_segment, reference_audio)
                    
                    # Add to combined audio
                    combined += normalized_segment
                else:
                    raise FileNotFoundError(f"Audio file not found: {audio_file}")
            
            # Export the combined audio
            combined.export(output_path, format="wav")
            logger.info(f"Successfully stitched audio into {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to stitch audio segments: {str(e)}")
            raise Exception(f"Failed to stitch audio segments: {str(e)}")
