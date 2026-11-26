"""Dashboard cards shipped with the Home Sapiens Assistant integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARDS_URL_BASE = "/domo_cards"
CARDS_PATTERN = "domo-*-card.js"
CARDS_PATH = Path(__file__).parent / "www"


def _find_bundles() -> list[str]:
    """Return the card bundles (one file per card family) found in www."""
    return sorted(path.name for path in CARDS_PATH.glob(CARDS_PATTERN))


async def async_register_cards(hass: HomeAssistant) -> None:
    """Serve the bundled dashboard cards and load them in the frontend."""
    bundles = await hass.async_add_executor_job(_find_bundles)
    if not bundles:
        _LOGGER.warning("No dashboard cards bundle found in %s", CARDS_PATH)
        return

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARDS_URL_BASE, str(CARDS_PATH), cache_headers=True)]
        )
    except RuntimeError:
        _LOGGER.debug("Static path %s is already registered", CARDS_URL_BASE)

    integration = await async_get_integration(hass, DOMAIN)
    for bundle in bundles:
        url = f"{CARDS_URL_BASE}/{bundle}?v={integration.version}"
        add_extra_js_url(hass, url)
        _LOGGER.debug("Dashboard cards registered: %s", url)
