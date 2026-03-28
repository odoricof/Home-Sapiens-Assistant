"""
platforms/activations.py

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

# Stati possibili per le attivazioni
ACTIVATION_STATE_OFF = 0
ACTIVATION_STATE_ON = 1

_ACTIVATIONS: dict[int, DomoActivation] = {}


class DomoActivation:
    """Attivazione/relay ETI Domo."""

    def __init__(self, gateway, activation_data: Dict[str, Any]):
        """Inizializza un'attivazione."""
        self._gateway = gateway
        self._act_id = activation_data["act_id"]
        self._name = activation_data.get("name", f"Activation {self._act_id}")
        self._state = activation_data.get("status", ACTIVATION_STATE_OFF)
        self._icon_id = activation_data.get("icon_id")
        
        _ACTIVATIONS[self._act_id] = self
        
        _LOGGER.debug("ACTIVATION created: %s (ID: %d) - stato: %s, icon_id: %s", 
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
        """Restituisce l'icon_id dal gateway."""
        return self._icon_id
        
    @property
    def is_on(self) -> bool:
        """Restituisce True se l'attivazione è attiva (ON)."""
        return self._state == ACTIVATION_STATE_ON

    def update_state(self, data: Dict[str, Any]) -> bool:
        """Aggiorna lo stato dell'attivazione."""
        if data.get("act_id") != self._act_id:
            return False
        if "status" in data:
            old_state = self._state
            self._state = data["status"]
            if old_state != self._state:
                _LOGGER.debug("ACTIVATION %s (ID: %d) - cambiato: %s -> %s", 
                             self._name, self._act_id, old_state, self._state)
        return True

    async def async_turn_on(self):
        """Accende l'attivazione."""
        _LOGGER.debug("Turning on activation %s (ID: %d)", self._name, self._act_id)
        await self._gateway.tx_command({
            "cmd_name": "relay_activation_req",
            "act_id": self._act_id,
            "status": 1
        })

    async def async_turn_off(self):
        """Spegne l'attivazione."""
        _LOGGER.debug("Turning off activation %s (ID: %d)", self._name, self._act_id)
        await self._gateway.tx_command({
            "cmd_name": "relay_activation_req",
            "act_id": self._act_id,
            "status": 0
        })


async def discover_activations(gateway):
    """Scopri tutte le attivazioni/relay disponibili."""
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


def get_all_activations() -> List[DomoActivation]:
    """Restituisce tutte le attivazioni."""
    return list(_ACTIVATIONS.values())


def get_activation(act_id: int) -> Optional[DomoActivation]:
    """Restituisce un'attivazione per ID."""
    return _ACTIVATIONS.get(act_id)


def handle_activation_status_update(gateway, device_info):
    """Gestisce aggiornamenti di stato delle attivazioni."""
    act_id = device_info.get("act_id")
    if not act_id:
        return
    
    # Aggiorna SOLO se c'è il campo status
    if "status" in device_info:
        activation = _ACTIVATIONS.get(act_id)
        if activation:
            activation.update_state(device_info)
            
            _LOGGER.debug("🔌 ACTIVATION - act_id: %s, stato: %s", 
                         act_id, device_info.get("status"))        
            
            if gateway and gateway.hass:
                async_dispatcher_send(
                    gateway.hass,
                    SIGNAL_UPDATE_ENTITY,
                    activation.unique_id
                )
