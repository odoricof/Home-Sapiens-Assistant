"""
platforms/activations.py

Entities fed by this file:
- domo/switch.py : exposes DomoActivation as switch entities (state, turn on/off)

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

ACTIVATION_STATE_OFF = 0
ACTIVATION_STATE_ON = 1

_ACTIVATIONS: dict[int, DomoActivation] = {}


# ============================================================
# ===== DEVICE MODEL =====
# ============================================================

class DomoActivation:
    """ETI Domo activation/relay."""

    def __init__(self, gateway, activation_data: dict[str, Any]):
        """Initialize an activation."""
        self._gateway = gateway
        self._act_id = activation_data["act_id"]
        self._name = activation_data.get("name", f"Activation {self._act_id}")
        self._state = activation_data.get("status", ACTIVATION_STATE_OFF)
        self._icon_id = activation_data.get("icon_id")

        _ACTIVATIONS[self._act_id] = self

        _LOGGER.debug("ACTIVATION created: %s (ID: %d) - state: %s, icon_id: %s",
                     self._name, self._act_id, self._state, self._icon_id)

    @property
    def act_id(self) -> int:
        return self._act_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"switch.domo_{self._act_id}"

    @property
    def icon_id(self) -> int | None:
        """Return the icon_id from the gateway."""
        return self._icon_id

    @property
    def is_on(self) -> bool:
        """Return True if the activation is ON."""
        return self._state == ACTIVATION_STATE_ON

    def update_state(self, data: dict[str, Any]) -> bool:
        """Update the activation state."""
        if data.get("act_id") != self._act_id:
            return False
        if "status" in data:
            old_state = self._state
            self._state = data["status"]
            if old_state != self._state:
                _LOGGER.debug("ACTIVATION %s (ID: %d) - changed: %s -> %s",
                             self._name, self._act_id, old_state, self._state)
        return True

    async def async_turn_on(self):
        """Turn on the activation."""
        _LOGGER.debug("Turning on activation %s (ID: %d)", self._name, self._act_id)
        await self._gateway.tx_command({
            "cmd_name": "relay_activation_req",
            "act_id": self._act_id,
            "status": 1
        })

    async def async_turn_off(self):
        """Turn off the activation."""
        _LOGGER.debug("Turning off activation %s (ID: %d)", self._name, self._act_id)
        await self._gateway.tx_command({
            "cmd_name": "relay_activation_req",
            "act_id": self._act_id,
            "status": 0
        })


# ============================================================
# ===== DISCOVERY & REFRESH =====
# ============================================================

async def discover_activations(gateway):
    """Discover all available activations/relays."""
    _LOGGER.debug("Discovering activations/relays")

    try:
        resp = await gateway.tx_command({
            "cmd_name": "relays_list_req",
            "topologic_scope": "plant"
        }, resp_command="relays_list_resp")

        if not resp:
            _LOGGER.error("No response from gateway")
            return []

        activations = []
        for item in resp.get("array", []):
            if item.get("leaf", True):
                activation = DomoActivation(gateway, item)
                activations.append(activation)

        _LOGGER.debug("Discovered %d activations/relays", len(activations))
        return activations

    except Exception as err:
        _LOGGER.error("Activations discovery failed: %s", err)
        return []


async def refresh_all_activations(gateway):
    """Request the full state of all activations from the gateway and
    update the existing DomoActivation objects."""
    _LOGGER.info("ACTIVATIONS refreshing state after gateway reconnect")

    try:
        resp = await gateway.tx_command({
            "cmd_name": "relays_list_req",
            "topologic_scope": "plant"
        }, resp_command="relays_list_resp")

        if not resp:
            _LOGGER.error("ACTIVATIONS refresh: no response")
            return

        updated_count = 0
        for item in resp.get("array", []):
            if not item.get("leaf", True):
                continue

            act_id = item.get("act_id")
            activation = get_activation(act_id)
            if not activation:
                _LOGGER.warning("ACTIVATIONS refresh: unknown act_id %s, skipping", act_id)
                continue

            was_on = activation.is_on
            activation.update_state(item)

            if activation.is_on != was_on and gateway.hass:
                updated_count += 1
                async_dispatcher_send(
                    gateway.hass,
                    SIGNAL_UPDATE_ENTITY,
                    activation.unique_id
                )

        _LOGGER.info("ACTIVATIONS refresh complete, %d entities updated", updated_count)

    except Exception as err:
        _LOGGER.error("ACTIVATIONS refresh failed: %s", err)


# ============================================================
# ===== LOOKUP HELPERS =====
# ============================================================

def get_all_activations() -> list[DomoActivation]:
    """Return all activations."""
    return list(_ACTIVATIONS.values())


def get_activation(act_id: int) -> DomoActivation | None:
    """Return an activation by ID."""
    return _ACTIVATIONS.get(act_id)


# ============================================================
# ===== PUSH UPDATE HANDLER =====
# ============================================================

def handle_activation_status_update(gateway, device_info):
    """Handle activation status push updates."""
    act_id = device_info.get("act_id")
    if not act_id:
        return

    if "status" in device_info:
        activation = _ACTIVATIONS.get(act_id)
        if activation:
            activation.update_state(device_info)

            _LOGGER.debug("ACTIVATION - act_id: %s, state: %s",
                         act_id, device_info.get("status"))

            if gateway and gateway.hass:
                async_dispatcher_send(
                    gateway.hass,
                    SIGNAL_UPDATE_ENTITY,
                    activation.unique_id
                )
