"""
platforms/loadsctrl.py

Entities fed by this file:
- domo/sensor.py : Instantaneous power reading of the power source (Generale)
- domo/number.py : Full-scale power (max_power), hysteresis
- domo/text.py   : Daily energy profile (7 days x 24 levels)
- domo/select.py : Day being edited (the "copy profile to..." feature is handled
                    entirely in domo/select.py's UI layer, as with thermostats -
                    no dedicated bus commands required)
- domo/switch.py : Load control enable/disable (relay), dynamic icon based on
                    connection status handled by domo/switch.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues

status: passed
"""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_DISCOVERY_NEW, SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)


class LoadCtrlProfileError(ValueError):
    """User input not applicable to the energy profile (overlapping or ambiguous slots)."""


# ============================================================
# ===== CONSTANTS =====
# ============================================================

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

LOADCTRL_DAY_TO_INDEX = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
LOADCTRL_INDEX_TO_DAY = {v: k for k, v in LOADCTRL_DAY_TO_INDEX.items()}
_WEEKDAY_ORDER = list(LOADCTRL_DAY_TO_INDEX)

LOADCTRL_PROFILE_HOURS = 24
LOADCTRL_LEVELS = 5
LOADCTRL_DEFAULT_LEVEL = 5

_LOADCTRL_METERS: dict[int, DomoLoadCtrlMeter] = {}
_LOADCTRL_RELAYS: dict[int, DomoLoadCtrlRelay] = {}


def loadsctrl_level_to_watts(level: int, max_power: int) -> int:
    """Convert a raw level (0-5) to Watts, proportional to the full-scale value (max_power)."""
    level = max(0, min(LOADCTRL_LEVELS, level))
    return round(max_power * level / LOADCTRL_LEVELS)


def loadsctrl_validate_profile_string(value: str) -> bool:
    """Check that a profile string is valid: 24 characters, digits 0-5."""
    if not isinstance(value, str) or len(value) != LOADCTRL_PROFILE_HOURS:
        return False
    return all(ch in "012345" for ch in value)


# ============================================================
# ===== PROFILE CODEC =====
# ============================================================

def _watts_to_level(watts: int, max_power: int) -> str:
    """Convert a Watt value to the nearest raw level '1'-'5' for the current full-scale value."""
    if max_power <= 0:
        raise LoadCtrlProfileError(f"Fondo scala non valido: {max_power}W")

    step = max_power / LOADCTRL_LEVELS
    level = round(watts / step)
    level = max(1, min(LOADCTRL_LEVELS, level))
    return str(level)


def _parse_hour_range(rng: str) -> tuple[int, int]:
    """Convert 'N' or 'N-M' (hours 1-24, inclusive) to a 0-indexed half-open (start, end) slot."""
    rng = rng.strip()
    if "-" in rng:
        start_str, end_str = rng.split("-")
        start_hour, end_hour = int(start_str.strip()), int(end_str.strip())
    else:
        start_hour = end_hour = int(rng)

    if not (1 <= start_hour <= end_hour <= LOADCTRL_PROFILE_HOURS):
        raise LoadCtrlProfileError(f"Slot orario non valido (atteso 1-{LOADCTRL_PROFILE_HOURS}): {rng}")

    return start_hour - 1, end_hour


def _parse_schedule_blocks(schedule_str: str, max_power: int) -> list[tuple[int, int, str]]:
    """Parse 'N-M=Watt,...' into a list of (start_slot, end_slot, raw char 0-4)."""
    blocks: list[tuple[int, int, str]] = []
    for raw_block in schedule_str.split(","):
        raw_block = raw_block.strip()
        if not raw_block:
            continue
        rng, watts_str = raw_block.split("=")
        try:
            watts = int(watts_str.strip())
        except ValueError as err:
            raise LoadCtrlProfileError(f"Valore non numerico: {watts_str.strip()}") from err
        char = _watts_to_level(watts, max_power)
        start_slot, end_slot = _parse_hour_range(rng)
        blocks.append((start_slot, end_slot, char))
    if not blocks:
        raise LoadCtrlProfileError("Profilo vuoto: nessun blocco specificato")
    return blocks


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    """Number of hours shared between two intervals [a_start,a_end) and [b_start,b_end)."""
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def _decode_profile_to_blocks(profile_data: str) -> list[tuple[int, int, str]]:
    """Decode a profile string (24 characters) into contiguous blocks (start_slot, end_slot, char)."""
    blocks: list[tuple[int, int, str]] = []
    if not profile_data:
        return blocks
    current_char, start = profile_data[0], 0
    for i in range(1, len(profile_data)):
        if profile_data[i] != current_char:
            blocks.append((start, i, current_char))
            current_char, start = profile_data[i], i
    blocks.append((start, len(profile_data), current_char))
    return blocks


