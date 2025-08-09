import json
import os
import time
from typing import List

from app.config.settings import settings
from app.logger import setup_logger
from app.graphs.podcast_graph import compile_podcast_graph


logger = setup_logger('llm_client')


class LLMClient:
    """
    LangGraph-powered client for generating podcast dialogue scripts.

    Public interface preserved:
    - generate_podcast_script(topics_text: List[str], job_id: str) -> List[Dict[str, str]]
    """

    def generate_podcast_script(self, topics_text: List[str], job_id: str):
        compiled_graph, initial_state = compile_podcast_graph(topics_text, job_id)

        # Execute the graph to completion with configurable recursion limit
        final_state = compiled_graph.invoke(
            initial_state,
            config={"recursion_limit": settings.LLM_GRAPH_RECURSION_LIMIT},
        )
        dialogue = final_state.get("dialogue", [])

        if settings.DEBUG:
            os.makedirs(settings.DEBUG_DIR, exist_ok=True)
            timestamp = int(time.time())
            file_path = os.path.join(settings.DEBUG_DIR, f"llm-podcast-{timestamp}.json")
            with open(file_path, "w") as f:
                json.dump(dialogue, f, indent=4)

        return dialogue
