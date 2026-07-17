"""
platforms/scheduler.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import DOMAIN, SIGNAL_DISCOVERY_NEW, SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

_TIMERS: Dict[int, "DomoTimer"] = {}


def _decode_days(days: int) -> List[str]:
    """Decodifica la bitmask 'days' nei giorni della settimana attivi."""
    return [WEEKDAYS[i] for i in range(7) if days & (1 << i)]


class DomoTimer:
    """Temporizzatore ETI Domo / CAME Domotic (feature 'timer')."""

    def __init__(self, gateway, data: Dict[str, Any]):
        self._gateway = gateway
        self._id = data["id"]
        self._name = data.get("name", f"Timer {self._id}")
        self._enabled = bool(data.get("enabled", 0))
        self._days = data.get("days", 0)
        self._bars = data.get("bars", 0)
        self._timetable = data.get("timetable", []) or []

        _TIMERS[self._id] = self

        _LOGGER.debug(
            "SCHEDULER timer created | id=%s name=%s enabled=%s days=%s bars=%s timetable=%s",
            self._id, self._name, self._enabled, self._days, self._bars, self._timetable,
        )

    # --------------------------------------------------
    # PROPRIETA'
    # --------------------------------------------------
    @property
    def timer_id(self) -> int:
        return self._id

    @property
    def gateway(self):
        return self._gateway

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"schedule.domo_timer_{self._id}"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def days(self) -> int:
        return self._days

    @property
    def active_weekdays(self) -> List[str]:
        return _decode_days(self._days)

    @property
    def bars(self) -> int:
        return self._bars

    @property
    def timetable(self) -> List[dict]:
        return self._timetable

    def get_slot(self, index: int) -> Optional[dict]:
        """Restituisce lo slot orario con il dato index, o None se non configurato."""
        for slot in self._timetable:
            if slot.get("index") == index:
                return slot
        return None

    def is_slot_active(self, index: int) -> bool:
        """True se l'orario corrente rientra nel range dello slot (campo 'active' del gateway)."""
        slot = self.get_slot(index)
        if slot is None:
            return False
        return bool(slot.get("active"))

    def weekly_schedule(self) -> Dict[str, List[Dict[str, str]]]:
        """Ricostruisce lo schema settimanale {giorno: [{from, to}, ...]}."""
        ranges = []
        for slot in self._timetable:
            start = slot.get("start", {}) or {}
            stop = slot.get("stop", {}) or {}
            ranges.append({
                "from": "{:02d}:{:02d}:{:02d}".format(
                    start.get("hour", 0), start.get("min", 0), start.get("sec", 0)
                ),
                "to": "{:02d}:{:02d}:{:02d}".format(
                    stop.get("hour", 0), stop.get("min", 0), stop.get("sec", 0)
                ),
                "active": slot.get("active"),
                "index": slot.get("index"),
            })

        active_days = set(self.active_weekdays)
        return {day: (ranges if day in active_days else []) for day in WEEKDAYS}

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------
    def update(self, data: Dict[str, Any]) -> bool:
        """Aggiorna il temporizzatore con i nuovi dati ricevuti dal bus."""
        if data.get("id") != self._id:
            return False

        changed = False
        field_map = {
            "name": "_name",
            "enabled": "_enabled",
            "days": "_days",
            "bars": "_bars",
            "timetable": "_timetable",
        }
        for key, attr in field_map.items():
            if key not in data:
                continue
            new_value = bool(data[key]) if key == "enabled" else data[key]
            if getattr(self, attr) != new_value:
                setattr(self, attr, new_value)
                changed = True

        if changed:
            _LOGGER.debug(
                "SCHEDULER timer updated | id=%s name=%s enabled=%s days=%s timetable=%s",
                self._id, self._name, self._enabled, self._days, self._timetable,
            )
        return True


# ============================================================
# DISCOVERY
# ============================================================
async def discover_timers(gateway):
    """Prova a scoprire i temporizzatori esistenti con una richiesta di lista."""
    _LOGGER.debug("SCHEDULER discovery timer (best-effort)")

    try:
        resp = await gateway.tx_command(
            {"cmd_name": "timers_list_req"}, resp_command=None
        )
    except Exception as err:
        _LOGGER.debug("SCHEDULER discovery fallita (non bloccante): %s", err)
        return []

    if not resp or "array" not in resp:
        _LOGGER.debug(
            "SCHEDULER: nessuna lista timer disponibile, verranno scoperti passivamente"
        )
        return []

    timers = []
    for item in resp.get("array", []):
        if "id" not in item:
            continue
        timer = _TIMERS.get(item["id"])
        if timer:
            timer.update(item)
        else:
            timer = DomoTimer(gateway, item)
        timers.append(timer)

    _LOGGER.info("SCHEDULER discovered %d timer(s)", len(timers))
    return timers


def get_all_timers() -> List["DomoTimer"]:
    return list(_TIMERS.values())


def get_timer(timer_id: int) -> Optional["DomoTimer"]:
    return _TIMERS.get(timer_id)


# ============================================================
# HANDLER BUS
# ============================================================
def handle_timer_status_update(gateway, device_info: Dict[str, Any]) -> bool:
    """Punto unico di ingresso per i pacchetti 'timer_info_ind' dal gateway."""
    cmd = device_info.get("cmd_name")
    if cmd != "timer_info_ind":
        return False

    timer_id = device_info.get("id")
    if timer_id is None:
        return False

    timer = _TIMERS.get(timer_id)
    is_new = timer is None

    if is_new:
        timer = DomoTimer(gateway, device_info)
    else:
        timer.update(device_info)

    if gateway and gateway.hass:
        async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("text"), timer)
        async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("switch"), timer)
        async_dispatcher_send(gateway.hass, SIGNAL_UPDATE_ENTITY)

    _LOGGER.debug(
        "SCHEDULER timer_info_ind | id=%s name=%s enabled=%s days=%s new=%s",
        timer_id, timer.name, timer.enabled, timer.days, is_new,
    )
    return True


# ============================================================
# FUNZIONI DI COMANDO
# ============================================================
async def async_set_timer_enabled(timer_id: int, value: int, gateway) -> None:
    """Abilita/disabilita un timer."""
    await gateway.tx_command(
        {"cmd_name": "timers_enable_req", "id": timer_id, "value": value},
        resp_command=None,
    )


async def async_set_timer_day(timer_id: int, day_index: int, value: int, gateway) -> None:
    """Abilita/disabilita un singolo giorno per un timer."""
    await gateway.tx_command(
        {
            "cmd_name": "timers_enable_day_req",
            "id": timer_id,
            "day": day_index,
            "value": value,
        },
        resp_command=None,
    )


async def async_set_timer_timetable(timer_id: int, timetable: List[dict], gateway) -> None:
    """Imposta la tabella oraria completa di un timer."""
    await gateway.tx_command(
        {"cmd_name": "timers_set_req", "id": timer_id, "timetable": timetable},
        resp_command=None,
    )