def encode_loadsctrl_profile(schedule_str: str, max_power: int, base_profile_data: str | None = None) -> str:
    """Convert 'N-M=Watt,...' into the 24-character string for loadsctrl_meter_set_req."""
    user_blocks = _parse_schedule_blocks(schedule_str, max_power)

    if base_profile_data and len(base_profile_data) == LOADCTRL_PROFILE_HOURS:
        base_blocks = _decode_profile_to_blocks(base_profile_data)
        slots = list(base_profile_data)
    else:
        base_blocks = []
        slots = [str(LOADCTRL_DEFAULT_LEVEL)] * LOADCTRL_PROFILE_HOURS

    real_blocks = [b for b in user_blocks if b not in base_blocks]
    if not real_blocks:
        return base_profile_data if base_profile_data else "".join(slots)

    sorted_blocks = sorted(real_blocks, key=lambda b: b[0])
    for prev_block, curr_block in zip(sorted_blocks, sorted_blocks[1:]):
        if _overlap(prev_block[0], prev_block[1], curr_block[0], curr_block[1]) > 0:
            raise LoadCtrlProfileError("Slot orari sovrapposti. Input annullato.")

    for start, end, char in sorted_blocks:
        for i in range(start, end):
            slots[i] = char

    return "".join(slots)


def decode_loadsctrl_profile_to_schedule_str(profile_data: str, max_power: int) -> str:
    """Decode the profile string (24 characters, raw digit 0-4) into 'N-M=Watt,...' format."""
    if not profile_data:
        return ""
    blocks = []
    current_char, start = None, 0
    for i, ch in enumerate(profile_data):
        if current_char is None:
            current_char, start = ch, i
            continue
        if ch != current_char:
            blocks.append(_format_block(start, i, current_char, max_power))
            current_char, start = ch, i
    if current_char is not None:
        blocks.append(_format_block(start, len(profile_data), current_char, max_power))
    return ",".join(blocks)


def _format_block(start_slot: int, end_slot: int, char: str, max_power: int) -> str:
    """Format a block (start_slot, end_slot, raw char) as 'N=Watt' or 'N-M=Watt'."""
    start_hour, end_hour = start_slot + 1, end_slot
    watts = loadsctrl_level_to_watts(int(char), max_power)
    if start_hour == end_hour:
        return f"{start_hour}={watts}"
    return f"{start_hour}-{end_hour}={watts}"


class DomoLoadCtrlRelay:
    """Single load managed by the load control feature (item of loadsctrl_relay_list_resp 'array[]')."""

    def __init__(self, meter: DomoLoadCtrlMeter, data: dict[str, Any]):
        self._meter = meter
        self._id = data["id"]
        self._name = data.get("name", f"Carico {self._id}")
        self._priority = data.get("priority", 0)
        self._enabled = bool(data.get("enabled", 0))
        self._act_id = data.get("act_id")
        self._detached = bool(data.get("detached", 0))
        self._status = data.get("status", 0)
        self._loadtype = data.get("loadtype")

    @property
    def meter(self) -> DomoLoadCtrlMeter:
        return self._meter

    @property
    def meter_id(self) -> int:
        return self._meter.meter_id

    @property
    def gateway(self):
        return self._meter.gateway

    @property
    def relay_id(self) -> int:
        return self._id

    @property
    def unique_id(self) -> str:
        return f"domo_loadsctrl_relay_{self._id}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def enabled(self) -> bool:
        """True if the load is currently enabled (switch ON)."""
        return self._enabled

    @property
    def act_id(self) -> int | None:
        return self._act_id

    @property
    def is_detached(self) -> bool:
        """True if the load manager has temporarily excluded the load (overload event)."""
        return self._detached

    @property
    def status(self) -> int:
        return self._status

    @property
    def loadtype(self) -> int | None:
        return self._loadtype

    def update(self, data: dict[str, Any]) -> None:
        if "name" in data:
            self._name = data["name"]
        if "priority" in data:
            self._priority = data["priority"]
        if "enabled" in data:
            self._enabled = bool(data["enabled"])
        if "act_id" in data:
            self._act_id = data["act_id"]
        if "detached" in data:
            self._detached = bool(data["detached"])
        if "status" in data:
            self._status = data["status"]
        if "loadtype" in data:
            self._loadtype = data["loadtype"]


