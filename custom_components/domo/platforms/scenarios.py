"""
platforms/scenarios.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)

# Dizionario per tenere traccia degli scenari (usiamo un ID fisso -1 per il dispositivo contenitore)
_SCENARIO_DEVICE = None


class DomoScenarioDevice:
    """Dispositivo contenitore per tutti gli scenari Domo."""

    def __init__(self, gateway):
        self._gateway = gateway
        self._name = "Scenari"
        self._act_id = -1  # ID fisso per il contenitore scenari
        
        global _SCENARIO_DEVICE
        _SCENARIO_DEVICE = self
        
        _LOGGER.debug("SCENARIO device created")

    @property
    def act_id(self) -> int:
        return self._act_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"scene.domo_scenarios"

    async def available_scenarios(self) -> List[Dict[str, Any]]:
        """Restituisce la lista degli scenari disponibili."""
        return await self._get_scenarios()

    async def _get_scenarios(self) -> List[Dict[str, Any]]:
        """Recupera la lista degli scenari dal gateway."""
        resp = await self._gateway.tx_command({
            "cmd_name": "scenarios_list_req"
        }, resp_command="scenarios_list_resp")
        
        if not resp:
            _LOGGER.error("No response from gateway for scenarios list")
            return []
        
        scenarios = resp.get("array", [])
        _LOGGER.debug("Retrieved %d scenarios", len(scenarios))
        return scenarios

    async def activate_scenario(self, scenario_id: int) -> bool:
        """Attiva uno scenario esistente."""
        await self._gateway.tx_command({
            "cmd_name": "scenario_activation_req",
            "id": scenario_id
        }, resp_command=None)  # Non aspettiamo risposta specifica
        
        _LOGGER.debug("Activated scenario %d", scenario_id)
        return True

    async def create_scenario(self, name: str) -> bool:
        """Inizia la registrazione di un nuovo scenario."""
        resp = await self._gateway.tx_command({
            "cmd_name": "scenario_registration_start",
            "name": name
        }, resp_command="scenario_registration_start_ack")
        
        success = resp is not None
        if success:
            _LOGGER.debug("Started scenario creation: %s", name)
        return success

    async def delete_scenario(self, scenario_id: int) -> bool:
        """Elimina uno scenario esistente."""
        resp = await self._gateway.tx_command({
            "cmd_name": "scenario_delete_req",
            "id": scenario_id
        }, resp_command="scenario_delete_resp")
        
        success = resp is not None
        if success:
            _LOGGER.debug("Deleted scenario %d", scenario_id)
        return success

    def update_state(self, data: Dict[str, Any]) -> bool:
        """Aggiorna lo stato del device scenari (non usato)."""
        return False


async def discover_scenarios(gateway):
    """Scopri il device scenari."""
    _LOGGER.debug("Discovering scenarios device")
    
    scenario_device = DomoScenarioDevice(gateway)
    _LOGGER.debug("Scenarios device created")
    return [scenario_device]


def get_scenario_device():
    """Restituisce il device scenari."""
    return _SCENARIO_DEVICE


def handle_scenario_status_update(gateway, device_info):
    """Gestisce aggiornamenti di stato degli scenari."""
    cmd_name = device_info.get("cmd_name")
    if not cmd_name:
        return
    
    # Gestisci aggiornamento stato scenario
    if cmd_name == "scenario_status_ind":
        scenario_id = device_info.get("id")
        _LOGGER.debug("Scenario status update for ID %d: %s", scenario_id, device_info)
        
        if gateway and gateway.hass:
            # Invia segnale per aggiornamento specifico scenario
            async_dispatcher_send(
                gateway.hass,
                "domo_scenario_update",
                scenario_id,
                device_info
            )
            
    # Gestisci creazione/modifica scenario da UI
    elif cmd_name == "scenario_user_ind":
        action = device_info.get("action")
        if action in ("add", "create"):
            _LOGGER.debug("Scenario user action: %s - refreshing list", action)
            
            if gateway and gateway.hass:
                # Invia segnale per refresh lista scenari
                async_dispatcher_send(
                    gateway.hass,
                    "domo_scenarios_refreshed"
                )
