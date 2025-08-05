import requests
import json
import os
import time
from typing import List, Dict, Any
from app.config.settings import settings
from app.logger import setup_logger

logger = setup_logger('llm_client')

class LLMClient:
    def __init__(self):
        self.endpoint = f"{settings.LLM_API_HOST}/v1/chat/completions"

    def summarize_podcast_text(self, text_content: str) -> str:
        """
        Send text content to LLM for summarization if enabled.

        Args:
            text_content: The text content to summarize

        Returns:
            summarized text content

        Raises:
            Exception: If LLM request fails
        """
        if not settings.LLM_SUMMARY_ENABLED:
            return text_content

        logger.debug(f"Using Summarizer System Prompt: {settings.LLM_SUMMARY_SYSTEM_PROMPT}")

        # Prepare the payload for the LLM API with system and user messages
        payload = {
            "model": settings.LLM_MODEL,  # Use configured model
            "messages": [
                {"role": "system", "content": settings.LLM_SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": text_content}
            ],
            "temperature": settings.LLM_TEMPERATURE,
            "stream": False
        }
        
        try:
            # Send request to LLM endpoint
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=settings.LLM_TIMEOUT
            )

            response.raise_for_status()

            # Parse the response
            result = response.json()

            # Extract the content from the LLM response
            if "choices" in result and len(result["choices"]) > 0:
                summary_text = result["choices"][0]["message"]["content"]

                # Write debug to file in tmp
                if settings.DEBUG:
                    os.makedirs(settings.DEBUG_DIR, exist_ok=True)
                    timestamp = int(time.time())
                    file_path = os.path.join(settings.DEBUG_DIR, f"llm-summary-{timestamp}.txt")
                    with open(file_path, "w") as f:
                        f.write(summary_text)

                return summary_text
            else:
                raise Exception("Invalid LLM response format")
        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing LLM response: {str(e)}")

    def generate_podcast_script(self, 
    text_content: str,
    intro: bool, 
    outro:bool) -> List[Dict[str, str]]:
        """
        Send text content to LLM and get podcast script.

        Args:
            text_content: The text content to convert to podcast format
            intro: Enable Intro segment
            outro: Enable Outro segment

        Returns:
            List of dialogue segments with speaker and text

        Raises:
            Exception: If LLM request fails
        """
        # Prepare the system prompt with dynamic values
        podcast_system_prompt = settings.LLM_PODCAST_SYSTEM_PROMPT.replace("$INTRO_SEGMENT", settings.INTRO_SEGMENT_INSTRUCTIONS[intro])
        podcast_system_prompt = podcast_system_prompt.replace("$OUTRO_SEGMENT", settings.OUTRO_SEGMENT_INSTRUCTIONS[outro])

        logger.debug(f"Using Podcast System Prompt: {podcast_system_prompt}")

        # Prepare the payload for the LLM API with system and user messages
        payload = {
            "model": settings.LLM_MODEL,  # Use configured model
            "messages": [
                {"role": "system", "content": podcast_system_prompt},
                {"role": "user", "content": text_content}
            ],
            "temperature": settings.LLM_TEMPERATURE,
            "stream": False,
            "response_format": settings.LLM_PODCAST_RESPONSE_FORMAT  # Use the response format from settings
        }

        try:
            # Send request to LLM endpoint
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=settings.LLM_TIMEOUT
            )

            response.raise_for_status()

            # Parse the response
            result = response.json()

            # Extract the content from the LLM response
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]

                # Try to parse the JSON from the LLM response
                try:
                    # Extract JSON from the response (in case it's wrapped in markdown or other formatting)
                    if "```json" in content:
                        # Extract JSON between markdown code blocks
                        start = content.find("```json") + 7
                        end = content.find("```", start)
                        json_content = content[start:end].strip()
                    else:
                        json_content = content.strip()

                    parsed_response = json.loads(json_content)

                    # Write debug to file in tmp
                    if settings.DEBUG:
                        os.makedirs(settings.DEBUG_DIR, exist_ok=True)
                        timestamp = int(time.time())
                        file_path = os.path.join(settings.DEBUG_DIR, f"llm-podcast-{timestamp}.json")
                        with open(file_path, "w") as f:
                            json.dump(parsed_response, f, indent=4)

                    return parsed_response.get("dialogue", [])
                except json.JSONDecodeError:
                    raise Exception("Invalid LLM response format")
            else:
                raise Exception("Invalid LLM response format")

        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing LLM response: {str(e)}")

    def refine_podcast_script(self, dialogues: List[Dict[str,str]]) -> List[Dict[str, str]]:
        """
        Send dialogues to LLM for refinement.

        Args:
            dialogues: LLM generated dialogues

        Returns:
            List of refined dialogue segments

        Raises:
            Exception: If LLM request fails
        """
        if not settings.LLM_PODCAST_REFINER_ENABLED:
            return dialogues

        logger.debug(f"Using Podcast System Prompt: {settings.LLM_PODCAST_REFINER_SYSTEM_PROMPT}")
        dialogues_json = json.dumps(dialogues, indent=4)

        # Prepare the payload for the LLM API with system and user messages
        payload = {
            "model": settings.LLM_MODEL,  # Use configured model
            "messages": [
                {"role": "system", "content": settings.LLM_PODCAST_REFINER_SYSTEM_PROMPT},
                {"role": "user", "content": dialogues_json}
            ],
            "temperature": settings.LLM_TEMPERATURE,
            "stream": False,
            "response_format": settings.LLM_PODCAST_RESPONSE_FORMAT  # Use the response format from settings
        }

        try:
            # Send request to LLM endpoint
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=settings.LLM_TIMEOUT
            )

            response.raise_for_status()

            # Parse the response
            result = response.json()

            # Extract the content from the LLM response
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]

                # Try to parse the JSON from the LLM response
                try:
                    # Extract JSON from the response (in case it's wrapped in markdown or other formatting)
                    if "```json" in content:
                        # Extract JSON between markdown code blocks
                        start = content.find("```json") + 7
                        end = content.find("```", start)
                        json_content = content[start:end].strip()
                    else:
                        json_content = content.strip()

                    parsed_response = json.loads(json_content)

                    # Write debug to file in tmp
                    if settings.DEBUG:
                        os.makedirs(settings.DEBUG_DIR, exist_ok=True)
                        timestamp = int(time.time())
                        file_path = os.path.join(settings.DEBUG_DIR, f"llm-podcast-refined-{timestamp}.json")
                        with open(file_path, "w") as f:
                            json.dump(parsed_response, f, indent=4)

                    return parsed_response.get("dialogue", [])
                except json.JSONDecodeError:
                    raise Exception("Invalid LLM response format")
            else:
                raise Exception("Invalid LLM response format")

        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing LLM response: {str(e)}")