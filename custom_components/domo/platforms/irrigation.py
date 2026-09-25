"""
platforms/irrigation.py

Entities fed by this file:
- domo/number.py  : Seasonal percentage, Work cycle, Max irrigation time
- domo/switch.py  : Sector enable, Weekdays, Manual mode, Sprinklers enable
- domo/time.py    : Start time, End time

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
from typing import Any

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_DISCOVERY_NEW, SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== HELPERS =====
# ============================================================

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

_IRRIGATION_ZONES: dict[int, DomoIrrigationZone] = {}


def _decode_days(days: int) -> list[str]:
    """Decode the 'days' bitmask into active weekday names."""
    return [WEEKDAYS[i] for i in range(7) if days & (1 << i)]


def _encode_day_change(current_days: int, day_index: int, value: int) -> int:
    """Return the 'days' bitmask with a single day enabled or disabled."""
    if value:
        return current_days | (1 << day_index)
    return current_days & ~(1 << day_index)


def _decode_time(data: dict[str, Any] | None) -> dict[str, int] | None:
    """Normalize a gateway {hour,min,sec} object, returning None when unset (-1)."""
    if not data:
        return None
    hour = data.get("hour", -1)
    if hour is None or hour < 0:
        return None
    return {
        "hour": hour,
        "min": max(data.get("min", 0), 0),
        "sec": max(data.get("sec", 0), 0),
    }


# ============================================================
# ===== SPRINKLER =====
# ============================================================

class DomoSprinkler:
    """Single sprinkler belonging to an irrigation zone."""

    def __init__(self, zone: DomoIrrigationZone, data: dict[str, Any]):
        self._zone = zone
        self._act_id = data.get("act_id")
        self._name = data.get("name", f"Irrigatore {self._act_id}")
        self._enabled = bool(data.get("enabled", 0))
        self._status = data.get("status", 0)
        self._active = data.get("active")
        self._duty = data.get("duty")

    @property
    def zone(self) -> DomoIrrigationZone:
        return self._zone

    @property
    def zone_id(self) -> int:
        return self._zone.zone_id

    @property
    def gateway(self):
        return self._zone.gateway

    @property
    def unique_id(self) -> str:
        return f"domo_irrigation_{self.zone_id}_sprinkler_{self._act_id}"

    @property
    def act_id(self) -> int:
        return self._act_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def is_active(self) -> bool:
        """True if this sprinkler is currently delivering water."""
        return self._status == 1

    @property
    def active(self) -> int | None:
        return self._active

    @property
    def duty(self) -> int | None:
        return self._duty

    def update(self, data: dict[str, Any]) -> None:
        if "name" in data:
            self._name = data["name"]
        if "enabled" in data:
            self._enabled = bool(data["enabled"])
        if "status" in data:
            self._status = data["status"]
        if "active" in data:
            self._active = data["active"]
        if "duty" in data:
            self._duty = data["duty"]


# ============================================================
# ===== IRRIGATION ZONE =====
# ============================================================

class DomoIrrigationZone:
    """ETI Domo / CAME Domotic irrigation zone (feature 'irrig')."""

    def __init__(self, gateway, data: dict[str, Any]):
        self._gateway = gateway
        self._id = data["id"]
        self._name = data.get("name", f"Settore irrigazione {self._id}")
        self._enabled = bool(data.get("enabled", 0))
        self._status = data.get("status", 0)
        self._forced = bool(data.get("forced", 0))
        self._days = data.get("days", 0)
        self._perc = data.get("perc", 100)
        self._start = _decode_time(data.get("start"))
        self._end = _decode_time(data.get("end"))

        self._sprinklers: dict[int, DomoSprinkler] = {}
        for spr in data.get("sprinklers", []) or []:
            act_id = spr.get("act_id")
            if act_id is not None:
                self._sprinklers[act_id] = DomoSprinkler(self, spr)

        _IRRIGATION_ZONES[self._id] = self

        _LOGGER.debug(
            "IRRIGATION zone created | id=%s name=%s enabled=%s days=%s perc=%s sprinklers=%s",
            self._id, self._name, self._enabled, self._days, self._perc,
            list(self._sprinklers.keys()),
        )

    @property
    def zone_id(self) -> int:
        return self._id

    @property
    def gateway(self):
        return self._gateway

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"domo_irrigation_{self._id}"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def is_watering(self) -> bool:
        """True if the zone is currently watering."""
        return self._status == 1

    @property
    def forced(self) -> bool:
        """True if a manual forced irrigation is running."""
        return self._forced

    @property
    def days(self) -> int:
        return self._days

    @property
    def active_weekdays(self) -> list[str]:
        return _decode_days(self._days)

    @property
    def perc(self) -> int:
        """Duration percentage relative to nominal time (100 = nominal)."""
        return self._perc

    @property
    def start(self) -> dict[str, int] | None:
        """Scheduled start time, or None if not set."""
        return self._start

    @property
    def end(self) -> dict[str, int] | None:
        """Scheduled end time computed by the gateway, read-only."""
        return self._end

    @property
    def sprinklers(self) -> list[DomoSprinkler]:
        return list(self._sprinklers.values())

    def get_sprinkler(self, act_id: int) -> DomoSprinkler | None:
        return self._sprinklers.get(act_id)

    def update(self, data: dict[str, Any]) -> bool:
        """Update the zone from bus data (irrigation_detail_ind); return True if changed."""
        if data.get("id") != self._id:
            return False

        changed = False
        field_map = {
            "name": "_name",
            "enabled": "_enabled",
            "status": "_status",
            "forced": "_forced",
            "days": "_days",
            "perc": "_perc",
        }
        for key, attr in field_map.items():
            if key not in data:
                continue
            value = data[key]
            if key in ("enabled", "forced"):
                value = bool(value)
            if getattr(self, attr) != value:
                setattr(self, attr, value)
                changed = True

        if "start" in data:
            new_start = _decode_time(data["start"])
            if new_start != self._start:
                self._start = new_start
                changed = True

        if "end" in data:
            new_end = _decode_time(data["end"]) if self._start is not None else None
            if new_end != self._end:
                self._end = new_end
                changed = True

        if "sprinklers" in data:
            for spr in data["sprinklers"] or []:
                act_id = spr.get("act_id")
                if act_id is None:
                    continue
                existing = self._sprinklers.get(act_id)
                if existing:
                    existing.update(spr)
                    if self._gateway and self._gateway.hass:
                        async_dispatcher_send(
                            self._gateway.hass, SIGNAL_UPDATE_ENTITY, existing.unique_id
                        )
                else:
                    new_sprinkler = DomoSprinkler(self, spr)
                    self._sprinklers[act_id] = new_sprinkler
                    if self._gateway and self._gateway.hass:
                        async_dispatcher_send(
                            self._gateway.hass, SIGNAL_DISCOVERY_NEW.format("number"), new_sprinkler
                        )
                        async_dispatcher_send(
                            self._gateway.hass, SIGNAL_DISCOVERY_NEW.format("binary_sensor"), new_sprinkler
                        )
            changed = True

        if changed:
            _LOGGER.debug(
                "IRRIGATION zone updated | id=%s enabled=%s status=%s forced=%s perc=%s",
                self._id, self._enabled, self._status, self._forced, self._perc,
            )
        return changed


# ============================================================
# ===== DISCOVERY =====
# ============================================================

async def discover_irrigation_zones(gateway):
    """Discover the available irrigation zones (feature 'irrig')."""
    _LOGGER.info("IRRIGATION starting discovery")

    try:
        resp = await gateway.tx_command(
            {"cmd_name": "irrigation_list_req", "detailed": 1},
            resp_command="irrigation_list_resp",
        )
    except Exception as err:
        _LOGGER.error("IRRIGATION discovery failed: %s", err)
        return []

    if not resp or "array" not in resp:
        _LOGGER.debug("IRRIGATION: no zones found")
        return []

    zones = []
    for item in resp.get("array", []):
        if "id" not in item:
            continue
        zone = _IRRIGATION_ZONES.get(item["id"])
        if zone:
            zone.update(item)
        else:
            zone = DomoIrrigationZone(gateway, item)
        zones.append(zone)

    _LOGGER.info("IRRIGATION discovered %d zone(s)", len(zones))
    return zones


async def refresh_all_irrigation(gateway) -> None:
    """Resynchronize all irrigation zones after the gateway comes back online."""
    _LOGGER.info("IRRIGATION starting refresh (gateway reconnect)")

    try:
        resp = await gateway.tx_command(
            {"cmd_name": "irrigation_list_req", "detailed": 1},
            resp_command="irrigation_list_resp",
        )
    except Exception as err:
        _LOGGER.error("IRRIGATION refresh failed: %s", err)
        return

    if not resp or "array" not in resp:
        _LOGGER.debug("IRRIGATION refresh: no data received")
        return

    updated = 0
    for item in resp.get("array", []):
        zone_id = item.get("id")
        if zone_id is None:
            continue
        zone = _IRRIGATION_ZONES.get(zone_id)
        if zone is None:
            _LOGGER.warning("IRRIGATION refresh: unknown zone id=%s, ignored", zone_id)
            continue
        if zone.update(item) and gateway and gateway.hass:
            async_dispatcher_send(gateway.hass, SIGNAL_UPDATE_ENTITY, zone.unique_id)
            updated += 1

    _LOGGER.info("IRRIGATION refresh completed | %d zone(s) updated", updated)


def get_all_irrigation_zones() -> list[DomoIrrigationZone]:
    return list(_IRRIGATION_ZONES.values())


def get_all_sprinklers() -> list[DomoSprinkler]:
    """Return all sprinklers of all zones, for initial entity setup."""
    result: list[DomoSprinkler] = []
    for zone in _IRRIGATION_ZONES.values():
        result.extend(zone.sprinklers)
    return result


def get_irrigation_zone(zone_id: int) -> DomoIrrigationZone | None:
    return _IRRIGATION_ZONES.get(zone_id)


# ============================================================
# ===== BUS HANDLER =====
# ============================================================

def handle_irrigation_status_update(gateway, device_info: dict[str, Any]) -> bool:
    """Single entry point for 'irrigation_detail_ind' packets from the gateway."""
    cmd = device_info.get("cmd_name")
    if cmd != "irrigation_detail_ind":
        return False

    zone_id = device_info.get("id")
    if zone_id is None:
        return False

    zone = _IRRIGATION_ZONES.get(zone_id)
    is_new = zone is None

    if is_new:
        zone = DomoIrrigationZone(gateway, device_info)
    else:
        zone.update(device_info)

    if gateway and gateway.hass:
        if is_new:
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("irrigation_switch"), zone)
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("time"), zone)
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("irrigation_number"), zone)
            for sprinkler in zone.sprinklers:
                async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("number"), sprinkler)
                async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("binary_sensor"), sprinkler)
        async_dispatcher_send(gateway.hass, SIGNAL_UPDATE_ENTITY, zone.unique_id)

    _LOGGER.debug(
        "IRRIGATION irrigation_detail_ind | id=%s enabled=%s status=%s forced=%s new=%s",
        zone_id, zone.enabled, zone.is_watering, zone.forced, is_new,
    )
    return True


# ============================================================
# ===== COMMAND FUNCTIONS =====
# ============================================================

async def async_set_irrigation_enabled(zone_id: int, value: int, gateway) -> None:
    """Enable or disable an irrigation zone."""
    await gateway.tx_command(
        {"cmd_name": "irrigation_set_req", "id": zone_id, "enabled": value},
        resp_command=None,
    )


async def async_set_irrigation_perc(zone_id: int, perc: int, gateway) -> None:
    """Set the irrigation duration percentage (100 = nominal duration)."""
    await gateway.tx_command(
        {"cmd_name": "irrigation_set_req", "id": zone_id, "perc": perc},
        resp_command=None,
    )


async def async_set_irrigation_days(zone_id: int, days: int, gateway) -> None:
    """Set the full active-days bitmask (mon=bit0 ... sun=bit6)."""
    await gateway.tx_command(
        {"cmd_name": "irrigation_set_req", "id": zone_id, "days": days},
        resp_command=None,
    )


async def async_set_irrigation_day(zone_id: int, day_index: int, value: int, gateway) -> None:
    """Enable or disable a single weekday for a zone."""
    zone = get_irrigation_zone(zone_id)
    if zone is None:
        _LOGGER.warning("IRRIGATION: set_day on unknown zone id=%s", zone_id)
        return
    new_days = _encode_day_change(zone.days, day_index, value)
    await async_set_irrigation_days(zone_id, new_days, gateway)


async def async_set_irrigation_start(
    zone_id: int, hour: int, minute: int, second: int, gateway
) -> None:
    """Set the scheduled start time of the zone."""
    await gateway.tx_command(
        {
            "cmd_name": "irrigation_set_req",
            "id": zone_id,
            "start": {"hour": hour, "min": minute, "sec": second},
        },
        resp_command=None,
    )


async def async_set_sprinkler_enabled(zone_id: int, act_id: int, value: int, gateway) -> None:
    """Enable or disable a single sprinkler of a zone."""
    await gateway.tx_command(
        {
            "cmd_name": "irrigation_set_req",
            "id": zone_id,
            "sprinklers": [{"act_id": act_id, "enabled": value}],
        },
        resp_command=None,
    )


async def async_set_sprinkler_active(zone_id: int, act_id: int, seconds: int, gateway) -> None:
    """Set the maximum irrigation time (seconds) of a single sprinkler."""
    await gateway.tx_command(
        {
            "cmd_name": "irrigation_set_req",
            "id": zone_id,
            "sprinklers": [{"act_id": act_id, "active": seconds}],
        },
        resp_command=None,
    )


async def async_set_sprinkler_duty(zone_id: int, act_id: int, duty: int, gateway) -> None:
    """Set the duty cycle (%) of a single sprinkler."""
    await gateway.tx_command(
        {
            "cmd_name": "irrigation_set_req",
            "id": zone_id,
            "sprinklers": [{"act_id": act_id, "duty": duty}],
        },
        resp_command=None,
    )


async def async_force_irrigation(zone_id: int, gateway) -> None:
    """Force manual start/stop of the irrigation."""
    await gateway.tx_command(
        {"cmd_name": "irrigation_force_req", "id": zone_id},
        resp_command=None,
    )
