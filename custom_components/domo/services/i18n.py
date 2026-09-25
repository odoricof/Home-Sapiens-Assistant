"""
domo/services/i18n.py

Entities fed by this file:
- domo/text.py : entity_names and action_feedback strings for scheduler, thermoregulation, loadsctrl, irrigation and scenarios entities
- domo/select.py : entity_names, weekday_options, season_options and algo_mode_options labels
- domo/switch.py : entity_names and action_feedback strings for irrigation switches
- domo/number.py : entity_names and action_feedback strings for numeric entities
- domo/time.py : entity_names and action_feedback strings for time entities
- domo/button.py : entity_names, status and action_feedback strings for scenario and backup/restore buttons
- domo/alarm_control_panel.py : sicu_notifications and sicu_entities strings
- domo/binary_sensor.py : sicu_entities area_status and input_status labels
- domo/sensor.py : sicu_entities and common_entities strings

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues

status: passed
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_I18N_DIR = Path(__file__).resolve().parent.parent / "i18n"
_DEFAULT_LANGUAGE = "en"
_language_cache: dict[str, dict] = {}


# ============================================================
# ===== TRANSLATION LOOKUP =====
# ============================================================

async def async_get_translated_strings(hass: HomeAssistant, category: str) -> dict[str, str]:
    """Return a flat {sub_key: translated_string} dict for a translation category."""
    strings = await _async_load_category(hass, hass.config.language, category)

    if not strings and hass.config.language != _DEFAULT_LANGUAGE:
        _LOGGER.debug(
            "No '%s' strings for language '%s', falling back to English",
            category, hass.config.language,
        )
        strings = await _async_load_category(hass, _DEFAULT_LANGUAGE, category)

    return strings


async def _async_load_category(hass: HomeAssistant, language: str, category: str) -> dict[str, str]:
    """Load and flatten a single translation category for a given language."""
    data = await _async_load_language_file(hass, language)
    category_data = data.get(category)
    if not category_data:
        return {}
    return _flatten(category_data)


async def _async_load_language_file(hass: HomeAssistant, language: str) -> dict:
    """Load and cache the custom i18n JSON file for a given language."""
    if language in _language_cache:
        return _language_cache[language]

    path = _I18N_DIR / f"{language}.json"

    try:
        data = await hass.async_add_executor_job(_read_json, path)
    except FileNotFoundError:
        _LOGGER.debug("No custom i18n file found for language '%s'", language)
        data = {}
    except (OSError, ValueError) as err:
        _LOGGER.warning("Failed to load i18n file '%s': %s", path, err)
        data = {}

    _language_cache[language] = data
    return data


def _read_json(path: Path) -> dict:
    """Read and parse a JSON file from disk."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    """Flatten a nested dict into dotted-key -> string mappings."""
    flat: dict[str, str] = {}
    for key, value in data.items():
        full_key = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, f"{full_key}."))
        else:
            flat[full_key] = value
    return flat
