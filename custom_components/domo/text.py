"""
domo/text.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging
import re

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_DISCOVERY_NEW, SIGNAL_UPDATE_ENTITY
from .platforms.scheduler import (
    DomoTimer,
    get_all_timers,
    async_set_timer_timetable,
)

_LOGGER = logging.getLogger(__name__)

_SLOT_PATTERN = re.compile(r"^(|Disabilitato|([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d)$")
_SLOT_DISABLED_LABEL = "Disabilitato"


class DomoTimerSlotText(TextEntity):
    """Entita' 'text' per uno slot orario (bar) di un temporizzatore. Fase A: sola lettura."""

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
        
        # Creazione del dispositivo per questo timer
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
            raise HomeAssistantError(f"Formato non valido: {value} (atteso HH:MM-HH:MM)")

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
            raise HomeAssistantError(f"Errore invio timers_set_req: {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup piattaforma text per gli slot orari dei temporizzatori (SCHEDULER)."""
    _LOGGER.debug("Setup piattaforma text (SCHEDULER)")

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
