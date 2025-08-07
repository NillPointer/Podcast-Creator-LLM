import requests
import json
import random
import re
import os
import time
from typing import List, Dict, Any
from app.config.settings import settings
from app.logger import setup_logger

logger = setup_logger('llm_client')

class LLMClient:
    def __init__(self):
        self.endpoint = f"{settings.LLM_API_HOST}/v1/chat/completions"
    
    def _make_llm_request(self, 
    system_prompt: str, 
    user_content: str, 
    temperature: float = settings.LLM_TEMPERATURE) -> str:
        """
        Helper function to make LLM API requests with consistent error handling.
        
        Args:
            system_prompt: The system prompt for the LLM
            user_content: The user content to send to the LLM
            temperature: Temperature setting for the LLM
            
        Returns:
            Response text from the LLM
            
        Raises:
            Exception: If LLM request fails
        """
        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": temperature,
            "stream": False
        }
        
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=settings.LLM_TIMEOUT
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"].strip()
                
                # Write debug to file in tmp
                if settings.DEBUG:
                    os.makedirs(settings.DEBUG_DIR, exist_ok=True)
                    timestamp = int(time.time())
                    file_path = os.path.join(settings.DEBUG_DIR, f"llm-podcast-{timestamp}.txt")
                    with open(file_path, "w") as f:
                        f.write(content)
                
                return content
            else:
                raise Exception("Invalid LLM response format")
        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing LLM response: {str(e)}")
    
    def _remove_xml(self, text: str) -> str:
        # Remove XML tags and everything inside them
        return re.sub(r'<.*?>.*?</.*?>', '', text, flags=re.DOTALL).strip()

    def _llm_chat(self, 
    system_prompt: str, 
    user_content: str, 
    llm_chat: List[Dict[str, str]], 
    temperature: float = settings.LLM_TEMPERATURE) -> (str, List[Dict[str, str]]):
        """
        Helper function to make LLM API requests with consistent error handling.
        
        Args:
            system_prompt: The system prompt for the LLM
            user_content: The user content to send to the LLM
            llm_chat: User - Assistant chat thus far
            temperature: Temperature setting for the LLM
            
        Returns:
            Response text from the LLM
            
        Raises:
            Exception: If LLM request fails
        """

        if system_prompt:
            llm_chat.append({"role": "system", "content": system_prompt})

        llm_chat.append({"role": "user", "content": user_content})

        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
            ],
            "temperature": temperature,
            "stream": False
        }

        payload["messages"].extend(llm_chat)

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=settings.LLM_TIMEOUT
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"].strip()
                llm_chat[-1]["content"] = self._remove_xml(llm_chat[-1]["content"])
                llm_chat.append({"role": "assistant", "content": content})
                
                # Write debug to file in tmp
                if settings.DEBUG:
                    os.makedirs(settings.DEBUG_DIR, exist_ok=True)
                    timestamp = int(time.time())
                    file_path = os.path.join(settings.DEBUG_DIR, f"llm-chat-{timestamp}.txt")
                    with open(file_path, "w") as f:
                        f.write(content)
                
                return content, llm_chat
            else:
                raise Exception("Invalid LLM response format")
        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing LLM response: {str(e)}")

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
        return self._make_llm_request(settings.LLM_SUMMARY_SYSTEM_PROMPT, text_content, settings.LLM_TEMPERATURE)

    def generate_podcast_script(self, topics_text: List[str], job: Dict) -> List[Dict[str, str]]:
        """
        Generate podcast script by alternating between HOST_A and HOST_B perspectives.
        
        Args:
            topics_text: List of text content topics to convert to podcast format

        Returns:
            List of dialogue segments with speaker and text

        Raises:
            Exception: If LLM request fails
        """
        # Start with HOST_A as the first speaker
        current_speaker = "HOST_A"
        dialogue = []
        host_a_chat = []
        host_b_chat = []

        host_a_prompt = settings.HOST_PODCAST_PROMPT.replace("$HOST_NAME", settings.HOST_A_NAME)
        host_a_prompt = host_a_prompt.replace("$COHOST_NAME", settings.HOST_B_NAME)
        host_a_prompt = host_a_prompt.replace("$HOST_PERSONALITY", settings.HOST_A_PERSONALITY)

        host_b_prompt = settings.HOST_PODCAST_PROMPT.replace("$HOST_NAME", settings.HOST_B_NAME)
        host_b_prompt = host_b_prompt.replace("$COHOST_NAME", settings.HOST_A_NAME)
        host_b_prompt = host_b_prompt.replace("$HOST_PERSONALITY", settings.HOST_B_PERSONALITY)
        current_speaker = "HOST_A"

        exchanges_per_topic = []
        total_exchanges = 0

        for i in range(len(topics_text)):
            num_exchanges = random.randint(settings.TOPIC_EXCHANGE_MIN, settings.TOPIC_EXCHANGE_MAX)
            exchanges_per_topic.append(num_exchanges)
            total_exchanges += num_exchanges
        
        progress_increment = 40 / total_exchanges

        try:
            # Process each topic in the list
            for i, topic_content in enumerate(topics_text):
                # Summarize the topic content first
                summary = self.summarize_podcast_text(topic_content)
                num_exchanges = exchanges_per_topic[i]
                
                # Get first response from HOST_A
                topic_context = f"""
                <system>
                {host_a_prompt if current_speaker == "HOST_A" else host_b_prompt}
                </system>

                <topic>
                {summary}
                </topic>

                <instruction>
                {settings.INTRO_SEGMENT_INSTRUCTIONS[i == 0]}
                </instruction>
                """
                if current_speaker == "HOST_A":
                    content, host_b_chat = self._llm_chat("", topic_context, host_b_chat)
                else:
                    content, host_a_chat = self._llm_chat("", topic_context, host_a_chat)
                
                # Add first HOST_A response to dialogue
                dialogue.append({"speaker": current_speaker, "text": content})
                current_speaker = "HOST_B" if current_speaker == "HOST_A" else "HOST_A"
                
                # Alternate between HOST_A and HOST_B for the remaining exchanges
                for j in range(num_exchanges):

                    chat_content = f"""
                    <system>
                    {host_a_prompt if current_speaker == "HOST_A" else host_b_prompt}
                    </system>

                    {content}
                    """

                    if j >= (num_exchanges - 2):
                        instruction = f"""
                        Naturally end the conversation about the current topic.
                        You will be given the next topic to cover for the podcast in the next instruction.
                        Say something like "alright, it's time to move onto another topic" in a natural way.
                        """

                        if i == (len(topics_text) - 1):
                            instruction = f"""
                            The podcast is ending now, say your goodbyes and thank the audience for tuning in.
                            """

                        chat_content = f"""
                        <system>
                        {host_a_prompt if current_speaker == "HOST_A" else host_b_prompt}
                        </system>

                        <instruction>
                        {instruction}
                        </instruction>

                        {content}
                        """

                    if current_speaker == "HOST_A":
                        content, host_b_chat = self._llm_chat("", chat_content, host_b_chat)
                    else:
                        content, host_a_chat = self._llm_chat("", chat_content, host_a_chat)
                    dialogue.append({"speaker": current_speaker, "text": content})
                    current_speaker = "HOST_B" if current_speaker == "HOST_A" else "HOST_A"
                    job["progress"] += progress_increment
            
            # Write debug to file in tmp
            if settings.DEBUG:
                os.makedirs(settings.DEBUG_DIR, exist_ok=True)
                timestamp = int(time.time())
                file_path = os.path.join(settings.DEBUG_DIR, f"llm-podcast-{timestamp}.json")
                with open(file_path, "w") as f:
                    json.dump(dialogue, f, indent=4)

            return dialogue
            
        except Exception as e:
            raise Exception(f"Error generating podcast script: {str(e)}")