class DomoLoadCtrlMeter:
    """Load control manager (ETI Domo / CAME Domotic 'loadsctrl' feature), e.g. 'Generale'."""

    def __init__(self, gateway, data: dict[str, Any]):
        self._gateway = gateway
        self._id = data["id"]
        self._name = data.get("name", f"Controllo carichi {self._id}")
        self._hysteresis = data.get("hysteresis", 0)
        self._max_power = data.get("max_power", 0)
        self._profile_data = list(data.get("profile_data") or [])
        self._meter_id = data.get("meter_id")
        self._power = data.get("power", 0)

        self._relays: dict[int, DomoLoadCtrlRelay] = {}

        self._selected_profile_day: str = _WEEKDAY_ORDER[datetime.now().weekday()]
        self._profile_draft_by_day: dict[str, str] = {}
        self._apply_profile_data_array(self._profile_data)

        _LOADCTRL_METERS[self._id] = self

        _LOGGER.debug(
            "LOADSCTRL meter created | id=%s name=%s max_power=%s hysteresis=%s meter_id=%s power=%s",
            self._id, self._name, self._max_power, self._hysteresis, self._meter_id, self._power,
        )

    # --- Properties ---

    @property
    def meter_id(self) -> int:
        return self._id

    @property
    def gateway(self):
        return self._gateway

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"domo_loadsctrl_{self._id}"

    @property
    def hysteresis(self) -> int:
        """Hysteresis in Watts."""
        return self._hysteresis

    @property
    def max_power(self) -> int:
        """Full-scale value in Watts."""
        return self._max_power

    @property
    def profile_data(self) -> list[str]:
        return list(self._profile_data)

    @property
    def energy_meter_id(self) -> int | None:
        """Id of the linked energy meter ('energy' feature), read-only."""
        return self._meter_id

    @property
    def power(self) -> int:
        """Instantaneous power in Watts of the power source."""
        return self._power

    @property
    def relays(self) -> list[DomoLoadCtrlRelay]:
        """Connected loads, ordered by priority."""
        return sorted(self._relays.values(), key=lambda relay: relay.priority)

    def get_relay(self, relay_id: int) -> DomoLoadCtrlRelay | None:
        return self._relays.get(relay_id)

    def get_profile_day(self, day_index: int) -> str:
        """Return the profile string (24 levels) for the given day (0=mon ... 6=sun)."""
        if 0 <= day_index < len(self._profile_data):
            return self._profile_data[day_index]
        return str(LOADCTRL_DEFAULT_LEVEL) * LOADCTRL_PROFILE_HOURS

    def get_day_level(self, day_index: int, hour: int) -> int:
        """Return the level (1-5) set for a specific hour of a given day."""
        day = self.get_profile_day(day_index)
        if 0 <= hour < len(day):
            return int(day[hour])
        return LOADCTRL_DEFAULT_LEVEL

    @property
    def selected_profile_day(self) -> str:
        """Day (stable English key) currently being edited for the energy profile."""
        return self._selected_profile_day

    def set_selected_profile_day(self, day: str) -> None:
        if day not in LOADCTRL_DAY_TO_INDEX:
            raise ValueError(f"Giorno non valido: {day}")
        self._selected_profile_day = day

    @property
    def profile_draft(self) -> str:
        """Human-readable draft ('HH:MM-HH:MM=N,...') of the currently selected day."""
        return self._profile_draft_by_day.get(self._selected_profile_day, "")

    def _apply_profile_data_array(self, profile_data_array: list[str]) -> None:
        """Rebuild the cache of human-readable drafts for all days (0-6: Mon...Sun)."""
        for day_index, raw in enumerate(profile_data_array):
            day_name = LOADCTRL_INDEX_TO_DAY.get(day_index)
            if day_name is None:
                continue
            self._profile_draft_by_day[day_name] = decode_loadsctrl_profile_to_schedule_str(raw, self._max_power)

    async def async_set_profile(self, schedule_str: str) -> None:
        """Write the energy profile (human-readable format) of the currently selected day."""
        day_index = LOADCTRL_DAY_TO_INDEX[self._selected_profile_day]
        base_profile_data = self.get_profile_day(day_index)
        profile_data = encode_loadsctrl_profile(schedule_str, self._max_power, base_profile_data=base_profile_data)

        _LOGGER.debug(
            "LOADSCTRL meter id=%s: profile day=%s base=%r input=%r -> profile_data=%r",
            self._id, self._selected_profile_day, base_profile_data, schedule_str, profile_data,
        )

        await async_set_loadsctrl_profile_day(self._id, day_index, profile_data, self._gateway)

    def update_profile_day_local(self, day_index: int, profile_string: str) -> None:
        """Optimistically update the local cache."""
        while len(self._profile_data) < 7:
            self._profile_data.append(str(LOADCTRL_DEFAULT_LEVEL) * LOADCTRL_PROFILE_HOURS)
        self._profile_data[day_index] = profile_string
        day_name = LOADCTRL_INDEX_TO_DAY.get(day_index)
        if day_name:
            self._profile_draft_by_day[day_name] = decode_loadsctrl_profile_to_schedule_str(profile_string, self._max_power)

    # --- Update ---

    def update(self, data: dict[str, Any]) -> bool:
        """Update the load manager with new data received from the bus (loadsctrl_meter_ind)."""
        if data.get("id") != self._id:
            return False

        changed = False
        field_map = {
            "name": "_name",
            "hysteresis": "_hysteresis",
            "max_power": "_max_power",
            "meter_id": "_meter_id",
            "power": "_power",
        }
        max_power_changed = False
        profile_changed = False
        for key, attr in field_map.items():
            if key not in data:
                continue
            if getattr(self, attr) != data[key]:
                setattr(self, attr, data[key])
                changed = True
                if key == "max_power":
                    max_power_changed = True

        if "profile_data" in data:
            new_profile = list(data["profile_data"] or [])
            if new_profile != self._profile_data:
                self._profile_data = new_profile
                changed = True
                profile_changed = True

        if profile_changed or max_power_changed:
            self._apply_profile_data_array(self._profile_data)

        if changed:
            _LOGGER.debug(
                "LOADSCTRL meter updated | id=%s max_power=%s hysteresis=%s power=%s",
                self._id, self._max_power, self._hysteresis, self._power,
            )
        return True

    def add_or_update_relay(self, data: dict[str, Any]) -> tuple[DomoLoadCtrlRelay, bool]:
        """Create or update a load connected to this manager. Returns (relay, is_new)."""
        relay_id = data["id"]
        relay = self._relays.get(relay_id)
        is_new = relay is None
        if is_new:
            relay = DomoLoadCtrlRelay(self, data)
            self._relays[relay_id] = relay
            _LOADCTRL_RELAYS[relay_id] = relay
        else:
            relay.update(data)
        return relay, is_new


