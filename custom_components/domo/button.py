"""
domo/button.py

Entities fed by:
- platforms/scenarios.py
- platforms/thermoregulation.py
- services/thermo_backup.py

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

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.scenarios import DomoScenarioDevice, get_scenario_device
from .platforms.thermoregulation import get_all_thermostats
from .services.thermo_backup import (
    async_backup_thermal_profiles,
    async_restore_thermal_profiles,
    get_selected_restore_file,
)

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup button platform."""
    # --- Thermostats ---
    thermostats = get_all_thermostats()
    if thermostats:
        async_add_entities([
            DomoThermoBackupButton(hass, entry.entry_id),
            DomoThermoRestoreButton(hass, entry.entry_id),
        ])
    else:
        _LOGGER.debug("No thermostats found, skipping thermal backup buttons")

    # --- Scenarios ---
    scenario_device = get_scenario_device()
    if scenario_device:
        async_add_entities([
            DomoScenarioStartRegistrationButton(scenario_device, entry.entry_id),
            DomoScenarioStopRegistrationButton(scenario_device, entry.entry_id),
            DomoScenarioDeleteButton(scenario_device, entry.entry_id),
            DomoScenarioRenameButton(scenario_device, entry.entry_id),
        ])
        _LOGGER.info("Added scenario buttons: start/stop/delete/rename")
    else:
        _LOGGER.debug("Scenario device not available, skipping scenario buttons")


# ============================================================
# ===== THERMOSTATS =====
# ============================================================

class DomoThermoBackupButton(ButtonEntity):
    """Saves a backup of t1/t2/t3 and thermal profiles for all thermostats."""

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
            raise HomeAssistantError(f"Backup failed: {err}") from err
        _LOGGER.info("THERMO BACKUP: created %s", filename)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE_ENTITY, self._attr_unique_id)


class DomoThermoRestoreButton(ButtonEntity):
    """Restores t1/t2/t3 and thermal profiles from the file selected in the related select."""

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
            raise HomeAssistantError("No backup file selected")
        try:
            await async_restore_thermal_profiles(self.hass, filename)
        except Exception as err:
            raise HomeAssistantError(f"Restore failed ({filename}): {err}") from err
        _LOGGER.info("THERMO RESTORE: completed from %s", filename)


# ============================================================
# ===== SCENARIOS =====
# ============================================================

class DomoScenarioStartRegistrationButton(ButtonEntity):
    """Starts registration of a new scenario."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:record-rec"
    _attr_name = "Avvia registrazione scenario"

    def __init__(self, device: DomoScenarioDevice, entry_id: str):
        self._device = device
        self._attr_unique_id = "domo_scenario_start_registration_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenari",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

    async def async_press(self) -> None:
        try:
            await self._device.start_registration()
        except Exception as err:
            raise HomeAssistantError(f"Error starting scenario registration: {err}") from err


class DomoScenarioStopRegistrationButton(ButtonEntity):
    """Concludes the scenario registration in progress."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:content-save"
    _attr_name = "Concludi registrazione scenario"

    def __init__(self, device: DomoScenarioDevice, entry_id: str):
        self._device = device
        self._attr_unique_id = "domo_scenario_stop_registration_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenari",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

    async def async_press(self) -> None:
        try:
            await self._device.stop_registration()
        except Exception as err:
            raise HomeAssistantError(f"Error stopping scenario registration: {err}") from err


class DomoScenarioDeleteButton(ButtonEntity):
    """Deletes the specified scenario."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:delete"
    _attr_name = "Cancella scenario"

    def __init__(self, device: DomoScenarioDevice, entry_id: str):
        self._device = device
        self._attr_unique_id = "domo_scenario_delete_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenari",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

    async def async_press(self) -> None:
        try:
            await self._device.delete_scenario_by_name(self._device.name_draft)
        except Exception as err:
            raise HomeAssistantError(f"Error deleting scenario: {err}") from err


class DomoScenarioRenameButton(ButtonEntity):
    """Starts the rename flow for a scenario."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:rename-outline"
    _attr_name = "Rinomina scenario"

    def __init__(self, device: DomoScenarioDevice, entry_id: str):
        self._device = device
        self._attr_unique_id = "domo_scenario_rename_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenari",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

    async def async_press(self) -> None:
        try:
            await self._device.start_rename()
        except Exception as err:
            raise HomeAssistantError(f"Error starting scenario rename: {err}") from err
