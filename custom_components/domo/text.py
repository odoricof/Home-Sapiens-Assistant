"""
domo/text.py

Entities fed by:
- platforms/thermoregulation.py
- platforms/scheduler.py
- platforms/sicu.py
- platforms/loadsctrl.py
- platforms/scenarios.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues

status: passed
"""
from __future__ import annotations

import asyncio
import logging
import re

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_DISCOVERY_NEW, SIGNAL_UPDATE_ENTITY
from .platforms.loadsctrl import (
    DomoLoadCtrlMeter,
    LoadCtrlProfileError,
    get_all_loadsctrl_meters,
)
from .platforms.scenarios import DomoScenarioDevice, get_scenario_device
from .platforms.scheduler import (
    DomoTimer,
    get_all_timers,
    async_set_timer_timetable,
)
from .platforms.sicu import get_security_device, CENTRAL_STATUS_MAP
from .platforms.thermoregulation import (
    DomoThermostat,
    get_all_thermostats as get_all_thermostats_thermo,
)

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass, entry, async_add_entities):

    # --- Scheduler (timer) ---
    _LOGGER.debug("Setting up text platform (SCHEDULER)")

    added_ids: set[int] = set()

    def _add_timer(timer: DomoTimer):
        if timer.timer_id in added_ids:
            return
        added_ids.add(timer.timer_id)
        entities = [DomoTimerSlotText(timer, i, entry.entry_id) for i in range(4)]
        async_add_entities(entities)
        _LOGGER.info(
            "Added %d text entities for timer id=%s (%s)",
            len(entities), timer.timer_id, timer.name,
        )

    for timer in get_all_timers():
        _add_timer(timer)

    @callback
    def _async_new_timer(timer: DomoTimer):
        _add_timer(timer)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_DISCOVERY_NEW.format("text"), _async_new_timer)
    )

    # --- Thermostats (weekly thermal profile) ---
    thermostats = get_all_thermostats_thermo()
    if thermostats:
        profile_entities = [DomoThermostatProfileText(t, entry.entry_id) for t in thermostats]
        async_add_entities(profile_entities)
        _LOGGER.info("Added %d thermal profile text entities", len(profile_entities))

    # --- Load control (daily energy profile) ---
    loadsctrl_added_ids: set[int] = set()

    def _add_loadsctrl_profile_text(meter: DomoLoadCtrlMeter):
        if meter.meter_id in loadsctrl_added_ids:
            return
        loadsctrl_added_ids.add(meter.meter_id)
        async_add_entities([DomoLoadCtrlProfileText(meter)])
        _LOGGER.info(
            "Added loadsctrl profile text entity for meter id=%s (%s)",
            meter.meter_id, meter.name,
        )

    for meter in get_all_loadsctrl_meters():
        _add_loadsctrl_profile_text(meter)

    @callback
    def _async_new_loadsctrl_meter(meter: DomoLoadCtrlMeter):
        _add_loadsctrl_profile_text(meter)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_text"), _async_new_loadsctrl_meter
        )
    )

    hass.data[DOMAIN].setdefault("_sicu_action_texts_added", False)

    # --- Scenarios (create / rename / delete) ---
    scenario_device = get_scenario_device()
    if scenario_device:
        async_add_entities([DomoScenarioNameText(scenario_device, entry.entry_id)])
        _LOGGER.info("Added scenario name/status text entity")
    else:
        _LOGGER.debug("Scenario device not yet available, skipping scenario text entity")

    # --- Security (central actions: silence / reset_event_memory) ---
    if get_security_device() and not hass.data[DOMAIN]["_sicu_action_texts_added"]:
        async_add_entities([
            DomoSicuActionText(entry.entry_id, "silence", "CODE - Silenzia sirene", "mdi:bell-off-outline"),
            DomoSicuActionText(entry.entry_id, "reset_event_memory", "CODE - Reset memoria eventi", "mdi:refresh"),
        ])
        hass.data[DOMAIN]["_sicu_action_texts_added"] = True
        _LOGGER.info("Added 2 text entities for SICU actions (silence / reset_event_memory)")
    else:
        _LOGGER.debug("SECURITY central not yet available, skipping SICU action texts")


# ============================================================
# ===== SCHEDULER (timer) =====
# ============================================================

_SLOT_PATTERN = re.compile(r"^(|Disabilitato|([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d)$")
_SLOT_DISABLED_LABEL = "Disabilitato"


