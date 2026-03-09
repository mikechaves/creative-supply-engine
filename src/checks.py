from __future__ import annotations

from collections.abc import Iterable


def check_campaign_message(message: str, prohibited_words: Iterable[str]) -> list[str]:
    lowered_message = message.lower()
    warnings: list[str] = []
    for word in prohibited_words:
        if word.lower() in lowered_message:
            warnings.append(f"campaign_message contains prohibited word: {word}")
    return warnings
