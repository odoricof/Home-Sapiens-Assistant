"""
domo/scene.py

Entities fed by:
- platforms/scenarios.py

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

from homeassistant.components.scene import BaseScene
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import DOMAIN
from .platforms.scenarios import DomoScenarioDevice, get_scenario_device

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the scene platform for Domo scenarios."""
    scenario_device = get_scenario_device()
    if not scenario_device:
        _LOGGER.error("No scenario device found")
        return

    if "domo_scenarios" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["domo_scenarios"] = {}

    existing_entities = hass.data[DOMAIN]["domo_scenarios"]

    def create_new_entities(scenario_list: list[dict[str, Any]], entry_id: str) -> list["DomoScenarioEntity"]:
        """Create new entities for scenarios not yet registered."""
        new_entities = []

        for scenario in scenario_list:
            scenario["user_defined"] = scenario.get("user_defined", scenario.get("user-defined", 0))

            scenario_id = scenario.get("id")
            if scenario_id is None:
                _LOGGER.debug("Ignored scenario without ID: %s", scenario)
                continue

            entity = existing_entities.get(scenario_id)

            if entity is None or entity.hass is None:
                entity = DomoScenarioEntity(scenario, scenario_device, entry_id)
                existing_entities[scenario_id] = entity
                new_entities.append(entity)
                _LOGGER.debug(
                    "Created new scenario entity: %s (ID: %d, User defined: %s)",
                    scenario.get("name"), scenario_id, scenario.get("user_defined")
                )

        return new_entities

    # --- Initial scenarios ---
    initial_scenarios = await scenario_device.available_scenarios()
    _LOGGER.debug("Initial setup: loaded %d scenarios", len(initial_scenarios))

    new_entities = create_new_entities(initial_scenarios, config_entry.entry_id)
    async_add_entities(new_entities)

    # --- Scenario refresh ---
    async def handle_refresh_scenarios():
        """Handle the scenario list refresh event."""
        _LOGGER.debug("Received scenario refresh event")

        updated_scenarios = await scenario_device.available_scenarios()

        existing_ids = set(existing_entities.keys())
        current_ids = set(s["id"] for s in updated_scenarios if s.get("id") is not None)

        removed_ids = existing_ids - current_ids
        registry = async_get_entity_registry(hass)

        for rid in removed_ids:
            entity = existing_entities.pop(rid, None)
            if entity is None:
                continue

            entity_id = entity.entity_id

            if entity.hass is not None:
                await entity.async_remove()
                _LOGGER.debug("Removed scenario %d from runtime", rid)

            if registry.async_is_registered(entity_id):
                registry.async_remove(entity_id)
                _LOGGER.debug("Removed scenario %d from registry", rid)

        new_entities = create_new_entities(updated_scenarios, config_entry.entry_id)
        if new_entities:
            _LOGGER.debug("Adding %d new scenario entities", len(new_entities))
            async_add_entities(new_entities, update_before_add=True)

        for scenario in updated_scenarios:
            sid = scenario.get("id")
            if sid in existing_ids:
                entity = existing_entities[sid]
                old_name = entity.name
                entity._scenario = scenario
                entity._attr_name = scenario.get("name", "Unknown Scenario")
                entity._attr_unique_id = f"scene.domo_scenario_{sid}"

                if old_name != entity._attr_name:
                    _LOGGER.debug(
                        "Updated scenario %d: '%s' -> '%s'",
                        sid, old_name, entity._attr_name
                    )

                if entity.hass is not None:
                    entity.async_write_ha_state()

    # --- Refresh listener ---
    async def _dispatcher_handler():
        hass.async_create_task(handle_refresh_scenarios())

    async_dispatcher_connect(hass, "domo_scenarios_refreshed", _dispatcher_handler)


# ============================================================
# ===== SCENARIO ENTITY =====
# ============================================================

class DomoScenarioEntity(BaseScene):
    """Represents a Domo scenario."""

    _attr_should_poll = False

    def __init__(self, scenario: dict[str, Any], scenario_device: DomoScenarioDevice, entry_id: str):
        """Initialize the scenario entity."""
        self._scenario_device = scenario_device
        self._scenario = scenario
        self._attr_name = scenario.get("name", "Unknown Scenario")
        self._attr_unique_id = f"scene.domo_scenario_{scenario['id']}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenarios",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes for the scenario."""
        return {
            "id": self._scenario["id"],
            "scenario_status": self._scenario.get("scenario_status", 0),
            "user_defined": self._scenario.get("user-defined", self._scenario.get("user_defined", 0)),
        }

    async def _async_activate(self, **kwargs: Any) -> None:
        """Activate the scenario (called by HA via scene.turn_on)."""
        try:
            success = await self._scenario_device.activate_scenario(self._scenario["id"])
        except Exception as err:
            raise HomeAssistantError(
                f"Error activating scenario {self._scenario['id']}: {err}"
            ) from err

        if success:
            _LOGGER.debug("Scenario %d activated successfully via HA", self._scenario["id"])

            await asyncio.sleep(1)
            async_dispatcher_send(self.hass, "domo_scenarios_refreshed")

    async def async_added_to_hass(self) -> None:
        """Register the update listener when the entity is added."""
        @callback
        def handle_update(scenario_id: int, new_data: dict):
            if scenario_id != self._scenario["id"]:
                return

            old_status = self._scenario.get("scenario_status")
            new_status = new_data.get("scenario_status")

            self._scenario.update(new_data)

            if old_status != 2 and new_status == 2:
                self._async_record_activation()
                self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, "domo_scenario_update", handle_update)
        )
