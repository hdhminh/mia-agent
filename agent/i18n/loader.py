from __future__ import annotations

import json
import os
from typing import Any

_locales_cache: dict[str, dict[str, Any]] = {}


def get_locale() -> str:
    return os.getenv("MIA_LOCALE", "en").strip().lower()


def load_locale_data(locale: str) -> dict[str, Any]:
    if locale in _locales_cache:
        return _locales_cache[locale]

    dir_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(dir_path, "locales", f"{locale}.json")

    # Fallback to English if file doesn't exist
    if not os.path.exists(file_path):
        if locale != "en":
            return load_locale_data("en")
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _locales_cache[locale] = data
            return data
    except Exception:
        if locale != "en":
            return load_locale_data("en")
        return {}


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    locale = get_locale()
    data = load_locale_data(locale)

    # Traverse nested keys e.g., "error.unexpected"
    parts = key.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            current = None
            break

    # Fallback to English if not found in current locale
    if current is None and locale != "en":
        en_data = load_locale_data("en")
        current = en_data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                current = None
                break

    if current is None:
        if default is not None:
            current = default
        else:
            return key

    if isinstance(current, str):
        try:
            # Substitute owner_name or any kwargs
            owner_name = os.getenv("OWNER_DISPLAY_NAME", "User").strip()
            # If "owner_name" is in string template but not in kwargs, add it
            if "{owner_name}" in current and "owner_name" not in kwargs:
                kwargs["owner_name"] = owner_name
            return current.format(**kwargs)
        except Exception:
            return current

    # If it's a list or dict, just return it as is (useful for followup cues lists)
    return current
