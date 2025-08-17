from __future__ import annotations
import re

from typing import Literal, Optional, Tuple

from langchain_core.messages import HumanMessage, AIMessage

from app.config.settings import settings
from app.graphs.types import PodcastState, Speaker
from app.graphs.xml_utils import compose_prompt_with_topic_instruction
from app.graphs.llm_utils import create_llm, invoke_llm
from app.progress import increment_progress

from app.logger import setup_logger

logger = setup_logger("graph_nodes")

_summarizer_llm = create_llm(temperature=settings.LLM_SUMMARY_TEMPERATURE)
_chat_llm = create_llm(
    temperature=settings.LLM_HOST_TEMPERATURE, 
    extra_body={
        "frequency_penalty": 1.5,
        "presence_penalty": 2.0
    })

# --- Internal helpers ---------------------------------------------------------

# Managing the instructions throughout the podcast lifecycle
def _get_current_instruction(state: PodcastState) -> str:
    topic_index = state["topic_index"]
    exchange_index = state.get("exchange_index", 0)
    num_exchanges = state["exchanges_per_topic"][topic_index]
    exchange_percentage = exchange_index / (num_exchanges - 1)

    is_first_exchange = exchange_index == 0
    is_second_exchange = exchange_index == 1
    is_first_topic = topic_index == 0
    is_last_topic = topic_index == len(state["topics"]) -1
    
    # First chat exchange, add the topic and intro
    if is_first_exchange:
        if is_first_topic:
            return (
                "Welcome the listeners to the podcast. "
                "Then introduce yourself. "
                "Then say a quip or two about the podcast itself. "
                "Then stop and offer the co-host to introduce themselves."
            )
        else:
            return (
                "Smoothly transition to the new podcast topic from "
                "the previous topic in a natural way. "
                "Do not abruptly stop the current discussion with the co-host, "
                "finish it gracefully then introduce the new topic of discussion."
            )

    if is_first_topic and is_second_exchange:
        return (
            "Humorously introduce yourself to the listeners, "
            "avoid directly stating your personality traits."
        )

    # Last exchange of this topic: add closing instruction
    if is_last_topic and exchange_index >= (num_exchanges - 2):
        return (
            "The podcast is ending now, "
            "conclude the current conversation naturally, "
            "say your goodbyes and thank the audience for tuning in."
        )
    
    if exchange_percentage < 0.7:
        return (
            "You are in the factual phase currently.\n"
            "Focus on explaining the topic to the listeners.\n"
            "Reference the topic often, explain complicated terms and concepts from the topic "
            "in a simple manner.\n"
            "Remember, you want to educate the listeners who don't know this topic well, be thorough "
            "and reference the topic often.\n"
            "Keep it short and conversational, we don't want paragraphs."
        )
    else:
        return (
            "You are in the opinion phase currently.\n"
            "Introduce your own ideas and opinions about the topic.\n"
            "Raise questions that are not covered in the topic itself.\n"
            "What are there any similarity with existing things and how do they compare to this topic?\n"
            "Keep it short and conversational, we don't want paragraphs."
        )


def _select_route_for_speaker(state: PodcastState) -> Tuple[Speaker, str, list, str]:
    """Return (current_speaker, system_prompt, history, history_key)."""
    current_speaker: Speaker = state.get("current_speaker", "HOST_A")
    if current_speaker == "HOST_A":
        return current_speaker, state["host_a_system_prompt"], list(state.get("host_a_history", [])), "host_a_history"
    return current_speaker, state["host_b_system_prompt"], list(state.get("host_b_history", [])), "host_b_history"


def _apply_llm_turn(
    state: PodcastState,
    user_text: str,
) -> PodcastState:
    """
    Shared logic for a single turn:
    - Route to correct system prompt/history by current speaker
    - Invoke LLM
    - Update history and dialogue
    - Flip speaker and set last_content
    """
    current_speaker, system_prompt, history, history_key = _select_route_for_speaker(state)

    content = invoke_llm(system_prompt, history, user_text, _chat_llm)
    logger.debug(f"Speaker: {'HOST_B' if current_speaker == 'HOST_A' else 'HOST_A'} text: {content}")

    # Remove any XML tagged content
    content = re.sub(r'<.*?>.*?</.*?>', '', content, flags=re.DOTALL).strip()

    # Update history and dialogue
    history.append(HumanMessage(content=user_text))
    history.append(AIMessage(content=content))

    updated: PodcastState = {history_key: history}

    dialogue = list(state.get("dialogue", []))
    dialogue.append({"speaker": current_speaker, "text": content})

    # Advance indices and flip speaker
    next_speaker: Speaker = "HOST_B" if current_speaker == "HOST_A" else "HOST_A"

    result: PodcastState = {
        **updated,
        "dialogue": dialogue,
        "current_speaker": next_speaker,
        "last_content": content,
    }

    result["exchange_index"] = state.get("exchange_index", 0) + 1
    # Update progress centrally
    job_id = state.get("job_id")
    if job_id:
        increment_progress(job_id, state.get("progress_increment", 0.0))
    return result


# --- Nodes ---------------------------------------------------------------------------------------

def prepare_topic(state: PodcastState) -> PodcastState:
    from app.graphs.llm_utils import summarize_topic
    topics = state["topics"]
    i = state.get("topic_index", 0)
    topic_summary = summarize_topic(topics[i], _summarizer_llm)
    new_state: PodcastState = {"topic_summary": topic_summary, "exchange_index": 0}
    return new_state

def chat_exchange(state: PodcastState) -> PodcastState:
    topic_index = state["topic_index"]
    exchange_index = state.get("exchange_index", 0)
    num_exchanges = state["exchanges_per_topic"][topic_index]

    # Build content for this turn
    content_seed = state.get("last_content", "")
    instruction: Optional[str] = None
    topic: Optional[str] = None
    exchange_countdown = num_exchanges - exchange_index

    instruction = _get_current_instruction(state)

    # First chat exchange, add the topic
    if exchange_index == 0:
        topic = state['topic_summary']
        
    chat_content = compose_prompt_with_topic_instruction(
        content_seed, 
        topic, 
        instruction,
        exchange_countdown)

    # Exchanges should count towards progress, and advance the exchange index by 1
    return _apply_llm_turn(
        state,
        chat_content,
    )


def should_continue_exchange(state: PodcastState) -> Literal["chat_exchange", "finish_topic"]:
    i = state["topic_index"]
    j = state.get("exchange_index", 0)
    num_exchanges = state["exchanges_per_topic"][i]
    return "chat_exchange" if j < num_exchanges else "finish_topic"


def finish_topic(state: PodcastState) -> PodcastState:
    return {
        "topic_index": state["topic_index"] + 1,
        "exchange_index": 0,
    }


def has_more_topics(state: PodcastState) -> Literal["prepare_topic", "end"]:
    if state["topic_index"] < len(state["topics"]):
        return "prepare_topic"
    return "end"
