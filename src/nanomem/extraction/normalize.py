from __future__ import annotations

import re

from nanomem.contracts import DialogueMessage


OBJECTIVE_PREFIX_PATTERN = re.compile(
    r"^The (user|agent) "
    r"(said|asked|decided|corrected|reported|confirmed|told|mentioned)\b",
    re.IGNORECASE,
)

USER_FACT_PATTERN = re.compile(
    r"^The user "
    r"(prefers|likes|dislikes|wants|needs|usually|always|never|has|uses)\b",
    re.IGNORECASE,
)


def normalize_memory_text(text: str, message: DialogueMessage) -> str:
    cleaned = _strip_terminal_punctuation(text.strip())
    if not cleaned:
        return ""
    if OBJECTIVE_PREFIX_PATTERN.search(cleaned):
        return _sentence(cleaned)
    if cleaned.lower().startswith("the agent "):
        return _sentence(cleaned)
    if USER_FACT_PATTERN.search(cleaned):
        return _sentence(f"The user said {_the_user_clause(cleaned)}")
    if cleaned.lower().startswith("the user "):
        return _sentence(cleaned)
    if message.role == "assistant":
        return _normalize_agent_text(cleaned)
    return _normalize_user_text(cleaned)


def _normalize_user_text(text: str) -> str:
    cleaned = re.sub(r"^correction:\s*", "", text, flags=re.IGNORECASE).strip()
    lower = cleaned.lower()
    remember_prefix = "please remember that "
    if lower.startswith(remember_prefix):
        clause = cleaned[len(remember_prefix):]
        return _sentence(
            "The user asked the agent to remember that "
            f"{_first_person_to_third_person(clause)}"
        )
    if lower.startswith("remember that "):
        clause = cleaned[len("remember that "):]
        return _sentence(
            "The user asked the agent to remember that "
            f"{_first_person_to_third_person(clause)}"
        )
    if lower.startswith("please "):
        action = cleaned[len("please "):]
        return _sentence(f"The user asked the agent to {_lower_first(action)}")
    for prefix in ("do not ", "don't ", "never "):
        if lower.startswith(prefix):
            action = cleaned[len(prefix):]
            return _sentence(f"The user asked the agent not to {_lower_first(action)}")
    if _has_first_person(cleaned):
        return _sentence(f"The user said {_first_person_to_third_person(cleaned)}")
    return _sentence(f"The user said: {cleaned}")


def _normalize_agent_text(text: str) -> str:
    clause = _second_person_to_user(text)
    clause = re.sub(r"^I will\b", "it will", clause, flags=re.IGNORECASE)
    clause = re.sub(r"^I'll\b", "it will", clause, flags=re.IGNORECASE)
    clause = re.sub(r"^I can\b", "it can", clause, flags=re.IGNORECASE)
    clause = re.sub(r"^I\b", "it", clause, flags=re.IGNORECASE)
    return _sentence(f"The agent said {_lower_first(clause)}")


def _the_user_clause(text: str) -> str:
    replacements = {
        "The user prefers ": "they prefer ",
        "The user likes ": "they like ",
        "The user dislikes ": "they dislike ",
        "The user wants ": "they want ",
        "The user needs ": "they need ",
        "The user usually wants ": "they usually want ",
        "The user always wants ": "they always want ",
        "The user never wants ": "they never want ",
        "The user usually ": "they usually ",
        "The user always ": "they always ",
        "The user never ": "they never ",
        "The user has ": "they have ",
        "The user uses ": "they use ",
    }
    for prefix, replacement in replacements.items():
        if text.lower().startswith(prefix.lower()):
            return replacement + text[len(prefix):]
    return _lower_first(text)


def _first_person_to_third_person(text: str) -> str:
    clause = text.strip()
    replacements = (
        (r"\bI am\b", "they are"),
        (r"\bI'm\b", "they are"),
        (r"\bI have\b", "they have"),
        (r"\bI've\b", "they have"),
        (r"\bI want\b", "they want"),
        (r"\bI need\b", "they need"),
        (r"\bI prefer\b", "they prefer"),
        (r"\bI like\b", "they like"),
        (r"\bI dislike\b", "they dislike"),
        (r"\bI usually\b", "they usually"),
        (r"\bI always\b", "they always"),
        (r"\bI never\b", "they never"),
        (r"\bI do not\b", "they do not"),
        (r"\bI don't\b", "they do not"),
        (r"\bI\b", "they"),
        (r"\bmy\b", "their"),
        (r"\bme\b", "them"),
        (r"\bmine\b", "theirs"),
    )
    for pattern, replacement in replacements:
        clause = re.sub(pattern, replacement, clause, flags=re.IGNORECASE)
    return _lower_first(clause)


def _second_person_to_user(text: str) -> str:
    clause = text.strip()
    replacements = (
        (r"\byou prefer\b", "the user prefers"),
        (r"\byou like\b", "the user likes"),
        (r"\byou dislike\b", "the user dislikes"),
        (r"\byou want\b", "the user wants"),
        (r"\byou need\b", "the user needs"),
        (r"\byou usually\b", "the user usually"),
        (r"\byou always\b", "the user always"),
        (r"\byou never\b", "the user never"),
        (r"\byou\b", "the user"),
        (r"\byour\b", "the user's"),
    )
    for pattern, replacement in replacements:
        clause = re.sub(pattern, replacement, clause, flags=re.IGNORECASE)
    return clause


def _has_first_person(text: str) -> bool:
    return bool(re.search(r"\b(I|I'm|I've|my|me|mine)\b", text, flags=re.IGNORECASE))


def _sentence(text: str) -> str:
    return f"{_strip_terminal_punctuation(text.strip())}."


def _strip_terminal_punctuation(text: str) -> str:
    return text.rstrip(" \t\r\n.!?。！？")


def _lower_first(text: str) -> str:
    if not text:
        return text
    return text[0].lower() + text[1:]
