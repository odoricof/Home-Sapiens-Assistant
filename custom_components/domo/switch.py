"""
domo/switch.py

Entities fed by:
- platforms/activations.py
- platforms/scheduler.py
- platforms/irrigation.py
- platforms/loadsctrl.py

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

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_DISCOVERY_NEW, SIGNAL_UPDATE_ENTITY
from .platforms.activations import DomoActivation, get_all_activations
from .platforms.irrigation import (
    DomoIrrigationZone,
    WEEKDAYS as IRRIGATION_WEEKDAYS,
    async_force_irrigation,
    async_set_irrigation_day,
    async_set_irrigation_enabled,
    async_set_sprinkler_enabled,
    get_all_irrigation_zones,
)
from .platforms.loadsctrl import (
    DomoLoadCtrlMeter,
    DomoLoadCtrlRelay,
    async_set_loadsctrl_relay_enabled,
    get_all_loadsctrl_relays,
)
from .platforms.scheduler import (
    DomoTimer,
    WEEKDAYS,
    async_set_timer_day,
    async_set_timer_enabled,
    get_all_timers,
)

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up switch platform for activations, timers, irrigation and load control."""

    # --- Activations ---
    activations = get_all_activations()
    if activations:
        activations_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_activations")},
            name="Activations",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )
        entities = [
            DomoSwitchEntity(activation, activations_device_info, entry.entry_id)
            for activation in activations
        ]
        async_add_entities(entities)
        _LOGGER.info("Added %d switch entities for activations", len(entities))
    else:
        _LOGGER.debug("No activations found")

    # --- Timers (Scheduler) ---
    scheduler_added_ids: set[int] = set()

    def _add_timer_switches(timer: DomoTimer):
        if timer.timer_id in scheduler_added_ids:
            return
        scheduler_added_ids.add(timer.timer_id)
        entities = [
            DomoTimerEnabledSwitch(timer, entry.entry_id),
            *[DomoTimerWeekdaySwitch(timer, wd, entry.entry_id) for wd in WEEKDAYS],
        ]
        async_add_entities(entities)
        _LOGGER.info(
            "Added %d switch entities for timer id=%s (%s)",
            len(entities), timer.timer_id, timer.name,
        )

    for timer in get_all_timers():
        _add_timer_switches(timer)

    @callback
    def _async_new_scheduler_timer(timer: DomoTimer):
        _add_timer_switches(timer)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_DISCOVERY_NEW.format("switch"), _async_new_scheduler_timer
        )
    )

    # --- Irrigation (zones + sprinklers) ---
    irrigation_added_ids: set[int] = set()

    def _add_irrigation_switches(zone: DomoIrrigationZone):
        if zone.zone_id in irrigation_added_ids:
            return
        irrigation_added_ids.add(zone.zone_id)
        entities = [
            DomoIrrigationEnabledSwitch(zone, entry.entry_id),
            DomoIrrigationForceSwitch(zone, entry.entry_id),
            *[DomoIrrigationDaySwitch(zone, wd, entry.entry_id) for wd in IRRIGATION_WEEKDAYS],
            *[DomoSprinklerSwitch(zone, spr.act_id, entry.entry_id) for spr in zone.sprinklers],
        ]
        async_add_entities(entities)
        _LOGGER.info(
            "Added %d switch entities for irrigation zone id=%s (%s)",
            len(entities), zone.zone_id, zone.name,
        )

    for zone in get_all_irrigation_zones():
        _add_irrigation_switches(zone)

    @callback
    def _async_new_irrigation_zone(zone: DomoIrrigationZone):
        _add_irrigation_switches(zone)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_DISCOVERY_NEW.format("irrigation_switch"), _async_new_irrigation_zone
        )
    )

    # --- Load Control (loadsctrl) ---
    loadsctrl_added_ids: set[int] = set()

    def _add_loadsctrl_switch(relay: DomoLoadCtrlRelay):
        if relay.relay_id in loadsctrl_added_ids:
            return
        loadsctrl_added_ids.add(relay.relay_id)
        async_add_entities([DomoLoadCtrlRelaySwitch(relay)])
        _LOGGER.info(
            "Added switch entity for load control relay id=%s (%s)",
            relay.relay_id, relay.name,
        )

    for relay in get_all_loadsctrl_relays():
        _add_loadsctrl_switch(relay)

    @callback
    def _async_new_loadsctrl_relay(relay: DomoLoadCtrlRelay):
        _add_loadsctrl_switch(relay)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_switch"), _async_new_loadsctrl_relay
        )
    )


