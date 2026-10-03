"""
domo/button.py

Entities fed by:
- platforms/scenarios.py
- platforms/thermoregulation.py
- platforms/sicu.py
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
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.scenarios import DomoScenarioDevice, get_scenario_device
from .platforms.sicu import get_security_device, InputBypassDenied
from .platforms.thermoregulation import get_all_thermostats
from .services.i18n import async_get_translated_strings
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

    # --- Security (bypass open inputs) ---
    security = get_security_device()
    if security:
        burglar_alarm_device = dr.async_get(hass).async_get_device_by_identifier(
            (DOMAIN, "burglar_alarm"), entry.entry_id
        )
        security_inputs_device_info = DeviceInfo(
            identifiers={(DOMAIN, "burglar_alarm_inputs")},
            name="Security Inputs",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
            via_device_id=burglar_alarm_device.id if burglar_alarm_device else None,
        )
        async_add_entities([
            SecurityBypassOpenInputsButton(entry.entry_id, security_inputs_device_info)
        ])
        _LOGGER.info("Added button entity for SICU bypass open inputs")
    else:
        _LOGGER.debug("SECURITY central not yet available, skipping bypass open inputs button")
        
        
# ============================================================
# ===== THERMOSTATS =====
# ============================================================

class DomoThermoBackupButton(ButtonEntity):
    """Saves a backup of t1/t2/t3 and thermal profiles for all thermostats."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:content-save-outline"

    def __init__(self, hass, entry_id: str):
        self.hass = hass
        self._attr_unique_id = f"{entry_id}_thermo_backup"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate")},
        )
        self._i18n: dict = {}

    async def async_added_to_hass(self) -> None:
        self._i18n = await async_get_translated_strings(self.hass, "thermoregulation_entities")

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.thermo_backup_button", "Backup thermal profiles")

    async def async_press(self) -> None:
        try:
            filename = await async_backup_thermal_profiles(self.hass)
        except Exception as err:
            i18n = self._i18n or await async_get_translated_strings(self.hass, "thermoregulation_entities")
            raise HomeAssistantError(
                i18n.get("action_feedback.backup_error", "Backup failed: {err}").format(err=err)
            ) from err
        _LOGGER.info("THERMO BACKUP: created %s", filename)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE_ENTITY, self._attr_unique_id)


class DomoThermoRestoreButton(ButtonEntity):
    """Restores t1/t2/t3 and thermal profiles from the file selected in the related select."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:file-restore-outline"

    def __init__(self, hass, entry_id: str):
        self.hass = hass
        self._attr_unique_id = f"{entry_id}_thermo_restore"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate")},
        )
        self._i18n: dict = {}

    async def async_added_to_hass(self) -> None:
        self._i18n = await async_get_translated_strings(self.hass, "thermoregulation_entities")

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.thermo_restore_button", "Restore thermal profiles")

    async def async_press(self) -> None:
        i18n = self._i18n or await async_get_translated_strings(self.hass, "thermoregulation_entities")
        filename = get_selected_restore_file()
        if not filename:
            raise HomeAssistantError(
                i18n.get("action_feedback.no_restore_file_selected", "No backup file selected")
            )
        try:
            await async_restore_thermal_profiles(self.hass, filename)
        except Exception as err:
            raise HomeAssistantError(
                i18n.get("action_feedback.restore_error", "Restore failed ({filename}): {err}").format(
                    filename=filename, err=err
                )
            ) from err
        _LOGGER.info("THERMO RESTORE: completed from %s", filename)


# ============================================================
# ===== SCENARIOS =====
# ============================================================

class DomoScenarioStartRegistrationButton(ButtonEntity):
    """Starts registration of a new scenario."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:record-rec"

    def __init__(self, device: DomoScenarioDevice, entry_id: str):
        self._device = device
        self._attr_unique_id = "domo_scenario_start_registration_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenarios",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )
        self._i18n: dict = {}

    async def async_added_to_hass(self) -> None:
        self._i18n = await async_get_translated_strings(self.hass, "scenarios_entities")

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.start_registration_button", "Start scenario registration")

    async def async_press(self) -> None:
        try:
            await self._device.start_registration()
        except Exception as err:
            i18n = self._i18n or await async_get_translated_strings(self.hass, "scenarios_entities")
            raise HomeAssistantError(
                i18n.get(
                    "action_feedback.start_registration_error",
                    "Error starting scenario registration: {err}",
                ).format(err=err)
            ) from err


