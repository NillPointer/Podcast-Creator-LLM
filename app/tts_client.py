import requests
import os
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
                              job: Dict,
                              temp_dir: str) -> List[str]:
        """
        Generate audio segments for each dialogue line using TTS.

        Args:
            dialogue: List of dialogue segments with speaker and text
            job: Job process
            temp_dir: Temporary directory path for storing audio segments

        Returns:
            List of file paths to generated audio segments

        Raises:
            Exception: If TTS request fails
        """

        audio_files = []
        progress_increment = 40 / len(dialogue)

        for i, segment in enumerate(dialogue):
            speaker = segment["speaker"]
            text = segment["text"]

            # Select parameters based on speaker
            voice = settings.HOST_A_VOICE if speaker == "HOST_A" else settings.HOST_B_VOICE
            temperature = settings.HOST_A_TEMPERATURE if speaker == "HOST_A" else settings.HOST_B_TEMPERATURE
            exaggeration = settings.HOST_A_EXAGGERATION if speaker == "HOST_A" else settings.HOST_B_EXAGGERATION
            cfg_weight = settings.HOST_A_CFG if speaker == "HOST_A" else settings.HOST_B_CFG

            # Prepare the payload for TTS API
            # Combination between OpenAI payload and TTS payload
            payload = {
                "model": settings.TTS_MODEL,  # Use configured model
                "text": text,
                "input": text,
                "voice_mode": "predefined",
                "predefined_voice_id": voice,
                "voice": voice,
                "output_format": "wav",
                "response_format": "wav",
                "temperature": temperature,
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
                filename = f"segment_{i+1:03d}.wav"
                filepath = os.path.join(temp_dir, filename)

                # Save the audio data
                with open(filepath, "wb") as f:
                    f.write(response.content)

                # Write debug to file in tmp
                if settings.DEBUG:
                    os.makedirs(settings.DEBUG_DIR, exist_ok=True)
                    file_path = os.path.join(settings.DEBUG_DIR, filename)
                    with open(file_path, "wb") as f:
                        f.write(response.content)

                audio_files.append(filepath)
                job["progress"] += progress_increment

            except requests.exceptions.RequestException as e:
                raise Exception(f"TTS API request failed for segment {i}: {str(e)}")
            except Exception as e:
                raise Exception(f"Error generating audio for segment {i}: {str(e)}")

        return audio_files