# ============================================================
# ===== ACTIVATIONS =====
# ============================================================

class DomoSwitchEntity(SwitchEntity):
    """Switch for a generic activation (light, climate, gate, etc.)."""

    DEFAULT_ICON = "mdi:electric-switch"
    ICON_MAP = {
        1: "mdi:lightbulb-on-outline",
        2: "mdi:air-conditioner",
        3: "mdi:radiator",
        4: "mdi:television-classic",
        5: "mdi:pipe-valve",
        6: "mdi:pipe-valve",
        7: "mdi:doorbell",
        8: "mdi:power-socket-eu",
        9: "mdi:roller-shade",
        10: "mdi:roller-shade-closed",
        11: "mdi:gate-open",
        12: "mdi:gate",
        13: "mdi:gate-open",
        14: "mdi:gate",
        15: "mdi:boom-gate-arrow-up-outline",
        16: "mdi:boom-gate-arrow-down-outline",
        17: "mdi:car-off",
        18: "mdi:car-off",
        19: "mdi:turnstile-outline",
        20: "mdi:turnstile",
        21: "mdi:door-sliding-open",
        22: "mdi:door-sliding",
        23: "mdi:garage-open-variant",
        24: "mdi:garage-variant",
        25: "mdi:speaker",
        26: "mdi:projector-screen-variant-off-outline",
        27: "mdi:projector-screen-variant-outline",
        28: "mdi:fridge-outline",
        29: "mdi:washing-machine",
        30: "mdi:toaster-oven",
        31: "mdi:key",
        32: "mdi:solar-power-variant-outline",
        33: "mdi:heat-pump",
        34: "mdi:wind-power",
        35: "mdi:hvac",
        36: "mdi:ceiling-fan",
    }

    def __init__(self, activation: DomoActivation, device_info: DeviceInfo, entry_id: str):
        """Inizializza lo switch per l'attivazione."""
        self._activation = activation
        self._attr_unique_id = activation.unique_id
        self._attr_name = activation.name
        self._attr_should_poll = False
        self._attr_device_info = device_info

    @property
    def icon(self) -> str | None:
        icon_id = self._activation.icon_id
        if icon_id and icon_id in self.ICON_MAP:
            return self.ICON_MAP[icon_id]
        return self.DEFAULT_ICON

    @property
    def is_on(self) -> bool:
        return self._activation.is_on

    async def async_turn_on(self, **kwargs):
        await self._activation.async_turn_on()

    async def async_turn_off(self, **kwargs):
        await self._activation.async_turn_off()

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


# ============================================================
# ===== TIMERS =====
# ============================================================

_WEEKDAY_LABELS = {
    "mon": "Lunedi'",
    "tue": "Martedi'",
    "wed": "Mercoledi'",
    "thu": "Giovedi'",
    "fri": "Venerdi'",
    "sat": "Sabato",
    "sun": "Domenica",
}


