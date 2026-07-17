"""
domo/switch.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""

from __future__ import annotations
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY, SIGNAL_DISCOVERY_NEW
from .platforms.activations import DomoActivation, get_all_activations
from .platforms.scheduler import (
    DomoTimer,
    get_all_timers,
    WEEKDAYS,
    async_set_timer_enabled,
    async_set_timer_day,
)

_LOGGER = logging.getLogger(__name__)

# ============================================================
# ENTITA' SWITCH PER LE ATTIVAZIONI (esistente)
# ============================================================
class DomoSwitchEntity(SwitchEntity):
    """Switch entity per attivazioni"""
    
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
        """Initialize the switch entity."""
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
# ENTITA' SWITCH PER I TEMPORIZZATORI
# ============================================================
_WEEKDAY_LABELS = {
    "mon": "Lunedi'", "tue": "Martedi'", "wed": "Mercoledi'", "thu": "Giovedi'",
    "fri": "Venerdi'", "sat": "Sabato", "sun": "Domenica",
}


class DomoTimerEnabledSwitch(SwitchEntity):
    """Entita' 'switch' per lo stato enabled/disabled del temporizzatore."""

    _attr_should_poll = False

    def __init__(self, timer: DomoTimer, entry_id: str):
        self._timer = timer
        self._attr_unique_id = f"domo_timer_{timer.timer_id}_enabled"
        self._attr_name = "Abilitazione"
        self._attr_icon = "mdi:calendar-check"
        
        # Creazione del dispositivo per questo timer
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_timer_{timer.timer_id}")},
            name=timer.name,
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

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
            raise HomeAssistantError(f"Errore invio timers_enable_req: {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


class DomoTimerWeekdaySwitch(SwitchEntity):
    """Entita' 'switch' per un singolo giorno della settimana."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, timer: DomoTimer, weekday: str, entry_id: str):
        self._timer = timer
        self._weekday = weekday
        self._attr_unique_id = f"domo_timer_{timer.timer_id}_day_{weekday}"
        self._attr_name = _WEEKDAY_LABELS[weekday]
        self._attr_icon = "mdi:calendar-week"
        
        # Creazione del dispositivo per questo timer
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_timer_{timer.timer_id}")},
            name=timer.name,
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

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
            raise HomeAssistantError(f"Errore invio timers_enable_day_req: {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


# ============================================================
# SETUP ENTRY (attivazioni + timer switch)
# ============================================================
async def async_setup_entry(hass, entry, async_add_entities):
    """Setup switch platform per attivazioni e temporizzatori."""
    
    # ----- ATTIVAZIONI -----
    activations = get_all_activations()
    if activations:
        activations_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_activations")},
            name="Activations",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )
        entities = [DomoSwitchEntity(activation, activations_device_info, entry.entry_id) 
                    for activation in activations]
        async_add_entities(entities)
        _LOGGER.info("Added %d switch entities for activations", len(entities))
    else:
        _LOGGER.debug("No activations found yet")

    # ----- TEMPORIZZATORI (SCHEDULER) -----
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
