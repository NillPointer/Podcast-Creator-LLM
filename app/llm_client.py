import requests
import json
from typing import List, Dict, Any
from app.config.settings import settings
from app.logger import setup_logger

logger = setup_logger('llm_client')

class LLMClient:
    def __init__(self):
        self.endpoint = f"{settings.LLM_ENDPOINT}/v1/chat/completions"
        self.system_prompt_template = settings.LLM_SYSTEM_PROMPT

    def generate_podcast_script(self, text_content: str, host_a_name: str, host_b_name: str) -> List[Dict[str, str]]:
        """
        Send text content to LLM and get podcast script.

        Args:
            text_content: The text content to convert to podcast format

        Returns:
            List of dialogue segments with speaker and text

        Raises:
            Exception: If LLM request fails
        """
        # Prepare the system prompt with dynamic values
        system_prompt = self.system_prompt_template.replace("$HOST_A_NAME", host_a_name)
        system_prompt = system_prompt.replace("$HOST_B_NAME", host_b_name)
        system_prompt = system_prompt.replace("$INTRO_ENABLED", settings.INTRO_ENABLED)
        system_prompt = system_prompt.replace("$OUTRO_ENABLED", settings.OUTRO_ENABLED)

        # Prepare the payload for the LLM API with system and user messages
        payload = {
            "model": settings.LLM_MODEL,  # Use configured model
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_content}
            ],
            "temperature": settings.LLM_TEMPERATURE,
            "stream": False,
            "response_format": settings.LLM_RESPONSE_FORMAT  # Use the response format from settings
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
                    return parsed_response.get("dialogue", [])
                except json.JSONDecodeError:
                    raise Exception("Invalid LLM response format")
            else:
                raise Exception("Invalid LLM response format")

        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing LLM response: {str(e)}")