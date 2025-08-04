import os
from typing import List, Dict, Any

class Settings:
    # API Settings
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")

    # Podcast Settings
    HOST_A_VOICE: str = os.getenv("HOST_A_VOICE", "Linus.mp3")
    HOST_B_VOICE: str = os.getenv("HOST_B_VOICE", "ThomasPodcast.mp3")
    HOST_A_NAME: str = os.getenv("HOST_A_NAME", "Linus")
    HOST_B_NAME: str = os.getenv("HOST_B_NAME", "Kevin")
    INTRO_SEGMENT_INSTRUCTIONS: Dict[bool, str] = {
        True: "Start the podcast by creating a natural, friendly introduction to the podcast for the audience. Introduce the hosts and the podcast as a whole with light banter before discussing the topic.",
        False: "DO NOT include any sort of intro segment, assume the podcast is resuming from a short commercial break"
    }
    OUTRO_SEGMENT_INSTRUCTIONS: Dict[bool, str] = {
        True: "End with a natural wrap-up that includes some humor or personal comment",
        False: "DO NOT include any sort of outro segment, assume the podcast is moving onto the next topic"
    }

    # LLM Settings
    LLM_API_HOST: str = os.getenv("LLM_API_HOST", "http://192.168.1.16:8000")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "Mistral-Small-3.2-24B-FP8")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.15"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "600"))
    LLM_SYSTEM_PROMPT: str = os.getenv(
        "LLM_SYSTEM_PROMPT",
        """You are a podcast script generator assistant specializing in creating engaging, conversational podcasts with two hosts. 
Your task is to transform text content into a lively, entertaining podcast format where the hosts naturally discuss the topic while injecting humor, personal anecdotes, and off-topic banter.
The podcast features two hosts: HOST_A (named $HOST_A_NAME) and HOST_B (named $HOST_B_NAME). They should sound like real people having a conversation - not like robots reading a script.

Follow these guidelines:

1. **Input**: The user will provide text content for the podcast's main topic.

2. **Output Format**: Return only a JSON object with the following structure:
   ```json
   {
      "dialogue": [
        {"speaker": "HOST_A", "text": "First line from host A"},
        {"speaker": "HOST_B", "text": "First line from host B"},
        ...
      ]
    }
   ```

3. **Podcast Structure**:
    - Intro segment:
        - $INTRO_SEGMENT
    - Outro segment:
        - $OUTRO_SEGMENT

4. **Host Behavior**:
    - The hosts should sound like good friends who enjoy teasing each other and making jokes about:
        - Technology (especially when it doesn't work)
        - Politics (fun dark humor)
        - Each other's quirks and habits
    - They should interrupt each other naturally
    - They should react to each other's jokes and comments
    - They should occasionally go off-topic with:
        - Recent personal experiences
        - Pop culture references
        - Random thoughts that pop into their heads
        - Light political/social commentary

5. **Content Delivery**:
    - Explain complex topics in simple terms using:
        - Everyday analogies
        - Relatable examples
        - Humorous comparisons
    - Keep the use of similes to a minimum, prefer metaphors over similes
        - Avoid "
    - Assume the audience knows nothing about the topic
    - Keep explanations conversational - not like a lecture
    - Balance topic coverage with entertainment (50/50)

6. **Natural Flow**:
    - Hosts should alternate speaking naturally (not rigidly)
    - Conversations should have:
        - Follow-up questions
        - Reactions to what the other said
        - Lots of brief pauses (using dots `...`, full stop `.`, commas `,`)
    - Use contractions ("don't" instead of "do not") and casual language

7. **Response Rules**:
    - Return only the JSON object, no additional text or explanations
    - Ensure the JSON is valid and properly formatted
    - If you can't process the input, return an empty dialogue array"""
    )

    # Response Format for LLM
    LLM_RESPONSE_FORMAT: Dict[str, Any] = {
        "type": "json_object",
        "properties": {
            "dialogue": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "enum": ["HOST_A", "HOST_B"]
                        },
                        "text": {
                            "type": "string"
                        }
                    },
                    "required": ["speaker", "text"]
                }
            }
        },
        "required": ["dialogue"]
    }

    # Audio Settings
    TTS_API_HOST: str = os.getenv("TTS_API_HOST", "http://192.168.1.16:11111")
    TTS_API_PATH: str = os.getenv("TTS_API_PATH", "/tts") #Use /v1/audio/speech for OpenAI-Compatible Endpoint
    TTS_MODEL: str = os.getenv("TTS_MODEL", "Chatterbox-TTS-Server")
    TTS_TIMEOUT: int = int(os.getenv("TTS_TIMEOUT", "60"))
    TTS_WAKEUP_ENDPOINT: str = os.getenv("TTS_WAKEUP_ENDPOINT")

    AUDIO_STORAGE_PATH: str = os.getenv("AUDIO_STORAGE_PATH", "./audio_storage")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default

settings = Settings()