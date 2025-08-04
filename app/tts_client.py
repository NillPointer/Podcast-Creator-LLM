import requests
import os
import random
from typing import List, Dict
from app.config.settings import settings
from app.logger import setup_logger

logger = setup_logger('tts_client')

class TTSClient:
    def __init__(self):
        self.endpoint = f"{settings.TTS_API_HOST}{settings.TTS_API_PATH}"
        if settings.TTS_WAKEUP_ENDPOINT:
            try:
                requests.get(
                    settings.TTS_WAKEUP_ENDPOINT,
                    timeout=settings.TTS_TIMEOUT
                )
            except Exception:
                pass

    def generate_audio_segments(self, dialogue: List[Dict[str, str]],
                              global_index: int,
                              temp_dir: str) -> List[str]:
        """
        Generate audio segments for each dialogue line using TTS.

        Args:
            dialogue: List of dialogue segments with speaker and text
            global_index: For multi podcast processing
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

            exaggeration = 0.9
            cfg_weight = 0.3
            temperature = 0.8
            
            if i > 0:
                temperature = round(random.uniform(0.65,0.85),2)
                exaggeration = round(random.uniform(0.35, 0.9), 2)
                cfg_weight = round(random.uniform(0.35, 0.7), 2)

            # Select voice based on speaker
            voice = settings.HOST_A_VOICE if speaker == "HOST_A" else settings.HOST_B_VOICE

            # Prepare the payload for TTS API
            # Combination between OpenAI payload and TTS payload
            payload = {
                "model": settings.TTS_MODEL,  # Use configured model
                "text": text,
                "input": text,
                "voice_mode": "predefined",
                "predefined_voice_id": voice,
                "voice": voice,
                "output_format": "mp3",
                "response_format": "mp3",
                "temperature": 0.8,
                "exaggeration": exaggeration,
                "cfg_weight": cfg_weight
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