# ============================================================
# ===== DISCOVERY =====
# ============================================================

async def discover_loadsctrl(gateway):
    """Discover load control managers and their connected loads ('loadsctrl' feature)."""
    _LOGGER.info("LOADSCTRL starting discovery")

    try:
        resp = await gateway.tx_command(
            {"cmd_name": "loadsctrl_meter_list_req"},
            resp_command="loadsctrl_meter_list_resp",
        )
    except Exception as err:
        _LOGGER.error("LOADSCTRL meter discovery failed: %s", err)
        return []

    if not resp or "array" not in resp:
        _LOGGER.debug("LOADSCTRL: no load managers found")
        return []

    meters = []
    for item in resp.get("array", []):
        if "id" not in item:
            continue
        meter = _LOADCTRL_METERS.get(item["id"])
        if meter:
            meter.update(item)
        else:
            meter = DomoLoadCtrlMeter(gateway, item)
        meters.append(meter)
        await _discover_loadsctrl_relays(gateway, meter)

    _LOGGER.info("LOADSCTRL discovered %d load manager(s)", len(meters))
    return meters


async def _discover_loadsctrl_relays(gateway, meter: DomoLoadCtrlMeter) -> None:
    """Discover the loads (relays) connected to a load control manager."""
    try:
        resp = await gateway.tx_command(
            {"cmd_name": "loadsctrl_relay_list_req", "id": meter.meter_id},
            resp_command="loadsctrl_relay_list_resp",
        )
    except Exception as err:
        _LOGGER.error("LOADSCTRL relay discovery failed for meter id=%s: %s", meter.meter_id, err)
        return

    if not resp or "array" not in resp:
        _LOGGER.debug("LOADSCTRL: no loads found for meter id=%s", meter.meter_id)
        return

    for item in resp.get("array", []):
        if "id" not in item:
            continue
        meter.add_or_update_relay(item)

    _LOGGER.debug("LOADSCTRL meter id=%s: %d load(s)", meter.meter_id, len(meter.relays))


