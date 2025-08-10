from __future__ import annotations

import os
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from app.config.settings import settings


def build_host_system_prompt(host_name: str, cohost_name: str, personality: str) -> str:
    prompt = settings.HOST_PODCAST_PROMPT
    prompt = prompt.replace("$HOST_NAME", host_name)
    prompt = prompt.replace("$COHOST_NAME", cohost_name)
    prompt = prompt.replace("$HOST_PERSONALITY", personality)
    return prompt


def create_llm() -> ChatOpenAI:
    # Many local OpenAI-compatible servers ignore the API key, but LangChain requires one.
    api_key = os.getenv("OPENAI_API_KEY", "not-needed")
    base_url = f"{settings.LLM_API_HOST}/v1"
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        api_key=api_key,
        base_url=base_url,
        timeout=float(settings.LLM_TIMEOUT),
        max_retries=1,
        extra_body = {
            "frequency_penalty": 1.5,
            "presence_penalty": 1.5
        }
    )


def invoke_llm(system_prompt: str, history: List[BaseMessage], user_text: str, llm: ChatOpenAI) -> str:
    messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]
    if history:
        messages.extend(history)
    messages.append(HumanMessage(content=user_text))
    ai_msg = llm.invoke(messages)
    return ai_msg.content.strip() if isinstance(ai_msg, AIMessage) else str(ai_msg)


def summarize_topic(text: str, llm: ChatOpenAI) -> str:
    if not settings.LLM_SUMMARY_ENABLED:
        return text
    system_prompt = settings.LLM_SUMMARY_SYSTEM_PROMPT
    return invoke_llm(system_prompt, [], text, llm)

def next_topic_summary(text: str, llm: ChatOpenAI) -> str:
    system_prompt = """
    Summarize this into a single sentence, make as concise and short as possible
    """.strip()
    return invoke_llm(system_prompt, [], text, llm)
    
