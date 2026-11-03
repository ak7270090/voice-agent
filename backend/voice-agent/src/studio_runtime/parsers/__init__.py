"""Reading typed answers (ages, days, times, yes or no) from what the caller said, per language.

Each language module exposes FIELD_PARSERS: field type -> parse(text, today) -> value or None.
Values are JSON-friendly: int, "YYYY-MM-DD", "HH:MM", bool, digit strings.
"""

from collections.abc import Callable
from datetime import date
from types import ModuleType
from typing import Any

from studio_runtime.languages import UnsupportedLanguageError
from studio_runtime.parsers import en

FieldParser = Callable[[str, date], Any]

LANGUAGE_PARSERS: dict[str, ModuleType] = {"en": en}


def parsers_for(language: str) -> dict[str, FieldParser]:
    module = LANGUAGE_PARSERS.get(language)
    if module is None:
        raise UnsupportedLanguageError(language)
    return module.FIELD_PARSERS