async def refresh_all_loadsctrl(gateway) -> None:
    """Reread the full state of load control managers from the gateway."""
    try:
        resp = await gateway.tx_command(
            {"cmd_name": "loadsctrl_meter_list_req"},
            resp_command="loadsctrl_meter_list_resp",
        )
    except Exception as err:
        _LOGGER.error("LOADSCTRL refresh: meter list failed: %s", err)
        return

    if not resp or "array" not in resp:
        _LOGGER.debug("LOADSCTRL refresh: no load managers found")
        return

    updated = 0
    for item in resp.get("array", []):
        meter_id = item.get("id")
        if meter_id is None:
            continue
        meter = _LOADCTRL_METERS.get(meter_id)
        if meter is None:
            _LOGGER.warning("LOADSCTRL refresh: manager id=%s not in cache, ignored", meter_id)
            continue
        meter.update(item)
        updated += 1
        if gateway and gateway.hass:
            async_dispatcher_send(gateway.hass, SIGNAL_UPDATE_ENTITY, meter.unique_id)
        await _refresh_loadsctrl_relays(gateway, meter)

    _LOGGER.info("LOADSCTRL refresh: %d manager(s) updated", updated)


async def _refresh_loadsctrl_relays(gateway, meter: DomoLoadCtrlMeter) -> None:
    """Reread the loads connected to a manager and update the ones already in cache in place."""
    try:
        resp = await gateway.tx_command(
            {"cmd_name": "loadsctrl_relay_list_req", "id": meter.meter_id},
            resp_command="loadsctrl_relay_list_resp",
        )
    except Exception as err:
        _LOGGER.error("LOADSCTRL refresh: relay list failed for meter id=%s: %s", meter.meter_id, err)
        return

    if not resp or "array" not in resp:
        return

    for item in resp.get("array", []):
        relay_id = item.get("id")
        if relay_id is None:
            continue
        relay = meter.get_relay(relay_id)
        if relay is None:
            _LOGGER.warning("LOADSCTRL refresh: load id=%s not in cache, ignored", relay_id)
            continue
        relay.update(item)
        if gateway and gateway.hass:
            async_dispatcher_send(gateway.hass, SIGNAL_UPDATE_ENTITY, relay.unique_id)


def get_all_loadsctrl_meters() -> list[DomoLoadCtrlMeter]:
    return list(_LOADCTRL_METERS.values())


def get_all_loadsctrl_relays() -> list[DomoLoadCtrlRelay]:
    """Return all loads from all managers, for initial entity setup."""
    result: list[DomoLoadCtrlRelay] = []
    for meter in _LOADCTRL_METERS.values():
        result.extend(meter.relays)
    return result


def get_loadsctrl_meter(meter_id: int) -> DomoLoadCtrlMeter | None:
    return _LOADCTRL_METERS.get(meter_id)


def get_loadsctrl_relay(relay_id: int) -> DomoLoadCtrlRelay | None:
    return _LOADCTRL_RELAYS.get(relay_id)


# ============================================================
# ===== BUS HANDLERS =====
# ============================================================

def handle_loadsctrl_status_update(gateway, device_info: dict[str, Any]) -> bool:
    """Single entry point for 'loadsctrl_meter_ind' / 'loadsctrl_relay_ind' packets from the gateway."""
    cmd = device_info.get("cmd_name")
    if cmd not in ("loadsctrl_meter_ind", "loadsctrl_relay_ind"):
        return False

    if cmd == "loadsctrl_meter_ind":
        return _handle_meter_ind(gateway, device_info)
    return _handle_relay_ind(gateway, device_info)


def _handle_meter_ind(gateway, device_info: dict[str, Any]) -> bool:
    meter_id = device_info.get("id")
    if meter_id is None:
        return False

    meter = _LOADCTRL_METERS.get(meter_id)
    is_new = meter is None

    if is_new:
        meter = DomoLoadCtrlMeter(gateway, device_info)
    else:
        meter.update(device_info)

    if gateway and gateway.hass:
        if is_new:
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_sensor"), meter)
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_number"), meter)
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_text"), meter)
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_select"), meter)
        async_dispatcher_send(gateway.hass, SIGNAL_UPDATE_ENTITY, meter.unique_id)

    _LOGGER.debug(
        "LOADSCTRL loadsctrl_meter_ind | id=%s max_power=%s hysteresis=%s power=%s new=%s",
        meter_id, meter.max_power, meter.hysteresis, meter.power, is_new,
    )
    return True


