"""
platforms/openings.py

Entities fed by this file:
- domo/cover.py : consumes DomoOpening class and helper functions
  (discover_openings, refresh_all_openings, get_all_openings, get_opening,
  handle_opening_status_update) to implement HA cover entities for motorized
  shutters and blinds

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
# ===== STATE CONSTANTS =====
# ============================================================

OPENING_STATE_STOP = 0
OPENING_STATE_OPENING = 1
OPENING_STATE_CLOSING = 2

_OPENINGS: dict[int, DomoOpening] = {}


# ============================================================
# ===== OPENING CLASS =====
# ============================================================

class DomoOpening:
    """Motorized opening (shutter/blind) managed via ETI Domo gateway."""

    def __init__(self, gateway, opening_data: dict[str, Any]):
        """Initialize a motorized opening."""
        self._gateway = gateway
        self._open_act_id = opening_data["open_act_id"]
        self._close_act_id = opening_data["close_act_id"]
        self._name = opening_data.get("name", f"Opening {self._open_act_id}")
        self._state = opening_data.get("status", OPENING_STATE_STOP)
        self._type = opening_data.get("type", 0)

        _OPENINGS[self._open_act_id] = self

        _LOGGER.debug(
            "OPENING created: %s (open_act_id: %d, close_act_id: %d) - state: %s",
            self._name, self._open_act_id, self._close_act_id, self._state
        )

    @property
    def open_act_id(self) -> int:
        return self._open_act_id

    @property
    def close_act_id(self) -> int:
        return self._close_act_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"cover.domo_{self._open_act_id}"

    @property
    def opening_type(self) -> int:
        """Return the opening type: 0=shutter, 1=blind."""
        return self._type

    @property
    def is_opening(self) -> bool:
        """Return True if the opening is currently moving in the opening direction."""
        return self._state == OPENING_STATE_OPENING

    @property
    def is_closing(self) -> bool:
        """Return True if the opening is currently moving in the closing direction."""
        return self._state == OPENING_STATE_CLOSING

    @property
    def is_closed(self) -> bool | None:
        """Return True/False when the motor is moving, None when stopped.

        The gateway only reports motor movement (opening/closing/stop), never
        an actual open/closed position. When the motor is moving it cannot be
        closed; when it is stopped the real position is unknown.
        """
        if self._state == OPENING_STATE_STOP:
            return None
        return False

    def update_state(self, data: dict[str, Any]) -> bool:
        """Update the opening state from gateway data."""
        if data.get("open_act_id") != self._open_act_id:
            return False
        changed = False
        if "status" in data:
            old_state = self._state
            self._state = data["status"]
            if old_state != self._state:
                changed = True
                _LOGGER.debug(
                    "OPENING %s (open_act_id: %d) - changed: %s -> %s",
                    self._name, self._open_act_id, old_state, self._state
                )
        return changed

    async def async_open(self):
        """Start opening."""
        _LOGGER.debug("Opening %s (act_id: %d, wanted_status: 1)", self._name, self._open_act_id)
        await self._gateway.tx_command({
            "cmd_name": "opening_move_req",
            "act_id": self._open_act_id,
            "wanted_status": OPENING_STATE_OPENING,
            "client": ""
        })

    async def async_close(self):
        """Start closing."""
        _LOGGER.debug("Closing %s (act_id: %d, wanted_status: 2)", self._name, self._open_act_id)
        await self._gateway.tx_command({
            "cmd_name": "opening_move_req",
            "act_id": self._open_act_id,
            "wanted_status": OPENING_STATE_CLOSING,
            "client": ""
        })

    async def async_stop(self):
        """Stop the movement."""
        _LOGGER.debug("Stopping %s (act_id: %d, wanted_status: 0)", self._name, self._open_act_id)
        await self._gateway.tx_command({
            "cmd_name": "opening_move_req",
            "act_id": self._open_act_id,
            "wanted_status": OPENING_STATE_STOP,
            "client": ""
        })


# ============================================================
# ===== DISCOVERY =====
# ============================================================

async def discover_openings(gateway):
    """Discover all available motorized openings."""
    _LOGGER.debug("Discovering motorized openings")

    try:
        resp = await gateway.tx_command({
            "cmd_name": "nested_openings_list_req",
            "username": "admin",
            "topologic_scope": "plant"
        }, resp_command="openings_list_resp")

        if not resp:
            _LOGGER.error("No response from gateway")
            return []

        openings = []
        for floor in resp.get("array", []):
            for room in floor.get("array", []):
                for item in room.get("array", []):
                    if item.get("leaf", True):
                        opening = DomoOpening(gateway, item)
                        openings.append(opening)

        _LOGGER.debug("Discovered %d motorized openings", len(openings))
        return openings

    except Exception as err:
        _LOGGER.error("Openings discovery failed: %s", err)
        return []


# ============================================================
# ===== REFRESH =====
# ============================================================

async def refresh_all_openings(gateway):
    """Resynchronize state of all motorized openings after a gateway reconnect."""
    _LOGGER.debug("Refreshing motorized openings state after reconnect")

    try:
        resp = await gateway.tx_command({
            "cmd_name": "nested_openings_list_req",
            "username": "admin",
            "topologic_scope": "plant"
        }, resp_command="openings_list_resp")

        if not resp:
            _LOGGER.error("No response from gateway during openings refresh")
            return

        count = 0
        for floor in resp.get("array", []):
            for room in floor.get("array", []):
                for item in room.get("array", []):
                    if not item.get("leaf", True):
                        continue
                    open_act_id = item.get("open_act_id")
                    opening = _OPENINGS.get(open_act_id)
                    if opening is None:
                        _LOGGER.warning(
                            "Refresh: opening open_act_id=%s not in cache, skipping",
                            open_act_id
                        )
                        continue
                    if opening.update_state(item) and gateway and gateway.hass:
                        async_dispatcher_send(
                            gateway.hass,
                            SIGNAL_UPDATE_ENTITY,
                            opening.unique_id
                        )
                    count += 1

        _LOGGER.info("Openings refresh completed: %d entities checked", count)

    except Exception as err:
        _LOGGER.error("Openings refresh failed: %s", err)


# ============================================================
# ===== ACCESSORS =====
# ============================================================

def get_all_openings() -> list[DomoOpening]:
    """Return all motorized openings."""
    return list(_OPENINGS.values())


def get_opening(open_act_id: int) -> DomoOpening | None:
    """Return an opening by open_act_id."""
    return _OPENINGS.get(open_act_id)


# ============================================================
# ===== UPDATE HANDLER =====
# ============================================================

def handle_opening_status_update(gateway, device_info):
    """Handle status updates for motorized openings."""
    open_act_id = device_info.get("open_act_id")
    if not open_act_id:
        return

    opening = _OPENINGS.get(open_act_id)
    if opening:
        opening.update_state(device_info)

        _LOGGER.debug(
            "OPENING - open_act_id: %s, state: %s",
            open_act_id, device_info.get("status")
        )

        if gateway and gateway.hass:
            async_dispatcher_send(
                gateway.hass,
                SIGNAL_UPDATE_ENTITY,
                opening.unique_id
            )
