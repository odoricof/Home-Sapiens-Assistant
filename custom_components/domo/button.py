"""
domo/button.py

Entities fed by:
- services/thermo_backup.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT
"""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.thermoregulation import get_all_thermostats
from .services.thermo_backup import (
    async_backup_thermal_profiles,
    async_restore_thermal_profiles,
    get_selected_restore_file,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup button platform."""
    thermostats = get_all_thermostats()
    if not thermostats:
        _LOGGER.debug("No thermostats found yet, skipping thermo backup buttons")
        return

    async_add_entities([
        DomoThermoBackupButton(hass, entry.entry_id),
        DomoThermoRestoreButton(hass, entry.entry_id),
    ])


class DomoThermoBackupButton(ButtonEntity):
    """Salva un backup di t1/t2/t3 e profili termici di tutti i termostati."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:content-save-outline"
    _attr_name = "Backup profili termici"

    def __init__(self, hass, entry_id: str):
        self.hass = hass
        self._attr_unique_id = f"{entry_id}_thermo_backup"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate")},
        )

    async def async_press(self) -> None:
        try:
            filename = await async_backup_thermal_profiles(self.hass)
        except Exception as err:
            raise HomeAssistantError(f"Backup fallito: {err}") from err
        _LOGGER.info("THERMO BACKUP: creato %s", filename)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE_ENTITY, self._attr_unique_id)


class DomoThermoRestoreButton(ButtonEntity):
    """Ripristina t1/t2/t3 e profili termici dal file selezionato nell'apposito select."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:file-restore-outline"
    _attr_name = "Ripristina profili termici"

    def __init__(self, hass, entry_id: str):
        self.hass = hass
        self._attr_unique_id = f"{entry_id}_thermo_restore"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate")},
        )

    async def async_press(self) -> None:
        filename = get_selected_restore_file()
        if not filename:
            raise HomeAssistantError("Nessun file di backup selezionato")
        try:
            await async_restore_thermal_profiles(self.hass, filename)
        except Exception as err:
            raise HomeAssistantError(f"Ripristino fallito ({filename}): {err}") from err
        _LOGGER.info("THERMO RESTORE: completato da %s", filename)