class DomoScenarioStopRegistrationButton(ButtonEntity):
    """Concludes the scenario registration in progress."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:content-save"

    def __init__(self, device: DomoScenarioDevice, entry_id: str):
        self._device = device
        self._attr_unique_id = "domo_scenario_stop_registration_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenarios",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )
        self._i18n: dict = {}

    async def async_added_to_hass(self) -> None:
        self._i18n = await async_get_translated_strings(self.hass, "scenarios_entities")

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.stop_registration_button", "Finish scenario registration")

    async def async_press(self) -> None:
        try:
            await self._device.stop_registration()
        except Exception as err:
            i18n = self._i18n or await async_get_translated_strings(self.hass, "scenarios_entities")
            raise HomeAssistantError(
                i18n.get(
                    "action_feedback.stop_registration_error",
                    "Error stopping scenario registration: {err}",
                ).format(err=err)
            ) from err


class DomoScenarioDeleteButton(ButtonEntity):
    """Deletes the specified scenario."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:delete"

    def __init__(self, device: DomoScenarioDevice, entry_id: str):
        self._device = device
        self._attr_unique_id = "domo_scenario_delete_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenarios",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )
        self._i18n: dict = {}

    async def async_added_to_hass(self) -> None:
        self._i18n = await async_get_translated_strings(self.hass, "scenarios_entities")

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.delete_button", "Delete scenario")

    async def async_press(self) -> None:
        try:
            await self._device.delete_scenario_by_name(self._device.name_draft)
        except Exception as err:
            i18n = self._i18n or await async_get_translated_strings(self.hass, "scenarios_entities")
            raise HomeAssistantError(
                i18n.get("action_feedback.delete_error", "Error deleting scenario: {err}").format(err=err)
            ) from err


class DomoScenarioRenameButton(ButtonEntity):
    """Starts the rename flow for a scenario."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:rename-outline"

    def __init__(self, device: DomoScenarioDevice, entry_id: str):
        self._device = device
        self._attr_unique_id = "domo_scenario_rename_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenarios",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )
        self._i18n: dict = {}

    async def async_added_to_hass(self) -> None:
        self._i18n = await async_get_translated_strings(self.hass, "scenarios_entities")

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.rename_button", "Rename scenario")

    async def async_press(self) -> None:
        try:
            await self._device.start_rename()
        except Exception as err:
            i18n = self._i18n or await async_get_translated_strings(self.hass, "scenarios_entities")
            raise HomeAssistantError(
                i18n.get("action_feedback.rename_error", "Error starting scenario rename: {err}").format(err=err)
            ) from err
            
            
# ============================================================
# ===== SECURITY (bypass open inputs) =====
# ============================================================

class SecurityBypassOpenInputsButton(ButtonEntity):
    """Button that excludes (bypasses) every currently open alarm input in one action."""

    _attr_should_poll = False

    _FEEDBACK_KEYS = {
        "no_code": ("input_bypass.denied_no_code", "Action denied, enter code"),
        "wrong_code": ("input_bypass.wrong_code", "Wrong code"),
    }

    def __init__(self, entry_id: str, device_info: DeviceInfo):
        self._attr_unique_id = f"{entry_id}_sicu_bypass_open_inputs"
        self._attr_device_info = device_info
        self._i18n: dict = {}

    @property
    def name(self) -> str:
        return self._i18n.get("input_bypass.button_name", "Bypass open inputs")

    @property
    def icon(self) -> str:
        device = get_security_device()
        if device and device.input_bypass_window_active:
            return "mdi:shield-alert-outline"
        return "mdi:cancel"

    async def async_press(self) -> None:
        device = get_security_device()
        if not device:
            raise HomeAssistantError("Security central unit not available")

        try:
            await device.bypass_open_inputs()
        except InputBypassDenied as err:
            strings = await async_get_translated_strings(self.hass, "sicu_entities")
            key, fallback = self._FEEDBACK_KEYS.get(err.feedback, (None, str(err)))
            message = strings.get(key, fallback) if key else fallback
            raise HomeAssistantError(message) from err
        except Exception as err:
            raise HomeAssistantError(f"Error sending sicu_multi_input_set_req: {err}") from err

    async def async_added_to_hass(self) -> None:
        self._i18n = await async_get_translated_strings(self.hass, "sicu_entities")
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()
