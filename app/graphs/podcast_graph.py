from __future__ import annotations

import random
from typing import List

from langgraph.graph import StateGraph, END

from app.config.settings import settings
from app.graphs.types import PodcastState
from app.graphs.llm_utils import build_host_system_prompt
from app.graphs.nodes import (
    start_topic,
    first_response,
    next_exchange,
    finish_topic,
    should_continue_exchange,
    has_more_topics,
)


def build_podcast_graph() -> StateGraph:
    """
    Construct the LangGraph state graph using predefined node functions and conditions.
    """
    graph = StateGraph(PodcastState)

    # Register nodes
    graph.add_node("start_topic", start_topic)
    graph.add_node("first_response", first_response)
    graph.add_node("next_exchange", next_exchange)
    graph.add_node("finish_topic", finish_topic)

    # Edges
    graph.set_entry_point("start_topic")
    graph.add_edge("start_topic", "first_response")
    graph.add_conditional_edges(
        "first_response",
        should_continue_exchange,
        {
            "next_exchange": "next_exchange",
            "finish_topic": "finish_topic",
        },
    )
    graph.add_conditional_edges(
        "next_exchange",
        should_continue_exchange,
        {
            "next_exchange": "next_exchange",
            "finish_topic": "finish_topic",
        },
    )
    graph.add_conditional_edges(
        "finish_topic",
        has_more_topics,
        {
            "start_topic": "start_topic",
            "end": END,
        },
    )

    return graph


def compile_podcast_graph(topics: List[str], job_id: str) -> tuple:
    """
    Prepare the compiled graph and its initial state for execution.
    Returns (compiled_graph, initial_state)
    """
    # Determine number of exchanges per topic and total
    exchanges_per_topic: List[int] = []
    total_exchanges = 0
    for _ in range(len(topics)):
        n = random.randint(settings.TOPIC_EXCHANGE_MIN, settings.TOPIC_EXCHANGE_MAX)
        exchanges_per_topic.append(n)
        total_exchanges += n

    progress_increment = 40.0 / total_exchanges if total_exchanges > 0 else 0.0

    host_a_system_prompt = build_host_system_prompt(
        settings.HOST_A_NAME, settings.HOST_B_NAME, settings.HOST_A_PERSONALITY
    )
    host_b_system_prompt = build_host_system_prompt(
        settings.HOST_B_NAME, settings.HOST_A_NAME, settings.HOST_B_PERSONALITY
    )

    initial_state: PodcastState = {
        "topics": topics,
        "topic_index": 0,
        "exchanges_per_topic": exchanges_per_topic,
        "exchange_index": 0,
        "current_speaker": "HOST_A",
        "host_a_history": [],
        "host_b_history": [],
        "summary": "",
        "dialogue": [],
        "host_a_system_prompt": host_a_system_prompt,
        "host_b_system_prompt": host_b_system_prompt,
        "last_content": "",
        "job_id": job_id,
        "progress_increment": progress_increment,
    }

    compiled = build_podcast_graph().compile()
    return compiled, initial_state


