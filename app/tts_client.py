import requests
import os
from typing import List, Dict
from app.config.settings import settings
from app.logger import setup_logger

logger = setup_logger('tts_client')

class TTSClient:
    def __init__(self):
        self.endpoint = f"{settings.TTS_ENDPOINT}/v1/audio/speech"

    def generate_audio_segments(self, dialogue: List[Dict[str, str]],
                              global_index: int,
                              speaker_a_voice: str,
                              speaker_b_voice: str,
                              temp_dir: str) -> List[str]:
        """
        Generate audio segments for each dialogue line using TTS.

        Args:
            dialogue: List of dialogue segments with speaker and text
            global_index: For multi podcast processing
            speaker_a_voice: Voice ID for speaker A
            speaker_b_voice: Voice ID for speaker B
            temp_dir: Temporary directory path for storing audio segments

        Returns:
            List of file paths to generated audio segments

        Raises:
            Exception: If TTS request fails
        """

        audio_files = []

        for i, segment in enumerate(dialogue):
            speaker = segment["speaker"]
            text = segment["text"]

            # Select voice based on speaker
            voice = speaker_a_voice if speaker == "HOST_A" else speaker_b_voice

            # Prepare the payload for TTS API
            payload = {
                "model": settings.TTS_MODEL,  # Use configured model
                "input": text,
                "voice": voice+".wav",
                "response_format": "mp3"
            }

            try:
                # Send request to TTS endpoint
                response = requests.post(
                    self.endpoint,
                    json=payload,
                    timeout=settings.TTS_TIMEOUT
                )

                response.raise_for_status()

                # Save the audio file
                filename = f"segment_{global_index}_{i+1:03d}.mp3"
                filepath = os.path.join(temp_dir, filename)

                # Save the audio data
                with open(filepath, "wb") as f:
                    f.write(response.content)

                audio_files.append(filepath)

            except requests.exceptions.RequestException as e:
                raise Exception(f"TTS API request failed for segment {i}: {str(e)}")
            except Exception as e:
                raise Exception(f"Error generating audio for segment {i}: {str(e)}")

        return audio_files