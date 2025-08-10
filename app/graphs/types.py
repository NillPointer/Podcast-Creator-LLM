from __future__ import annotations

from typing import Dict, List, Literal, TypedDict
from langchain_core.messages import BaseMessage


Speaker = Literal["HOST_A", "HOST_B"]


class PodcastState(TypedDict, total=False):
    topics: List[str]
    topic_index: int
    exchanges_per_topic: List[int]
    exchange_index: int
    current_speaker: Speaker

    # Chat histories for each host (as LC messages)
    host_a_history: List[BaseMessage]
    host_b_history: List[BaseMessage]

    # Per-topic context
    topic_summary: str

    # Output dialogue
    dialogue: List[Dict[str, str]]

    # System prompts
    host_a_system_prompt: str
    host_b_system_prompt: str

    # Rolling content used to seed next turn
    last_content: str

    # Progress tracking
    job_id: str
    progress_increment: float


