from __future__ import annotations

from typing import Optional


def render_xml_block(tag: str, content: str) -> str:
    return f"<{tag}>\n{content}\n</{tag}>"


def render_topic_block(summary: str) -> str:
    return render_xml_block("topic", summary)


def render_instruction_block(instruction: str) -> str:
    return render_xml_block("instruction", instruction)


def compose_prompt_with_topic_instruction(
    base_text: str,
    topic: Optional[str] = None,
    instruction: Optional[str] = None,
    exchange_countdown: Optional[int] = None,
) -> str:
    result = base_text.strip()
    if exchange_countdown is not None:
        result = f"{render_instruction_block(f'This Topic Countdown: {exchange_countdown}')}\n\n{result}"
    if instruction:
        result = f"{render_instruction_block(instruction)}\n\n{result}".strip()
    if topic:
        result = f"{render_topic_block(topic)}\n\n{result}".strip()
    
    return result


