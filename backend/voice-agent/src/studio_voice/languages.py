"""Everything worded for one language lives in `locales/<code>/`, never in flow or tool code.

Adding a language means adding a folder (prompt rules, messages and answer parsers), not
editing this module.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Any

LOCALES_DIR = Path(__file__).with_name("locales")
# For messages sent before an agent's own language is known.
FALLBACK_LANGUAGE = "en"
PROMPT_RULES_FILE = "prompt_rules.md"
MESSAGES_FILE = "messages.json"

# Reads a typed answer (age, day, time, yes or no) from what the caller said, or returns None.
# Values are JSON-friendly: int, "YYYY-MM-DD", "HH:MM", bool, digit strings.
FieldParser = Callable[[str, date], Any]


class UnsupportedLanguageError(LookupError):
    pass


@dataclass(frozen=True)
class Locale:
    code: str
    prompt_rules: str
    messages: dict[str, str]


@lru_cache
def load_locale(code: str) -> Locale:
    folder = LOCALES_DIR / code
    if not folder.is_dir():
        raise UnsupportedLanguageError(code)
    return Locale(
        code=code,
        prompt_rules=(folder / PROMPT_RULES_FILE).read_text(encoding="utf-8").strip(),
        messages=json.loads((folder / MESSAGES_FILE).read_text(encoding="utf-8")),
    )


def build_instructions(agent_instructions: str, locale: Locale, has_knowledge: bool) -> str:
    rules = [locale.prompt_rules]
    if has_knowledge:
        rules.append(locale.messages["knowledge_rule"])
    return "\n\n".join([agent_instructions.strip(), *rules])


def parsers_for(language: str) -> dict[str, FieldParser]:
    try:
        module = import_module(f"studio_voice.locales.{language}.parser")
    except ModuleNotFoundError as error:
        raise UnsupportedLanguageError(language) from error
    return module.FIELD_PARSERS
