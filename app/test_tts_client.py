import unittest
import os
import shutil
from app.tts_client import TTSClient
from app.config.settings import settings

class TestTTSClient(unittest.TestCase):
    def setUp(self):
        # Ensure the audio storage directory exists
        if os.path.exists(settings.AUDIO_STORAGE_PATH):
            # Clean up existing files but keep the directory
            for filename in os.listdir(settings.AUDIO_STORAGE_PATH):
                file_path = os.path.join(settings.AUDIO_STORAGE_PATH, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        # Create a test instance of TTSClient
        self.client = TTSClient()

        # Test dialogue data
        self.test_dialogue = [
            {"speaker": "HOST_A", "text": "Hello, this is a test message."},
            {"speaker": "HOST_B", "text": "Yes, this is a test for the TTS client."},
            {"speaker": "HOST_A", "text": "The test should verify the API integration."}
        ]

    # def tearDown(self):
    #     # Clean up any test files created
    #     for filename in os.listdir(settings.AUDIO_STORAGE_PATH):
    #         file_path = os.path.join(settings.AUDIO_STORAGE_PATH, filename)
    #         if os.path.isfile(file_path) and filename.startswith("segment_"):
    #             os.remove(file_path)

    def test_generate_audio_segments_with_real_api(self):
        """Test audio generation with real TTS API endpoint"""
        # Override the endpoint to use the real endpoint
        original_endpoint = self.client.endpoint
        self.client.endpoint = "http://192.168.1.16:8000/v1/audio/speech"

        try:
            # Call the method with the real API
            audio_files = self.client.generate_audio_segments(self.test_dialogue)

            # Verify we got audio files back
            self.assertEqual(len(audio_files), 3)

            # Verify each file was created and has content
            for i, filepath in enumerate(audio_files):
                self.assertTrue(os.path.exists(filepath))
                self.assertEqual(os.path.basename(filepath), f"segment_{i+1:03d}.mp3")
                self.assertGreater(os.path.getsize(filepath), 0)  # File should have content

        finally:
            # Restore original endpoint
            self.client.endpoint = original_endpoint

if __name__ == '__main__':
    unittest.main()