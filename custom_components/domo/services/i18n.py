"""
domo/services/i18n.py

Runtime translation helper for notification strings, sourced from
translations/<lang>.json custom categories (e.g. "sicu_notifications").

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues

status: passed
"""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== TRANSLATION LOOKUP =====
# ============================================================

async def async_get_translated_strings(hass: HomeAssistant, category: str) -> dict[str, str]:
    """Return a flat {sub_key: translated_string} dict for a notification category."""
    strings = await _async_load_category(hass, hass.config.language, category)

    if not strings and hass.config.language != "en":
        _LOGGER.debug(
            "No '%s' strings for language '%s', falling back to English",
            category, hass.config.language,
        )
        strings = await _async_load_category(hass, "en", category)

    return strings


async def _async_load_category(hass: HomeAssistant, language: str, category: str) -> dict[str, str]:
    """Load and flatten a single translation category for a given language."""
    translations = await async_get_translations(
        hass, language, category, integrations=[DOMAIN]
    )
    prefix = f"component.{DOMAIN}.{category}."
    return {
        key[len(prefix):]: value
        for key, value in translations.items()
        if key.startswith(prefix)
    }
