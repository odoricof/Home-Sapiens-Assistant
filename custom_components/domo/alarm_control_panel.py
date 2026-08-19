"""
domo/alarm_control_panel.py

Entities fed by:
- platforms/sicu.py

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
from datetime import datetime
import logging
import time

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.sicu import get_security_device


_LOGGER = logging.getLogger(__name__)


PENDING_ARM_DELAY = 30
STATE_LABELS = {
    AlarmControlPanelState.ARMED_AWAY: "ATTIVO FUORI CASA",
    AlarmControlPanelState.ARMED_NIGHT: "ATTIVO NOTTE",
    AlarmControlPanelState.ARMED_HOME: "ATTIVO IN CASA",
    AlarmControlPanelState.ARMED_CUSTOM_BYPASS: "ATTIVO PARZIALMENTE",
    AlarmControlPanelState.DISARMED: "DISATTIVO",
}


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================
async def async_setup_entry(hass, entry, async_add_entities):
    """Setup alarm control panel platform."""
    _LOGGER.debug("Setting up alarm_control_panel platform (SECURITY)")

    hass.data[DOMAIN].setdefault("_security_panel_added", False)

    security = get_security_device()
    if security and not hass.data[DOMAIN]["_security_panel_added"]:
        _LOGGER.info(
            "SECURITY central already available, creating alarm panel | name=%s",
            security.name,
        )
        async_add_entities([DomoSecurityCentralEntity(security)])
        hass.data[DOMAIN]["_security_panel_added"] = True
    else:
        _LOGGER.debug("SECURITY central not yet available, will be created later")


# ============================================================
# ===== ENTITY =====
# ============================================================
class DomoSecurityCentralEntity(AlarmControlPanelEntity):
    """ETI Domo security alarm panel."""

    _attr_should_poll = False

    def __init__(self, device):
        """Initialize the alarm panel."""
        self._device = device
        self._attr_unique_id = f"{device.unique_id}_panel"
        self._attr_name = device.name
        self._last_armed_state = None
        self._last_valid_state = None
        self._last_notified_state = None
        self._notif_state_initialized = False
        self._alarm_notified = False
        self._alarm_notification_id = None
        self._pending_arm = None
        self._pending_arm_notification_id = None

    @property
    def device_info(self):
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "burglar_alarm")},
            name="Alarm",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

    # ============================================================
    # ===== FEATURE =====
    # ============================================================
    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        scenarios = getattr(self._device, "_scenarios", {})
        scenario_by_arm = getattr(self._device, "_scenario_by_arm", {})
        features = AlarmControlPanelEntityFeature.ARM_AWAY

        if scenarios.get(scenario_by_arm.get("armed_night"), {}).get("areas"):
            features |= AlarmControlPanelEntityFeature.ARM_NIGHT

        if scenarios.get(scenario_by_arm.get("armed_home"), {}).get("areas"):
            features |= AlarmControlPanelEntityFeature.ARM_HOME

        if scenarios.get(scenario_by_arm.get("armed_custom_bypass"), {}).get("areas"):
            features |= AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS
        return features

    # ============================================================
    # ===== CODE =====
    # ============================================================
    @property
    def code_arm_required(self) -> bool:
        """Whether the code is required for arm actions."""
        return True

    @property
    def code_format(self) -> str | None:
        """Return the code format."""
        return "number"

    # ============================================================
    # ===== STATE =====
    # ============================================================
    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the state of the device."""
        device = self._device
        data = getattr(device, "_last_snapshot", None)

        if not data:
            return AlarmControlPanelState.DISARMED

        areas = data.get("areas", [])
        central = data.get("central", {})
        central_status = central.get("status")

        if central_status in (3072, 3328, 11520, 11264, 2304, 10496):
            violated_inputs = []
            for inp in data.get("inputs", []):
                if inp.get("status") in (25, 17):
                    area_names = []
                    for area_id in inp.get("areas", []):
                        area = next((a for a in areas if a.get("area_id") == area_id), None)
                        if area:
                            area_names.append(area.get("name", f"area_{area_id}"))

                    violated_inputs.append({
                        "name": inp.get("name", f"input_{inp.get('input_id')}"),
                        "area": ", ".join(area_names) if area_names else "Sconosciuta"
                    })

            if violated_inputs and not self._alarm_notified:
                self._alarm_notified = True
                self.hass.async_create_task(
                    self._send_alarm_notifications(violated_inputs)
                )

            self._last_valid_state = AlarmControlPanelState.TRIGGERED
            return self._last_valid_state

        if self._pending_arm is not None:
            return AlarmControlPanelState.ARMING

        if central_status in (4096, 4352, 12288, 14336):
            return AlarmControlPanelState.ARMING

        armed_now = {
            a.get("area_id")
            for a in areas
            if a.get("status") in [42, 58]
        }

        if not armed_now:
            self._last_armed_state = None
            return AlarmControlPanelState.DISARMED

        scenarios = getattr(device, "_scenarios", {})
        scenario_by_arm = getattr(device, "_scenario_by_arm", {})
        scenario_areas = {
            role: frozenset(scenarios.get(sid, {}).get("areas", []))
            for role, sid in scenario_by_arm.items()
        }
        scenarios_are_unique = len(set(scenario_areas.values())) == len(scenario_areas)

        if scenarios_are_unique:
            if "armed_away" in scenario_areas and armed_now == scenario_areas["armed_away"]:
                self._last_armed_state = AlarmControlPanelState.ARMED_AWAY
                return self._last_armed_state

            if "armed_night" in scenario_areas and armed_now == scenario_areas["armed_night"]:
                self._last_armed_state = AlarmControlPanelState.ARMED_NIGHT
                return self._last_armed_state

            if "armed_home" in scenario_areas and armed_now == scenario_areas["armed_home"]:
                self._last_armed_state = AlarmControlPanelState.ARMED_HOME
                return self._last_armed_state

            if "armed_custom_bypass" in scenario_areas and armed_now == scenario_areas["armed_custom_bypass"]:
                self._last_armed_state = AlarmControlPanelState.ARMED_CUSTOM_BYPASS
                return self._last_armed_state

        known_areas = set(data.get("known_area_ids", []))
        if known_areas and armed_now == known_areas:
            self._last_armed_state = AlarmControlPanelState.ARMED_AWAY
            return self._last_armed_state

        if known_areas:
            self._last_armed_state = AlarmControlPanelState.ARMED_CUSTOM_BYPASS
            return self._last_armed_state

        _LOGGER.warning(
            "Unable to determine alarm_state | central_status=%s | armed_now=%s | last_armed_state=%s",
            central_status, armed_now, self._last_armed_state,
        )
        return None

    # ============================================================
    # ===== EXTRA ATTRIBUTES =====
    # ============================================================
    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        data = getattr(self._device, "_last_snapshot", None)
        if not data:
            return {}

        central = data.get("central", {}) or {}
        central_raw = central.get("status")

        central_status = self._device.decode_central_status(central_raw)

        areas = data.get("areas", [])
        areas_status = {}

        area_id_to_name = {}

        for a in areas:
            area_id = a.get("area_id")
            raw_status = a.get("status")

            area_name = (
                a.get("name")
                or a.get("area_name")
                or f"area_{area_id}"
            )

            if area_id is not None:
                area_id_to_name[area_id] = area_name

            if raw_status is None:
                continue

            areas_status[area_name] = self._device.decode_area_status(raw_status)

        inputs = data.get("inputs", [])
        inputs_status = {}

        for i in inputs:
            input_id = i.get("input_id")
            raw_status = i.get("status")

            input_name = (
                i.get("name")
                or i.get("input_name")
                or f"input_{input_id}"
            )

            if raw_status is None:
                continue

            input_areas = [
                area_id_to_name.get(aid, f"area_{aid}")
                for aid in (i.get("areas") or [])
            ]

            inputs_status[input_name] = {
                **self._device.decode_input_status(raw_status),
                "areas": input_areas,
            }

        outputs = data.get("outputs", [])
        outputs_status = {}

        for o in outputs:
            output_id = o.get("output_id")
            raw_status = o.get("status")
            output_name = o.get("name", f"output_{output_id}")

            if raw_status is None:
                continue

            outputs_status[output_name] = {
                "raw": raw_status,
                "state": "on" if raw_status == 1 else "off",
                "output_id": output_id,
            }

        return {
            "central": central_status,
            "areas": areas_status,
            "inputs": inputs_status,
            "outputs": outputs_status,
        }

    # ============================================================
    # ===== COMMANDS =====
    # ============================================================
    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        if self._pending_arm is not None:
            _LOGGER.info(
                "Disarm requested while pending arm '%s' is active: request cancelled",
                self._pending_arm.get("mode"),
            )
            await self._async_cancel_pending_arm()
            return
        await self._device.disarm(code)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self._async_handle_arm_request("armed_home", "home", code)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""
        await self._async_handle_arm_request("armed_night", "night", code)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self._async_handle_arm_request("armed_away", "away", code)

    async def async_alarm_arm_custom_bypass(self, code: str | None = None) -> None:
        """Send arm custom bypass command."""
        await self._async_handle_arm_request("armed_custom_bypass", "custom_bypass", code)

    # ============================================================
    # ===== PENDING ARM =====
    # ============================================================
    async def _async_handle_arm_request(self, arm_key: str, mode: str, code: str | None) -> None:
        """Handle an arm request, waiting if some areas are not ready."""
        await self._async_cancel_pending_arm()

        ready, not_ready_areas = self._device.scenario_ready(arm_key)

        if ready:
            await self._async_send_arm_command(mode, code)
            return

        _LOGGER.info(
            "Arm '%s' requested with areas not ready (%s): starting %ss wait",
            mode, ", ".join(not_ready_areas), PENDING_ARM_DELAY,
        )

        self._pending_arm = {
            "mode": mode,
            "code": code,
            "arm_key": arm_key,
            "ready_event": asyncio.Event(),
        }
        self.async_write_ha_state()

        await self._send_pending_arm_notification(not_ready_areas)

        self._pending_arm["task"] = self.hass.async_create_task(
            self._pending_arm_watcher(arm_key, mode, code)
        )

    async def _pending_arm_watcher(self, arm_key: str, mode: str, code: str | None) -> None:
        """Wait for areas to become ready or for PENDING_ARM_DELAY to expire.
        In both cases the arm command is sent, unless the request was
        cancelled by a disarm in the meantime.
        """
        ready_event = self._pending_arm["ready_event"]
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=PENDING_ARM_DELAY)
            _LOGGER.info("Areas ready, proceeding with arm '%s'", mode)
        except asyncio.TimeoutError:
            _LOGGER.info(
                "Timeout of %ss expired: arm '%s' forced as requested by user",
                PENDING_ARM_DELAY, mode,
            )

        await self._async_send_arm_command(mode, code)
        await self._clear_pending_arm_notification()
        self._pending_arm = None
        self.async_write_ha_state()

    async def _async_cancel_pending_arm(self) -> None:
        """Cancel a pending arm request, if present."""
        if self._pending_arm is None:
            return

        task = self._pending_arm.get("task")
        self._pending_arm = None

        if task and not task.done():
            task.cancel()

        await self._clear_pending_arm_notification()
        self.async_write_ha_state()

    async def _async_send_arm_command(self, mode: str, code: str | None) -> None:
        """Send the actual arm command to the central unit."""
        if mode == "away":
            await self._device.arm_away(code)
        elif mode == "night":
            await self._device.arm_night(code)
        elif mode == "home":
            await self._device.arm_home(code)
        elif mode == "custom_bypass":
            await self._device.arm_custom_bypass(code)

    # ============================================================
    # ===== NOTIFICATIONS =====
    # ============================================================
    async def _send_alarm_notifications(self, violated_inputs):
        """Send push and persistent notifications for the alarm."""
        now = datetime.now().strftime("%H:%M")
        if len(violated_inputs) == 1:
            msg = f"Sensore violato: {violated_inputs[0]['name']} (area {violated_inputs[0]['area']}) - {now}"
        else:
            sensori = [f"{i['name']} (area {i['area']})" for i in violated_inputs]
            msg = f"Sensori violati: {', '.join(sensori)} - {now}"

        all_services = self.hass.services.async_services()
        mobile_app_services = [
            service for service in all_services.get("notify", [])
            if service.startswith("mobile_app_")
        ]

        if mobile_app_services:
            for service in mobile_app_services:
                try:
                    await self.hass.services.async_call(
                        "notify",
                        service,
                        {
                            "title": "🚨 ALLARME IN CORSO!",
                            "message": msg,
                            "data": {
                                "priority": "high",
                                "channel": "alarm_v2",
                                "importance": "high",
                                "vibrationPattern": "500, 500, 500, 500",
                                "color": "#FF0000",
                                "led_color": "red",
                                "sticky": "true",
                                "persistent": "true",
                                "tag": "alarm_active",
                                "push": {
                                    "sound": {"name": "default", "critical": 1, "volume": 1.0},
                                    "interruption-level": "critical"
                                }
                            }
                        },
                        blocking=False
                    )
                except Exception as err:
                    _LOGGER.error("Failed to send push notification to %s: %s", service, err)
        else:
            _LOGGER.warning("No mobile_app device registered, push notifications skipped")

        self._alarm_notification_id = f"alarm_{int(time.time())}"
        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "🚨 ALLARME IN CORSO!",
                    "message": msg,
                    "notification_id": self._alarm_notification_id
                },
                blocking=True
            )
        except Exception as err:
            _LOGGER.error("Failed to create persistent notification: %s", err)

    async def _send_state_change_notification(self, state) -> None:
        """Send a push notification on panel state change."""
        label = STATE_LABELS.get(state, str(state))
        now = datetime.now().strftime("%H:%M")
        title = "🛡️ CENTRALE ANTIFURTO"
        msg = f"Stato: {label} - {now}"

        all_services = self.hass.services.async_services()
        mobile_app_services = [
            service for service in all_services.get("notify", [])
            if service.startswith("mobile_app_")
        ]

        if not mobile_app_services:
            _LOGGER.warning("No mobile_app device registered, state-change notification skipped")
            return

        for service in mobile_app_services:
            try:
                await self.hass.services.async_call(
                    "notify",
                    service,
                    {
                        "title": title,
                        "message": msg,
                        "data": {
                            "channel": "alarm",
                        },
                    },
                    blocking=False,
                )
            except Exception as err:
                _LOGGER.error("Failed to send state-change push notification to %s: %s", service, err)

    async def _send_pending_arm_notification(self, not_ready_areas):
        """Send push/persistent notification for a pending arm with open inputs."""
        aree = ", ".join(not_ready_areas) if not_ready_areas else "sconosciuta"
        msg = f"Attenzione: inserimento in corso con ingressi aperti (area: {aree})"

        all_services = self.hass.services.async_services()
        mobile_app_services = [
            service for service in all_services.get("notify", [])
            if service.startswith("mobile_app_")
        ]

        if mobile_app_services:
            for service in mobile_app_services:
                try:
                    await self.hass.services.async_call(
                        "notify",
                        service,
                        {
                            "title": "⚠️ INSERIMENTO IN ATTESA",
                            "message": msg,
                            "data": {
                                "priority": "high",
                                "channel": "alarm",
                            }
                        },
                        blocking=False,
                    )
                except Exception as err:
                    _LOGGER.error("Failed to send pending-arm push notification to %s: %s", service, err)
        else:
            _LOGGER.warning("No mobile_app device registered, pending-arm notification skipped")

        self._pending_arm_notification_id = f"pending_arm_{int(time.time())}"
        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "⚠️ INSERIMENTO IN ATTESA",
                    "message": msg,
                    "notification_id": self._pending_arm_notification_id
                },
                blocking=True,
            )
        except Exception as err:
            _LOGGER.error("Failed to create pending-arm persistent notification: %s", err)

    async def _clear_pending_arm_notification(self):
        """Remove the pending-arm notification."""
        if self._pending_arm_notification_id:
            try:
                await self.hass.services.async_call(
                    "persistent_notification",
                    "dismiss",
                    {
                        "notification_id": self._pending_arm_notification_id
                    },
                    blocking=True,
                )
                _LOGGER.debug("Pending-arm notification cleared")
            except Exception as err:
                _LOGGER.error("Failed to clear pending-arm notification: %s", err)
            self._pending_arm_notification_id = None

    async def _clear_alarm_notification(self):
        """Remove the persistent notification when the alarm ends."""
        if self._alarm_notification_id:
            try:
                await self.hass.services.async_call(
                    "persistent_notification",
                    "dismiss",
                    {
                        "notification_id": self._alarm_notification_id
                    },
                    blocking=True
                )
                self._alarm_notification_id = None
                _LOGGER.debug("Alarm notification cleared")
            except Exception as err:
                _LOGGER.error("Failed to clear notification: %s", err)

    # ============================================================
    # ===== UPDATE =====
    # ============================================================
    async def async_added_to_hass(self):
        """When entity is added to hass."""
        _LOGGER.debug("SECURITY PANEL added to hass | entity_id=%s", self.entity_id)

        if not self.hass.services.has_service(DOMAIN, "security_panel_action"):
            async def async_security_panel_action(call):
                entity_id = call.data.get("entity_id")
                action = call.data.get("action")
                code = call.data.get("code")

                _LOGGER.debug(
                    "security_panel_action called | entity_id=%s | action=%s | target=%s | my_entity_id=%s",
                    entity_id, action, entity_id, self.entity_id,
                )

                if entity_id != self.entity_id:
                    _LOGGER.debug("Entity id mismatch | got=%s | expected=%s", entity_id, self.entity_id)
                    return

                if action == "reset_event_memory":
                    await self.reset_event_memory(code)
                elif action == "silence":
                    await self.silence(code)

            self.hass.services.async_register(
                DOMAIN,
                "security_panel_action",
                async_security_panel_action,
            )

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle update signal."""
        if entity_id is not None and entity_id != self._attr_unique_id:
            return
        data = getattr(self._device, "_last_snapshot", None)
        if data:
            central = data.get("central", {})
            central_status = central.get("status")

            if central_status == 8192 and self._alarm_notification_id:
                self.hass.async_create_task(self._clear_alarm_notification())
                self._alarm_notified = False

            if self._pending_arm is not None:
                ready, _ = self._device.scenario_ready(self._pending_arm["arm_key"])
                if ready:
                    self._pending_arm["ready_event"].set()

        new_state = self.alarm_state
        if new_state not in (None, AlarmControlPanelState.ARMING, AlarmControlPanelState.TRIGGERED):
            if not self._notif_state_initialized:
                self._notif_state_initialized = True
                self._last_notified_state = new_state
            elif new_state != self._last_notified_state:
                self._last_notified_state = new_state
                self.hass.async_create_task(self._send_state_change_notification(new_state))

        self.async_write_ha_state()