class DomoTimerSlotText(TextEntity):
    """Text entity for a time slot (bar) of a timer."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 12
    _attr_pattern = _SLOT_PATTERN.pattern

    def __init__(self, timer: DomoTimer, slot_index: int, entry_id: str):
        self._timer = timer
        self._slot_index = slot_index
        self._attr_unique_id = f"domo_timer_{timer.timer_id}_slot_{slot_index + 1}"
        self._attr_name = f"Slot {slot_index + 1}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_timer_{timer.timer_id}")},
            name=timer.name,
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

    @property
    def icon(self) -> str:
        return "mdi:clock-check" if self._timer.is_slot_active(self._slot_index) else "mdi:clock-outline"

    @property
    def extra_state_attributes(self) -> dict:
        return {"active": self._timer.is_slot_active(self._slot_index)}

    @property
    def native_value(self) -> str:
        slot = self._timer.get_slot(self._slot_index)
        if slot is None:
            return _SLOT_DISABLED_LABEL

        start = slot.get("start", {}) or {}
        stop = slot.get("stop", {}) or {}
        start_h, start_m = start.get("hour", -1), start.get("min", -1)
        stop_h, stop_m = stop.get("hour", -1), stop.get("min", -1)

        if start_h < 0 or start_m < 0:
            return _SLOT_DISABLED_LABEL

        return "{:02d}:{:02d}-{:02d}:{:02d}".format(
            start_h, start_m,
            stop_h if stop_h >= 0 else start_h,
            stop_m if stop_m >= 0 else start_m,
        )

    async def async_set_value(self, value: str) -> None:
        value = value.strip()
        disable_slot = value == "" or value == _SLOT_DISABLED_LABEL

        if not disable_slot and not _SLOT_PATTERN.match(value):
            raise HomeAssistantError(f"Invalid format: {value} (expected HH:MM-HH:MM)")

        if not disable_slot:
            start_str, stop_str = value.split("-")
            start_h, start_m = (int(x) for x in start_str.split(":"))
            stop_h, stop_m = (int(x) for x in stop_str.split(":"))

        timetable = []
        for i in range(4):
            if i == self._slot_index:
                if disable_slot:
                    timetable.append({
                        "start": {"hour": -1, "min": -1, "sec": -1},
                        "stop": {"hour": -1, "min": -1, "sec": -1},
                        "index": i,
                    })
                else:
                    timetable.append({
                        "start": {"hour": start_h, "min": start_m, "sec": 0},
                        "stop": {"hour": stop_h, "min": stop_m, "sec": 0},
                        "index": i,
                    })
                continue
            slot = self._timer.get_slot(i)
            if slot is None:
                timetable.append({
                    "start": {"hour": -1, "min": -1, "sec": -1},
                    "stop": {"hour": -1, "min": -1, "sec": -1},
                    "index": i,
                })
            else:
                s = slot.get("start", {}) or {}
                st = slot.get("stop", {}) or {}
                timetable.append({
                    "start": {
                        "hour": s.get("hour", -1),
                        "min": s.get("min", -1),
                        "sec": s.get("sec", -1),
                    },
                    "stop": {
                        "hour": st.get("hour", -1),
                        "min": st.get("min", -1),
                        "sec": st.get("sec", -1),
                    },
                    "index": i,
                })

        try:
            await async_set_timer_timetable(self._timer.timer_id, timetable, self._timer.gateway)
        except Exception as err:
            raise HomeAssistantError(f"Error sending timers_set_req: {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


# ============================================================
# ===== THERMOSTATS (weekly thermal profile) =====
# ============================================================

class DomoThermostatProfileText(TextEntity):
    """Time-slot string ('HH:MM-HH:MM=tN,...') for the day selected in DomoThermostatProfileDaySelect."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_max = 255
    _attr_name = "Profilo termico giornaliero (HH:MM-HH:MM=tN,...)"
    _attr_force_update = True

    def __init__(self, thermostat: DomoThermostat, entry_id: str):
        self._thermostat = thermostat
        self._attr_unique_id = f"domo_thermostat_{thermostat.act_id}_profile_text"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate_{thermostat.unique_id}")},
        )
        self._pending_display: str | None = None
        self._attempt_token: int = 0

    @property
    def native_value(self) -> str:
        if self._pending_display is not None:
            return self._pending_display
        return self._thermostat.profile_draft

    async def async_set_value(self, value: str) -> None:
        _LOGGER.debug("TEXT %s: async_set_value called with value=%r", self._attr_unique_id, value)
        self._attempt_token += 1
        my_token = self._attempt_token
        self._pending_display = "Attendere..."
        self.async_write_ha_state()
        try:
            ok = await self._thermostat.async_set_thermal_profile(value.strip())
        except ValueError as err:
            self._show_transient_message(str(err), my_token)
            raise HomeAssistantError(str(err)) from err
        except Exception as err:
            self._show_transient_message(f"Errore invio thermo_zone_config_req: {err}", my_token)
            raise HomeAssistantError(f"Error sending thermo_zone_config_req: {err}") from err
        _LOGGER.debug("TEXT %s: async_set_thermal_profile returned ok=%s", self._attr_unique_id, ok)
        if not ok:
            self._show_transient_message(
                "Comando ignorato: set_point non ancora noto per questo termostato.", my_token
            )
            raise HomeAssistantError("Command ignored: set_point not yet known for this thermostat.")
        await asyncio.sleep(2)
        if my_token == self._attempt_token:
            self._pending_display = None
            self.async_write_ha_state()

    def _show_transient_message(self, message: str, token: int) -> None:
        """Shows `message` in the field for 2 seconds, then reverts to the original profile
        (unless a new attempt has started meanwhile, tracked via `token`)."""
        self._pending_display = message
        self.async_write_ha_state()

        async def _revert():
            await asyncio.sleep(2)
            if token == self._attempt_token:
                self._pending_display = None
                self.async_write_ha_state()

        if self.hass:
            self.hass.async_create_task(_revert())

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._thermostat.unique_id:
            current_state = self.hass.states.get(self.entity_id) if self.hass else None
            if current_state is not None and current_state.state == self.native_value:
                return
            self.async_write_ha_state()


