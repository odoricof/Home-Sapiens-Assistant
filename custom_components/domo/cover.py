"""
domo/cover.py

Entities fed by:
- platforms/openings.py

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

from homeassistant.components.cover import (
    CoverEntity,
    CoverDeviceClass,
    CoverEntityFeature,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.openings import DomoOpening, get_all_openings

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the cover platform for motorized openings."""

    openings = get_all_openings()
    if not openings:
        _LOGGER.debug("No openings found at this time")
        return

    openings_device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_openings")},
        name="Openings",
        manufacturer="Home Sapiens Assistant",
        model="Eti/Domo",
    )

    entities = [DomoCoverEntity(opening, openings_device_info, entry.entry_id)
                for opening in openings]
    async_add_entities(entities)

    _LOGGER.info("Added %d cover entities for motorized openings", len(entities))


# ============================================================
# ===== COVER =====
# ============================================================

class DomoCoverEntity(CoverEntity):
    """Cover entity for Domo motorized openings."""

    def __init__(self, opening: DomoOpening, device_info: DeviceInfo, entry_id: str):
        """Initialize the cover entity."""
        self._opening = opening
        self._attr_unique_id = opening.unique_id
        self._attr_name = opening.name
        self._attr_should_poll = False
        self._attr_device_info = device_info

        if opening.opening_type == 0:
            self._attr_device_class = CoverDeviceClass.SHUTTER
        else:
            self._attr_device_class = CoverDeviceClass.BLIND
        self._attr_assumed_state = True

        self._attr_supported_features = (
            CoverEntityFeature.OPEN |
            CoverEntityFeature.CLOSE |
            CoverEntityFeature.STOP
        )

        self._last_movement = None

    @property
    def is_opening(self) -> bool:
        """Return True if the cover is opening."""
        return self._opening.is_opening

    @property
    def is_closing(self) -> bool:
        """Return True if the cover is closing."""
        return self._opening.is_closing

    @property
    def is_closed(self) -> bool:
        """Return True if the cover is closed."""
        if self._opening.is_closed:
            if self._last_movement == 'opening':
                return False
            elif self._last_movement == 'closing':
                return True
            else:
                return True
        return False

    @property
    def current_cover_position(self) -> int | None:
        """Return the current position (0=closed, 100=open)."""
        if self._opening.is_opening:
            self._last_movement = 'opening'
            return None
        elif self._opening.is_closing:
            self._last_movement = 'closing'
            return None
        else:
            if self._last_movement == 'opening':
                return 100
            elif self._last_movement == 'closing':
                return 0
            else:
                return 0

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self._last_movement = 'opening'
        await self._opening.async_open()

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        self._last_movement = 'closing'
        await self._opening.async_close()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self._opening.async_stop()

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str | None = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()
