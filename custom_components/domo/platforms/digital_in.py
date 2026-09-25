"""
platforms/digital_in.py

Entities fed by this file:
- domo/binary_sensor.py : consumes DomoDigitalIn, discover_digital_ins,
  refresh_all_digital_ins, get_all_digital_ins, handle_digital_in_status_update

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

from ..const import SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== CONSTANTS =====
# ============================================================

BINARY_SENSOR_STATE_OFF = 0
BINARY_SENSOR_STATE_ON = 1

_DIGITAL_INS: dict[int, DomoDigitalIn] = {}


# ============================================================
# ===== DIGITAL INPUT ENTITY =====
# ============================================================

class DomoDigitalIn:
    """ETI Domo digital input."""

    def __init__(self, gateway, digital_in_data: dict[str, Any]):
        self._gateway = gateway
        self._act_id = digital_in_data["act_id"]
        self._name = digital_in_data.get("name", f"Digital {self._act_id}")
        self._state = digital_in_data.get("status", 1)

        _DIGITAL_INS[self._act_id] = self

        _LOGGER.debug("DIGITAL_IN created: %s (ID: %d) - state: %s",
                      self._name, self._act_id, self._state)

    @property
    def act_id(self) -> int:
        return self._act_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"binary_sensor.domo_{self._act_id}"

    @property
    def is_on(self) -> bool:
        return self._state == BINARY_SENSOR_STATE_OFF

    def update_state(self, data: dict[str, Any]) -> bool:
        if data.get("act_id") != self._act_id:
            return False
        if "status" in data:
            self._state = data["status"]
        return True


# ============================================================
# ===== DISCOVERY =====
# ============================================================

async def discover_digital_ins(gateway):
    """Discover all available digital inputs."""
    _LOGGER.debug("Discovering digital inputs")

    try:
        resp = await gateway.tx_command({
            "cmd_name": "digitalin_list_req",
            "topologic_scope": "plant"
        }, resp_command="digitalin_list_resp")

        if not resp:
            _LOGGER.error("No response from gateway")
            return []

        digital_ins = []
        for item in resp.get("array", []):
            if item.get("leaf", True):
                digital_in = DomoDigitalIn(gateway, item)
                digital_ins.append(digital_in)

        _LOGGER.debug("Discovered %d digital inputs", len(digital_ins))
        return digital_ins

    except Exception as err:
        _LOGGER.error("Digital inputs discovery failed: %s", err)
        return []


# ============================================================
# ===== REFRESH =====
# ============================================================

async def refresh_all_digital_ins(gateway):
    """Resync the state of all digital inputs already in cache."""
    _LOGGER.debug("Refreshing digital inputs state")

    try:
        resp = await gateway.tx_command({
            "cmd_name": "digitalin_list_req",
            "topologic_scope": "plant"
        }, resp_command="digitalin_list_resp")

        if not resp:
            _LOGGER.error("No response from gateway during digital inputs refresh")
            return

        updated = 0
        for item in resp.get("array", []):
            if not item.get("leaf", True):
                continue

            act_id = item.get("act_id")
            digital_in = _DIGITAL_INS.get(act_id)
            if digital_in is None:
                _LOGGER.warning(
                    "Digital input act_id=%s not in cache, skipping refresh", act_id
                )
                continue

            if digital_in.update_state(item):
                updated += 1
                if gateway and gateway.hass:
                    async_dispatcher_send(
                        gateway.hass,
                        SIGNAL_UPDATE_ENTITY,
                        digital_in.unique_id
                    )

        _LOGGER.info("Digital inputs refresh complete: %d entities updated", updated)

    except Exception as err:
        _LOGGER.error("Digital inputs refresh failed: %s", err)


# ============================================================
# ===== HELPERS =====
# ============================================================

def get_all_digital_ins() -> list[DomoDigitalIn]:
    """Return all digital inputs."""
    return list(_DIGITAL_INS.values())


# ============================================================
# ===== EVENT HANDLERS =====
# ============================================================

def handle_digital_in_status_update(gateway, device_info):
    """Handle status update events."""
    act_id = device_info.get("act_id")
    if not act_id:
        return

    digital_in = _DIGITAL_INS.get(act_id)
    if digital_in:
        digital_in.update_state(device_info)

        _LOGGER.debug("DIGITAL_IN update - act_id: %s, full payload: %s",
                      act_id, device_info)

        if gateway and gateway.hass:
            async_dispatcher_send(
                gateway.hass,
                SIGNAL_UPDATE_ENTITY,
                digital_in.unique_id
            )
