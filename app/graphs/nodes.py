from __future__ import annotations

from typing import Literal, Optional, Tuple

from langchain_core.messages import HumanMessage, AIMessage

from app.config.settings import settings
from app.graphs.types import PodcastState, Speaker
from app.graphs.xml_utils import render_topic_block, render_instruction_block, compose_prompt_with_optional_instruction
from app.graphs.llm_utils import create_llm, invoke_llm
from app.progress import increment_progress


_llm = create_llm()


def start_topic(state: PodcastState) -> PodcastState:
    from app.graphs.llm_utils import summarize_topic  # local import avoids circulars at module import
    topics = state["topics"]
    i = state.get("topic_index", 0)
    summary = summarize_topic(topics[i], _llm)
    return {"summary": summary, "exchange_index": 0}


# --- Internal helpers (no logic changes) ---------------------------------------------------------

def _select_route_for_speaker(state: PodcastState) -> Tuple[Speaker, str, list, str]:
    """Return (current_speaker, system_prompt, history, history_key)."""
    current_speaker: Speaker = state.get("current_speaker", "HOST_A")
    if current_speaker == "HOST_A":
        return current_speaker, state["host_a_system_prompt"], list(state.get("host_a_history", [])), "host_a_history"
    return current_speaker, state["host_b_system_prompt"], list(state.get("host_b_history", [])), "host_b_history"


def _apply_llm_turn(
    state: PodcastState,
    user_text: str,
    *,
    increment_exchange: bool,
) -> PodcastState:
    """
    Shared logic for a single turn:
    - Route to correct system prompt/history by current speaker
    - Invoke LLM
    - Update history and dialogue
    - Optionally increment progress and exchange index
    - Flip speaker and set last_content
    """
    current_speaker, system_prompt, history, history_key = _select_route_for_speaker(state)

    content = invoke_llm(system_prompt, history, user_text, _llm)

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
    if increment_exchange:
        result["exchange_index"] = state.get("exchange_index", 0) + 1
        # Update progress centrally
        job_id = state.get("job_id")
        if job_id:
            increment_progress(job_id, state.get("progress_increment", 0.0))
    return result


# --- Nodes ---------------------------------------------------------------------------------------

def first_response(state: PodcastState) -> PodcastState:
    i = state["topic_index"]
    is_first_topic = i == 0
    context = (
        f"{render_topic_block(state['summary'])}\n\n"
        f"{render_instruction_block(settings.INTRO_SEGMENT_INSTRUCTIONS[is_first_topic])}"
    )

    # Do not advance progress or exchange index on the first response
    return _apply_llm_turn(
        state,
        context,
        increment_exchange=False,
    )


def next_exchange(state: PodcastState) -> PodcastState:
    i = state["topic_index"]
    j = state.get("exchange_index", 0)
    num_exchanges = state["exchanges_per_topic"][i]

    # Build content for this turn
    content_seed = state.get("last_content", "")
    instruction: Optional[str] = None

    # First exchange on very first topic: explicit self-intro
    if i == 0 and j == 0:
        instruction = "Introduce yourself to the listeners"

    # Last exchange of this topic: add closing instruction
    if j >= (num_exchanges - 2):
        if i == (len(state["topics"]) - 1):
            instruction = (
                "The podcast is ending now, say your goodbyes and thank the audience for tuning in."
            )
        else:
            instruction = (
                "Naturally end this conversation about the current topic. You will be given the next topic to "
                "cover in the next instruction. Do not make up the next topic; be ambiguous. Say something like "
                '"alright, it\'s time to move onto another topic" in a natural way.'
            )

    chat_content = compose_prompt_with_optional_instruction(content_seed, instruction)

    # Exchanges should count towards progress, and advance the exchange index by 1
    return _apply_llm_turn(
        state,
        chat_content,
        increment_exchange=True,
    )


def should_continue_exchange(state: PodcastState) -> Literal["next_exchange", "finish_topic"]:
    i = state["topic_index"]
    j = state.get("exchange_index", 0)
    num_exchanges = state["exchanges_per_topic"][i]
    return "next_exchange" if j < num_exchanges else "finish_topic"


def finish_topic(state: PodcastState) -> PodcastState:
    return {
        "topic_index": state["topic_index"] + 1,
        "exchange_index": 0,
    }


def has_more_topics(state: PodcastState) -> Literal["start_topic", "end"]:
    if state["topic_index"] < len(state["topics"]):
        return "start_topic"
    return "end"


