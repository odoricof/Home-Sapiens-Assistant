"""
domo/platforms/lights.py

Entities fed by this file:
- domo/light.py : consumes get_all_lights() and DomoLight objects to create and update light entities
- domo/__init__.py : calls discover_lights() / refresh_all_lights() and registers handle_light_status_update() as gateway event callback

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
import logging
from typing import Any

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)


LIGHT_TYPES = ["STEP_STEP", "DIMMER", "rgb"]

_LIGHTS: dict[int, "DomoLight"] = {}


# ============================================================
# ===== DISCOVERY =====
# ============================================================

async def discover_lights(gateway):
    """Discover all available lights."""
    _LOGGER.info("LIGHTS starting discovery")

    try:
        resp = await gateway.tx_command({
            "cmd_name": "nested_light_list_req",
            "topologic_scope": "plant"
        }, resp_command="light_list_resp")

        if not resp:
            _LOGGER.error("LIGHTS discovery: no response")
            return None

        lights_found = []
        for floor in resp.get("array", []):
            floor_name = floor.get("name")

            for room in floor.get("array", []):
                room_name = room.get("name")

                for light in room.get("array", []):
                    if light.get("leaf"):
                        light_obj = DomoLight(
                            gateway,
                            light,
                            floor_name,
                            room_name
                        )
                        _LIGHTS[light.get("act_id")] = light_obj
                        lights_found.append(light_obj)

        _LOGGER.info("LIGHTS discovered %d devices", len(lights_found))
        return lights_found

    except Exception as err:
        _LOGGER.error("LIGHTS discovery failed: %s", err)
        return None


async def refresh_all_lights(gateway):
    """Restore pre-disconnect light state, then resync entities from the gateway."""
    _LOGGER.info("LIGHTS restoring and resyncing state after gateway reconnect")

    pre_disconnect_states = {
        light.act_id: (light.is_on, light.brightness, light.rgb_color)
        for light in get_all_lights()
    }

    for act_id, (was_on, brightness, rgb) in pre_disconnect_states.items():
        light = get_light(act_id)
        if not light:
            continue

        try:
            if was_on:
                await light.turn_on(brightness, rgb)
            else:
                await light.turn_off()
        except Exception as err:
            _LOGGER.error("LIGHTS restore: failed to restore %s: %s", light.name, err)

        await asyncio.sleep(0.2)

    try:
    
        resp = await gateway.tx_command({
            "cmd_name": "nested_light_list_req",
            "topologic_scope": "plant"
        }, resp_command="light_list_resp")

        if not resp:
            _LOGGER.error("LIGHTS refresh: no response")
            return

        updated_count = 0
        updated_names = []
        for floor in resp.get("array", []):
            for room in floor.get("array", []):
                for light_data in room.get("array", []):
                    if not light_data.get("leaf"):
                        continue

                    act_id = light_data.get("act_id")
                    light = get_light(act_id)
                    if not light:
                        _LOGGER.warning("LIGHTS refresh: unknown act_id %s, skipping", act_id)
                        continue

                    if light.refresh_state(light_data) and gateway.hass:
                        updated_count += 1
                        updated_names.append(light.name)
                        async_dispatcher_send(
                            gateway.hass,
                            SIGNAL_UPDATE_ENTITY,
                            light.unique_id
                        )

        _LOGGER.info("LIGHTS refresh complete, %d entities updated", updated_count)
              
    except Exception as err:
        _LOGGER.error("LIGHTS refresh failed: %s", err)


# ============================================================
# ===== LOOKUP HELPERS =====
# ============================================================

def get_light(act_id: int) -> "DomoLight | None":
    """Return a light object by its act_id."""
    return _LIGHTS.get(act_id)


def get_all_lights() -> list["DomoLight"]:
    """Return all lights."""
    return list(_LIGHTS.values())


# ============================================================
# ===== LIGHT ENTITY MODEL =====
# ============================================================

class DomoLight:
    """Logical representation of an ETI Domo light."""

    def __init__(self, gateway, light_data: dict[str, Any], floor: str, room: str):
        """Initialize the light."""
        self._gateway = gateway
        self._act_id = light_data.get("act_id")
        self._name = light_data.get("name")
        self._type = light_data.get("type", "STEP_STEP")
        self._floor = floor
        self._room = room

        self._state = light_data.get("status", 0)
        self._brightness = light_data.get("perc", 0)
        self._rgb = light_data.get("rgb", [0, 0, 0])

        _LOGGER.debug("LIGHT created: %s (ID: %d, type: %s)",
                     self._name, self._act_id, self._type)

    @property
    def act_id(self) -> int:
        """Return the actuator ID."""
        return self._act_id

    @property
    def name(self) -> str:
        """Return the light name."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID for HA."""
        return f"light.domo_{self._act_id}_{self._name.lower().replace(' ', '_')}"

    @property
    def floor(self) -> str:
        """Return the floor."""
        return self._floor

    @property
    def room(self) -> str:
        """Return the room."""
        return self._room

    @property
    def light_type(self) -> str:
        """Return the light type."""
        return self._type

    @property
    def is_on(self) -> bool:
        """Return True if the light is on."""
        return self._state == 1

    @property
    def brightness(self) -> int:
        """Return the brightness percentage."""
        return self._brightness

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Return the RGB color."""
        r, g, b = self._rgb
        return (r, g, b)

    async def turn_on(self, brightness: int | None = None, rgb: tuple | None = None):
        """Turn on the light."""
        payload = {
            "cmd_name": "light_switch_req",
            "act_id": self._act_id,
            "wanted_status": 1,
        }

        if brightness is not None:
            payload["perc"] = brightness

        if self._type == "rgb" and rgb is not None:
            payload["rgb"] = list(rgb)

        return await self._gateway.tx_command(payload, resp_command=None)

    async def turn_off(self):
        """Turn off the light."""
        payload = {
            "cmd_name": "light_switch_req",
            "act_id": self._act_id,
            "wanted_status": 0,
            "perc": 0,
        }

        return await self._gateway.tx_command(payload, resp_command=None)

    def update_state(self, data: dict[str, Any]):
        """Update the state from a live event payload."""
        if data.get("act_id") != self._act_id:
            return False

        if data.get("cmd_name") == "light_switch_ind":
            old_state = self._state
            self._state = data.get("status", self._state)
            if old_state != self._state:
                _LOGGER.debug("Light %s changed to %s", self._name, self._state)

        if "perc" in data:
            self._brightness = data.get("perc")
        if "rgb" in data:
            self._rgb = data.get("rgb")

        return True

    def refresh_state(self, light_data: dict[str, Any]) -> bool:
        """Force a state update from a full discovery/refresh payload"""

        changed = False

        new_state = light_data.get("status", self._state)
        if new_state != self._state:
            self._state = new_state
            changed = True

        if "perc" in light_data and light_data["perc"] != self._brightness:
            self._brightness = light_data["perc"]
            changed = True

        if "rgb" in light_data and light_data["rgb"] != self._rgb:
            self._rgb = light_data["rgb"]
            changed = True

        if changed:
            _LOGGER.debug("LIGHT %s refreshed: state=%s perc=%s rgb=%s",
                         self._name, self._state, self._brightness, self._rgb)

        return changed


# ============================================================
# ===== EVENT HANDLERS =====
# ============================================================

def handle_light_status_update(gateway, device_info: dict[str, Any]) -> bool:
    """Handle light status updates from the gateway event bus."""
    act_id = device_info.get("act_id")
    if not act_id:
        return False

    light = get_light(act_id)
    if not light:
        return False

    updated = light.update_state(device_info)

    if updated and gateway.hass:
        async_dispatcher_send(
            gateway.hass,
            SIGNAL_UPDATE_ENTITY,
            light.unique_id
        )

    return updated
