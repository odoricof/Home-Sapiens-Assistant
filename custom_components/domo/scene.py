"""
domo/scene.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from homeassistant.components.scene import BaseScene
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .platforms.scenarios import DomoScenarioDevice, get_scenario_device

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Setup scene platform per gli scenari Domo."""
    
    # Ottieni il device scenari
    scenario_device = get_scenario_device()
    if not scenario_device:
        _LOGGER.error("No scenario device found")
        return
    
    # Inizializza struttura per tracciare le entità scenario
    if "domo_scenarios" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["domo_scenarios"] = {}
    
    existing_entities = hass.data[DOMAIN]["domo_scenarios"]
    
    def create_new_entities(scenario_list: List[Dict[str, Any]], entry_id: str) -> List['DomoScenarioEntity']:
        """Crea nuove entità per scenari non ancora registrati."""
        new_entities = []
        
        for scenario in scenario_list:
            # Normalizza il campo user_defined (può arrivare come user_defined o user-defined)
            scenario["user_defined"] = scenario.get("user_defined", scenario.get("user-defined", 0))
            
            scenario_id = scenario.get("id")
            if scenario_id is None:
                _LOGGER.debug("Scenario without ID ignored: %s", scenario)
                continue
            
            entity = existing_entities.get(scenario_id)
            
            # Se l'entità non è ancora registrata, creala
            if entity is None or entity.hass is None:
                entity = DomoScenarioEntity(scenario, scenario_device, entry_id)
                existing_entities[scenario_id] = entity
                new_entities.append(entity)
                _LOGGER.debug(
                    "Created new scenario entity: %s (ID: %d, User defined: %s)",
                    scenario.get("name"), scenario_id, scenario.get("user_defined")
                )
        
        return new_entities
    
    # Carica gli scenari iniziali
    initial_scenarios = await scenario_device.available_scenarios()
    _LOGGER.debug("Initial setup: loaded %d scenarios", len(initial_scenarios))
    
    new_entities = create_new_entities(initial_scenarios, config_entry.entry_id)
    async_add_entities(new_entities)
    
    # Funzione per gestire il refresh della lista scenari
    async def handle_refresh_scenarios():
        """Gestisce l'evento di refresh della lista scenari."""
        _LOGGER.debug("Received scenarios refresh event")
        
        # Ricarica la lista scenari - chiamata diretta async
        updated_scenarios = await scenario_device.available_scenarios()
        
        # IDs correnti e nuovi
        existing_ids = set(existing_entities.keys())
        current_ids = set(s["id"] for s in updated_scenarios if s.get("id") is not None)
        
        # Rimuovi entità obsolete
        removed_ids = existing_ids - current_ids
        registry = async_get_entity_registry(hass)
        
        for rid in removed_ids:
            entity = existing_entities.pop(rid, None)
            if entity is None:
                continue
            
            entity_id = entity.entity_id
            
            # Rimuovi dal runtime
            if entity.hass is not None:
                await entity.async_remove()
                _LOGGER.debug("Removed scenario %d from runtime", rid)
            
            # Rimuovi dal registry
            if registry.async_is_registered(entity_id):
                registry.async_remove(entity_id)
                _LOGGER.debug("Removed scenario %d from registry", rid)
        
        # Aggiungi nuove entità
        new_entities = create_new_entities(updated_scenarios, config_entry.entry_id)
        if new_entities:
            _LOGGER.debug("Adding %d new scenario entities", len(new_entities))
            async_add_entities(new_entities, update_before_add=True)
        
        # Aggiorna le entità esistenti
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
    
    # Registra listener per eventi di refresh
    async def _dispatcher_handler():
        hass.async_create_task(handle_refresh_scenarios())
    
    async_dispatcher_connect(hass, "domo_scenarios_refreshed", _dispatcher_handler)


class DomoScenarioEntity(BaseScene):
    """Rappresentazione di uno scenario Domo."""

    def __init__(self, scenario: Dict[str, Any], scenario_device: DomoScenarioDevice, entry_id: str):
        """Inizializza l'entità scenario."""
        self._scenario_device = scenario_device
        self._scenario = scenario
        self._attr_name = scenario.get("name", "Unknown Scenario")
        self._attr_unique_id = f"scene.domo_scenario_{scenario['id']}"
        self._attr_should_poll = False
        self._unsub = None
        
        """DEVICE INFO"""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_scenarios")},
            name="Scenarios",
            manufacturer="Home Sapiens",
            model=" ",
        )        
        
        
    async def _async_activate(self, **kwargs: Any) -> None:
        """Attiva lo scenario - chiamato da HA quando si usa scene.turn_on."""
        
        try:
            success = await self._scenario_device.activate_scenario(self._scenario["id"])
            
            if success:
                _LOGGER.debug("Successfully activated scenario %d via HA", self._scenario["id"])
                
                # Dopo l'attivazione, attendi un momento e poi richiedi il refresh
                await asyncio.sleep(1)
                async_dispatcher_send(self.hass, "domo_scenarios_refreshed")
                    
        except Exception as err:
            _LOGGER.error("Error activating scenario %d: %s", self._scenario["id"], err)

    async def async_added_to_hass(self) -> None:
        """Registra per gli aggiornamenti quando l'entità viene aggiunta."""
        @callback
        def handle_update(scenario_id: int, new_data: dict):
            """Gestisce aggiornamenti specifici per questo scenario (attivazioni esterne)."""
            if scenario_id == self._scenario["id"]:
                old_status = self._scenario.get("scenario_status")
                new_status = new_data.get("scenario_status")
                        
                self._scenario.update(new_data)
                # Chiama _async_record_activation() SOLO quando si passa a stato 2 (attivato)
                if old_status != 2 and new_status == 2:
                    self._async_record_activation()
                    self.async_write_ha_state()
                
        self._unsub = async_dispatcher_connect(
            self.hass, "domo_scenario_update", handle_update
        )               
        

    async def async_will_remove_from_hass(self) -> None:
        """Clean up on removal."""
        if self._unsub:
            self._unsub()
            self._unsub = None


    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Attributi aggiuntivi per lo scenario."""
        return {
            "id": self._scenario["id"],
            "scenario_status": self._scenario.get("scenario_status", 0),
            "user_defined": self._scenario.get("user-defined", self._scenario.get("user_defined", 0)),
        }