def _handle_relay_ind(gateway, device_info: dict[str, Any]) -> bool:
    relay_id = device_info.get("id")
    if relay_id is None:
        return False

    relay = _LOADCTRL_RELAYS.get(relay_id)

    if relay is not None:
        relay.update(device_info)
        is_new = False
        meter = relay.meter
    else:
        if len(_LOADCTRL_METERS) != 1:
            _LOGGER.warning(
                "LOADSCTRL: unknown load id=%s with %d active managers, cannot associate",
                relay_id, len(_LOADCTRL_METERS),
            )
            return False
        meter = next(iter(_LOADCTRL_METERS.values()))
        relay, is_new = meter.add_or_update_relay(device_info)

    if gateway and gateway.hass:
        if is_new:
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_switch"), relay)
        async_dispatcher_send(gateway.hass, SIGNAL_UPDATE_ENTITY, relay.unique_id)

    _LOGGER.debug(
        "LOADSCTRL loadsctrl_relay_ind | id=%s enabled=%s status=%s detached=%s new=%s",
        relay_id, relay.enabled, relay.status, relay.is_detached, is_new,
    )
    return True


# ============================================================
# ===== COMMAND FUNCTIONS =====
# ============================================================

async def _async_send_meter_set(meter: DomoLoadCtrlMeter, gateway, **overrides: Any) -> None:
    """Send loadsctrl_meter_set_req with the full payload (hysteresis, max_power, profile_data),
    applying only the requested changes."""
    payload = {
        "cmd_name": "loadsctrl_meter_set_req",
        "id": meter.meter_id,
        "hysteresis": meter.hysteresis,
        "max_power": meter.max_power,
        "profile_data": meter.profile_data,
    }
    payload.update(overrides)

    await gateway.tx_command(payload, resp_command=None)


async def async_set_loadsctrl_max_power(meter_id: int, max_power: int, gateway) -> None:
    """Set the full-scale value (max_power, in Watts) of the load manager."""
    meter = get_loadsctrl_meter(meter_id)
    if meter is None:
        _LOGGER.warning("LOADSCTRL: set_max_power on unknown manager id=%s", meter_id)
        return
    await _async_send_meter_set(meter, gateway, max_power=max_power)


async def async_set_loadsctrl_hysteresis(meter_id: int, hysteresis: int, gateway) -> None:
    """Set the hysteresis (in Watts) of the load manager."""
    meter = get_loadsctrl_meter(meter_id)
    if meter is None:
        _LOGGER.warning("LOADSCTRL: set_hysteresis on unknown manager id=%s", meter_id)
        return
    await _async_send_meter_set(meter, gateway, hysteresis=hysteresis)


async def async_set_loadsctrl_profile_day(
    meter_id: int, day_index: int, profile_string: str, gateway
) -> None:
    """Replace the profile (24 levels) of a single day of the week."""
    meter = get_loadsctrl_meter(meter_id)
    if meter is None:
        _LOGGER.warning("LOADSCTRL: set_profile_day on unknown manager id=%s", meter_id)
        return
    if not (0 <= day_index < 7):
        _LOGGER.warning("LOADSCTRL: day_index out of range: %s", day_index)
        return
    if not loadsctrl_validate_profile_string(profile_string):
        _LOGGER.warning("LOADSCTRL: invalid profile (expected 24 characters 1-5): %s", profile_string)
        return

    new_profile = meter.profile_data
    while len(new_profile) < 7:
        new_profile.append(str(LOADCTRL_DEFAULT_LEVEL) * LOADCTRL_PROFILE_HOURS)
    new_profile[day_index] = profile_string

    await _async_send_meter_set(meter, gateway, profile_data=new_profile)

    meter.update_profile_day_local(day_index, profile_string)


async def async_set_loadsctrl_relay_enabled(relay_id: int, value: int, gateway) -> None:
    """Enable/disable control of the load (switch ON/OFF)."""
    relay = get_loadsctrl_relay(relay_id)
    if relay is None:
        _LOGGER.warning("LOADSCTRL: set_relay_enabled on unknown load id=%s", relay_id)
        return
    await gateway.tx_command(
        {
            "cmd_name": "loadsctrl_relay_set_req",
            "id": relay_id,
            "enabled": value,
            "priority": relay.priority,
        },
        resp_command=None,
    )