def _timer_device_info(timer: DomoTimer, entry_id: str) -> DeviceInfo:
    """DeviceInfo for the 'timer' device, shared by all entities of the same timer."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_timer_{timer.timer_id}")},
        name=timer.name,
        manufacturer="Home Sapiens Assistant",
        model="Eti/Domo",
    )


class DomoTimerEnabledSwitch(SwitchEntity):
    """Switch to enable/disable a timer."""

    _attr_should_poll = False

    def __init__(self, timer: DomoTimer, entry_id: str):
        self._timer = timer
        self._attr_unique_id = f"domo_timer_{timer.timer_id}_enabled"
        self._attr_name = "Abilitazione"
        self._attr_icon = "mdi:calendar-check"
        self._attr_device_info = _timer_device_info(timer, entry_id)

    @property
    def is_on(self) -> bool:
        return self._timer.enabled

    async def async_turn_on(self, **kwargs):
        await self._async_set_enabled(1)

    async def async_turn_off(self, **kwargs):
        await self._async_set_enabled(0)

    async def _async_set_enabled(self, value: int) -> None:
        try:
            await async_set_timer_enabled(self._timer.timer_id, value, self._timer.gateway)
        except Exception as err:
            raise HomeAssistantError(f"Error sending timers_enable_req: {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


class DomoTimerWeekdaySwitch(SwitchEntity):
    """Switch to enable a single weekday in the timer."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, timer: DomoTimer, weekday: str, entry_id: str):
        self._timer = timer
        self._weekday = weekday
        self._attr_unique_id = f"domo_timer_{timer.timer_id}_day_{weekday}"
        self._attr_name = _WEEKDAY_LABELS[weekday]
        self._attr_icon = "mdi:calendar-week"
        self._attr_device_info = _timer_device_info(timer, entry_id)

    @property
    def is_on(self) -> bool:
        return self._weekday in self._timer.active_weekdays

    async def async_turn_on(self, **kwargs):
        await self._async_set_day(1)

    async def async_turn_off(self, **kwargs):
        await self._async_set_day(0)

    async def _async_set_day(self, value: int) -> None:
        day_index = WEEKDAYS.index(self._weekday)
        try:
            await async_set_timer_day(self._timer.timer_id, day_index, value, self._timer.gateway)
        except Exception as err:
            raise HomeAssistantError(f"Error sending timers_enable_day_req: {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


# ============================================================
# ===== IRRIGATION =====
# ============================================================

def _irrigation_zone_device_info(zone: DomoIrrigationZone, entry_id: str) -> DeviceInfo:
    """DeviceInfo for the 'irrigation zone' device, shared by all entities of the zone."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_irrigation_{zone.zone_id}")},
        name=zone.name,
        manufacturer="Home Sapiens Assistant",
        model="Eti/Domo",
    )


class DomoIrrigationEnabledSwitch(SwitchEntity):
    """Switch to enable/disable an irrigation zone."""

    _attr_should_poll = False

    def __init__(self, zone: DomoIrrigationZone, entry_id: str):
        self._zone = zone
        self._attr_unique_id = f"domo_irrigation_{zone.zone_id}_enabled"
        self._attr_name = "Abilitazione"
        self._attr_icon = "mdi:sprinkler-variant"
        self._attr_device_info = _irrigation_zone_device_info(zone, entry_id)

    @property
    def is_on(self) -> bool:
        return self._zone.enabled

    async def async_turn_on(self, **kwargs):
        await self._async_set_enabled(1)

    async def async_turn_off(self, **kwargs):
        await self._async_set_enabled(0)

    async def _async_set_enabled(self, value: int) -> None:
        try:
            await async_set_irrigation_enabled(self._zone.zone_id, value, self._zone.gateway)
        except Exception as err:
            raise HomeAssistantError(f"Error sending irrigation_set_req (enabled): {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._zone.unique_id:
            self.async_write_ha_state()


class DomoIrrigationDaySwitch(SwitchEntity):
    """Switch to enable a single weekday for an irrigation zone."""

    _attr_should_poll = False

    def __init__(self, zone: DomoIrrigationZone, weekday: str, entry_id: str):
        self._zone = zone
        self._weekday = weekday
        self._attr_unique_id = f"domo_irrigation_{zone.zone_id}_day_{weekday}"
        self._attr_name = _WEEKDAY_LABELS[weekday]
        self._attr_icon = "mdi:calendar-week"
        self._attr_device_info = _irrigation_zone_device_info(zone, entry_id)

    @property
    def is_on(self) -> bool:
        return self._weekday in self._zone.active_weekdays

    async def async_turn_on(self, **kwargs):
        await self._async_set_day(1)

    async def async_turn_off(self, **kwargs):
        await self._async_set_day(0)

    async def _async_set_day(self, value: int) -> None:
        day_index = IRRIGATION_WEEKDAYS.index(self._weekday)
        try:
            await async_set_irrigation_day(
                self._zone.zone_id, day_index, value, self._zone.gateway
            )
        except Exception as err:
            raise HomeAssistantError(f"Error sending irrigation_set_req (days): {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._zone.unique_id:
            self.async_write_ha_state()


class DomoIrrigationForceSwitch(SwitchEntity):
    """Switch to manually force irrigation for a zone."""

    _attr_should_poll = False
    _attr_icon = "mdi:hand-back-right"

    def __init__(self, zone: DomoIrrigationZone, entry_id: str):
        self._zone = zone
        self._attr_unique_id = f"domo_irrigation_{zone.zone_id}_forced"
        self._attr_name = "Modalità manuale"
        self._attr_device_info = _irrigation_zone_device_info(zone, entry_id)

    @property
    def is_on(self) -> bool:
        return self._zone.forced

    async def async_turn_on(self, **kwargs):
        if not self._zone.forced:
            await self._async_toggle()

    async def async_turn_off(self, **kwargs):
        if self._zone.forced:
            await self._async_toggle()

    async def _async_toggle(self) -> None:
        try:
            await async_force_irrigation(self._zone.zone_id, self._zone.gateway)
        except Exception as err:
            raise HomeAssistantError(f"Error sending irrigation_force_req: {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._zone.unique_id:
            self.async_write_ha_state()


class DomoSprinklerSwitch(SwitchEntity):
    """Switch to enable/disable a single sprinkler in a zone."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, zone: DomoIrrigationZone, act_id: int, entry_id: str):
        self._zone = zone
        self._act_id = act_id
        self._attr_unique_id = f"domo_irrigation_{zone.zone_id}_sprinkler_{act_id}"
        sprinkler = zone.get_sprinkler(act_id)
        self._attr_name = sprinkler.name if sprinkler else f"Irrigatore {act_id}"
        self._attr_device_info = _irrigation_zone_device_info(zone, entry_id)

    @property
    def is_on(self) -> bool:
        sprinkler = self._zone.get_sprinkler(self._act_id)
        return sprinkler.enabled if sprinkler else False

    @property
    def icon(self) -> str:
        sprinkler = self._zone.get_sprinkler(self._act_id)
        return "mdi:sprinkler-variant" if sprinkler and sprinkler.is_active else "mdi:sprinkler"

    @property
    def extra_state_attributes(self) -> dict:
        sprinkler = self._zone.get_sprinkler(self._act_id)
        if sprinkler is None:
            return {}
        return {
            "in_funzione": sprinkler.is_active,
            "tempo_massimo_min": None if sprinkler.active is None else round(sprinkler.active / 60),
            "ciclo_di_lavoro_pct": sprinkler.duty,
        }

    async def async_turn_on(self, **kwargs):
        await self._async_set_enabled(1)

    async def async_turn_off(self, **kwargs):
        await self._async_set_enabled(0)

    async def _async_set_enabled(self, value: int) -> None:
        try:
            await async_set_sprinkler_enabled(
                self._zone.zone_id, self._act_id, value, self._zone.gateway
            )
        except Exception as err:
            raise HomeAssistantError(
                f"Error sending irrigation_set_req (sprinklers): {err}"
            ) from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


# ============================================================
# ===== LOAD CONTROL =====
# ============================================================

def _loadsctrl_meter_device_info(meter: DomoLoadCtrlMeter) -> DeviceInfo:
    """DeviceInfo for the load control manager (e.g. 'General'). Same identifiers used in domo/sensor.py."""
    return DeviceInfo(
        identifiers={(DOMAIN, meter.unique_id)},
        name=meter.name,
        manufacturer="Home Sapiens Assistant",
        model="Eti/Domo",
        via_device=(DOMAIN, "loadsctrl_root"),
    )


class DomoLoadCtrlRelaySwitch(SwitchEntity):
    """Switch to enable/disable control of a load (e.g. 'Kitchen appliances')."""

    _attr_should_poll = False

    def __init__(self, relay: DomoLoadCtrlRelay):
        self._relay = relay
        self._attr_unique_id = relay.unique_id
        self._attr_name = relay.name
        self._attr_device_info = _loadsctrl_meter_device_info(relay.meter)

    @property
    def is_on(self) -> bool:
        return self._relay.enabled

    @property
    def icon(self) -> str:
        if self._relay.is_detached:
            return "mdi:power-plug-off"
        return "mdi:power-plug"

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "priority": self._relay.priority,
            "status": self._relay.status,
            "detached": self._relay.is_detached,
            "loadtype": self._relay.loadtype,
        }

    async def async_turn_on(self, **kwargs):
        await self._async_set_enabled(1)

    async def async_turn_off(self, **kwargs):
        await self._async_set_enabled(0)

    async def _async_set_enabled(self, value: int) -> None:
        try:
            await async_set_loadsctrl_relay_enabled(
                self._relay.relay_id, value, self._relay.gateway
            )
        except Exception as err:
            raise HomeAssistantError(f"Error sending loadsctrl_relay_set_req: {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()
