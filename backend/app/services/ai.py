import json
import re

from langchain_anthropic import ChatAnthropic

from app.config import get_settings


def get_chat_model() -> ChatAnthropic:
    settings = get_settings()
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        anthropic_api_key=settings.anthropic_api_key,
    )


def parse_json_response(text: str) -> dict:
    """Parse JSON from AI response, stripping markdown code fences if present."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)
