from __future__ import annotations

from typing import Optional


def render_xml_block(tag: str, content: str) -> str:
    return f"<{tag}>\n{content}\n</{tag}>"


def render_topic_block(summary: str) -> str:
    return render_xml_block("topic", summary)


def render_instruction_block(instruction: str) -> str:
    return render_xml_block("instruction", instruction)


def compose_prompt_with_optional_instruction(
    base_text: str,
    instruction: Optional[str] = None,
) -> str:
    if instruction:
        return f"{render_instruction_block(instruction)}\n\n{base_text}".strip()
    return base_text