# ============================================================
# ===== LOAD CONTROL (daily energy profile) =====
# ============================================================

def _loadsctrl_meter_device_info(meter: DomoLoadCtrlMeter) -> DeviceInfo:
    """DeviceInfo of the load control manager (e.g. 'General'). Same identifiers
    used in domo/sensor.py, domo/switch.py and domo/select.py."""
    return DeviceInfo(
        identifiers={(DOMAIN, meter.unique_id)},
        name=meter.name,
        manufacturer="Home Sapiens Assistant",
        model="Eti/Domo",
    )


class DomoLoadCtrlProfileText(TextEntity):
    """Time-slot string ('HH:MM-HH:MM=N,...') for the day selected in
    DomoLoadCtrlProfileDaySelect."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_max = 255
    _attr_name = "Profilo energetico (H-H=W, H-H=W)"
    _attr_force_update = True

    def __init__(self, meter: DomoLoadCtrlMeter):
        self._meter = meter
        self._attr_unique_id = f"{meter.unique_id}_profile_text"
        self._attr_device_info = _loadsctrl_meter_device_info(meter)
        self._pending_display: str | None = None
        self._attempt_token: int = 0

    @property
    def native_value(self) -> str:
        if self._pending_display is not None:
            return self._pending_display
        return self._meter.profile_draft

    async def async_set_value(self, value: str) -> None:
        _LOGGER.debug("LOADSCTRL TEXT %s: async_set_value called with value=%r", self._attr_unique_id, value)
        self._attempt_token += 1
        my_token = self._attempt_token
        self._pending_display = "Attendere..."
        self.async_write_ha_state()
        try:
            await self._meter.async_set_profile(value.strip())
        except LoadCtrlProfileError as err:
            self._show_transient_message(str(err), my_token)
            raise HomeAssistantError(str(err)) from err
        except Exception as err:
            self._show_transient_message(f"Errore invio loadsctrl_meter_set_req: {err}", my_token)
            raise HomeAssistantError(f"Error sending loadsctrl_meter_set_req: {err}") from err
        await asyncio.sleep(2)
        if my_token == self._attempt_token:
            self._pending_display = None
            self.async_write_ha_state()

    def _show_transient_message(self, message: str, token: int) -> None:
        """Shows `message` in the field for 2 seconds."""
        self._pending_display = message
        self.async_write_ha_state()

        async def _revert():
            await asyncio.sleep(2)
            if token == self._attempt_token:
                self._pending_display = None
                self.async_write_ha_state()

        if self.hass:
            self.hass.async_create_task(_revert())

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._meter.unique_id:
            current_state = self.hass.states.get(self.entity_id) if self.hass else None
            if current_state is not None and current_state.state == self.native_value:
                return
            self.async_write_ha_state()


# ============================================================
# ===== SECURITY (silence sirens / reset event memory) =====
# ============================================================

class DomoSicuActionText(TextEntity):
    """Write-only text: the entered code is sent immediately as a command
    (silence / reset_event_memory) to the central unit and the field reverts to empty.
    Appears as a control in the 'Alarm' device (same device as alarm_control_panel)."""

    _attr_should_poll = False
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 23

    _TARGET_STATUS = {
        "silence": {3072, 11264},
        "reset_event_memory": {0, 8192, 9216},
    }

    _SEND_REQUIRES = {
        "silence": {3328, 11520},
    }

    def __init__(self, entry_id: str, action: str, name: str, icon: str):
        self._action = action
        self._attr_unique_id = f"{entry_id}_sicu_{action}_code"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "burglar_alarm")},
            name="Alarm",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )
        self._pending_display: str | None = None
        self._attempt_token: int = 0

    @property
    def native_value(self) -> str:
        if self._pending_display is not None:
            return self._pending_display
        return ""

    async def async_set_value(self, value: str) -> None:
        code = value.strip()
        device = get_security_device()
        if not device:
            raise HomeAssistantError("Security central unit not available")

        self._attempt_token += 1
        my_token = self._attempt_token

        initial_status = device.state.get("status")

        required = self._SEND_REQUIRES.get(self._action)
        if required is not None and initial_status not in required:
            _LOGGER.debug(
                "SICU ACTION %s: precondition not met (status=%s), command not sent",
                self._action, initial_status,
            )
            self._pending_display = "Nessuna azione eseguita"
            self.async_write_ha_state()
            await asyncio.sleep(2)
            if my_token == self._attempt_token:
                self._pending_display = None
                self.async_write_ha_state()
            return

        try:
            if self._action == "silence":
                await device.silence(code)
            else:
                await device.reset_event_memory(code)
        except Exception as err:
            self._show_transient_message("Errore", my_token)
            raise HomeAssistantError(f"Error in SICU ACTION {self._action}: {err}") from err

        if initial_status in self._TARGET_STATUS.get(self._action, set()):
            _LOGGER.info(
                "SICU ACTION %s: central already idle (status=%s), no action needed",
                self._action, initial_status,
            )
            self._pending_display = "Nessuna azione eseguita"
        else:
            confirmed = await self._wait_for_confirmation(device, initial_status)
            if confirmed:
                _LOGGER.info("SICU ACTION %s confirmed by central unit", self._action)
                self._pending_display = "eseguito"
            else:
                _LOGGER.warning(
                    "SICU ACTION %s NOT confirmed within timeout (current status=%s)",
                    self._action, device.state.get("status"),
                )
                self._pending_display = "Errore"
        self.async_write_ha_state()

        await asyncio.sleep(2)
        if my_token == self._attempt_token:
            self._pending_display = None
            self.async_write_ha_state()

    async def _wait_for_confirmation(self, device, initial_status, timeout: float = 2.0) -> bool:
        """Polls until the central unit's status reaches one of the expected values
        for the current action, within `timeout` seconds. Requires an actual
        transition from `initial_status`."""
        targets = self._TARGET_STATUS.get(self._action, set())
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            status = device.state.get("status")
            if status in targets and status != initial_status:
                _LOGGER.debug(
                    "SICU ACTION %s: status confirmed %s (%s)",
                    self._action, status, CENTRAL_STATUS_MAP.get(status),
                )
                return True
            await asyncio.sleep(0.1)
        return False

    def _show_transient_message(self, message: str, token: int) -> None:
        """Shows `message` in the field for 2 seconds, then reverts to empty."""
        self._pending_display = message
        self.async_write_ha_state()

        async def _revert():
            await asyncio.sleep(2)
            if token == self._attempt_token:
                self._pending_display = None
                self.async_write_ha_state()

        if self.hass:
            self.hass.async_create_task(_revert())

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


# ============================================================
# ===== SCENARIOS (create / rename / delete) =====
# ============================================================

class DomoScenarioNameText(TextEntity):
    """Single field for the name of a new scenario or for renaming an existing one;
    also shows registration status messages."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_max = 64
    _attr_icon = "mdi:palette"
    _attr_name = "Nome scenario"

    def __init__(self, device: DomoScenarioDevice, entry_id: str):
        self._device = device
        self._attr_unique_id = "domo_scenario_name_text"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenari",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

    @property
    def native_value(self) -> str:
        if self._device.status_message is not None:
            return self._device.status_message
        if self._device.registration_state == "recording":
            return f"Registrazione in corso: {self._device.name_draft}"
        if self._device.rename_pending:
            return "Nuovo nome: "
        return self._device.name_draft or ""

    async def async_set_value(self, value: str) -> None:
        await self._device.submit_text_value(value.strip())
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()
