from __future__ import annotations

from collections.abc import Iterable


def find_prohibited_words(message: str, prohibited_words: Iterable[str]) -> list[str]:
    lowered_message = message.lower()
    return [word for word in prohibited_words if word.lower() in lowered_message]


def check_campaign_message(message: str, prohibited_words: Iterable[str]) -> list[str]:
    return [
        f"campaign_message contains prohibited word: {word}"
        for word in find_prohibited_words(message, prohibited_words)
    ]
