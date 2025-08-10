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


_llm = create_llm()

# --- Internal helpers ---------------------------------------------------------

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

    content = invoke_llm(system_prompt, history, user_text, _llm)

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
    topic_summary = summarize_topic(topics[i], _llm)
    new_state: PodcastState = {"topic_summary": topic_summary, "exchange_index": 0}
    return new_state

def chat_exchange(state: PodcastState) -> PodcastState:
    i = state["topic_index"]
    is_first_topic = i == 0
    is_last_topic = i == len(state["topics"]) -1
    exchange_index = state.get("exchange_index", 0)
    num_exchanges = state["exchanges_per_topic"][i]

    # Build content for this turn
    content_seed = state.get("last_content", "")
    instruction: Optional[str] = None
    topic: Optional[str] = None

    # First chat exchange, add the topic and intro
    if exchange_index == 0:
        topic = state['topic_summary']
        instruction = settings.INTRO_SEGMENT_INSTRUCTIONS[is_first_topic]

    if i == 0 and exchange_index == 1:
        instruction = "Introduce yourself to the listeners"

    # Last exchange of this topic: add closing instruction
    if is_last_topic and exchange_index >= (num_exchanges - 2):
        instruction = "The podcast is ending now, say your goodbyes and thank the audience for tuning in."

    chat_content = compose_prompt_with_topic_instruction(content_seed, topic, instruction)

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


