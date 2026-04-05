"""
platforms/openings.py

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

# Stati per aperture motorizzate
OPENING_STATE_STOP = 0
OPENING_STATE_OPENING = 1
OPENING_STATE_CLOSING = 2

_OPENINGS: dict[int, DomoOpening] = {}


class DomoOpening:
    """Apertura motorizzata ETI Domo."""

    def __init__(self, gateway, opening_data: Dict[str, Any]):
        """Inizializza un'apertura motorizzata."""
        self._gateway = gateway
        self._open_act_id = opening_data["open_act_id"]
        self._close_act_id = opening_data["close_act_id"]
        self._name = opening_data.get("name", f"Opening {self._open_act_id}")
        self._state = opening_data.get("status", OPENING_STATE_STOP)
        self._type = opening_data.get("type", 0)
        
        _OPENINGS[self._open_act_id] = self
        
        _LOGGER.debug("OPENING created: %s (open_act_id: %d, close_act_id: %d) - stato: %s", 
                     self._name, self._open_act_id, self._close_act_id, self._state)

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
        """Restituisce il tipo: 0=shutter, 1=blind."""
        return self._type        

    @property
    def is_opening(self) -> bool:
        """Restituisce True se l'apertura è in movimento di apertura."""
        return self._state == OPENING_STATE_OPENING

    @property
    def is_closing(self) -> bool:
        """Restituisce True se l'apertura è in movimento di chiusura."""
        return self._state == OPENING_STATE_CLOSING

    @property
    def is_closed(self) -> bool:
        """Restituisce True se l'apertura è ferma (non in movimento)."""
        return self._state == OPENING_STATE_STOP

    def update_state(self, data: Dict[str, Any]) -> bool:
        """Aggiorna lo stato dell'apertura."""
        if data.get("open_act_id") != self._open_act_id:
            return False
        if "status" in data:
            old_state = self._state
            self._state = data["status"]
            if old_state != self._state:
                _LOGGER.debug("OPENING %s (open_act_id: %d) - cambiato: %s -> %s", 
                             self._name, self._open_act_id, old_state, self._state)
        return True

    async def async_open(self):
        """Avvia l'apertura."""
        _LOGGER.debug("Opening %s (act_id: %d, wanted_status: 1)", self._name, self._open_act_id)
        await self._gateway.tx_command({
            "cmd_name": "opening_move_req",
            "act_id": self._open_act_id,
            "wanted_status": OPENING_STATE_OPENING,
            "client": ""
        })

    async def async_close(self):
        """Avvia la chiusura."""
        _LOGGER.debug("Closing %s (act_id: %d, wanted_status: 2)", self._name, self._open_act_id)
        await self._gateway.tx_command({
            "cmd_name": "opening_move_req",
            "act_id": self._open_act_id,  # Usa open_act_id, come nei log
            "wanted_status": OPENING_STATE_CLOSING,
            "client": ""
        })

    async def async_stop(self):
        """Ferma il movimento."""
        _LOGGER.debug("Stopping %s (act_id: %d, wanted_status: 0)", self._name, self._open_act_id)
        await self._gateway.tx_command({
            "cmd_name": "opening_move_req",
            "act_id": self._open_act_id,
            "wanted_status": OPENING_STATE_STOP,
            "client": ""
        })


async def discover_openings(gateway):
    """Scopri tutte le aperture motorizzate disponibili."""
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
        # Naviga la struttura nidificata
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


def get_all_openings() -> List[DomoOpening]:
    """Restituisce tutte le aperture motorizzate."""
    return list(_OPENINGS.values())


def get_opening(open_act_id: int) -> Optional[DomoOpening]:
    """Restituisce un'apertura per open_act_id."""
    return _OPENINGS.get(open_act_id)


def handle_opening_status_update(gateway, device_info):
    """Gestisce aggiornamenti di stato delle aperture motorizzate."""
    open_act_id = device_info.get("open_act_id")
    if not open_act_id:
        return
    
    opening = _OPENINGS.get(open_act_id)
    if opening:
        opening.update_state(device_info)
        
        _LOGGER.debug("⏛ OPENING - open_act_id: %s, stato: %s", 
                     open_act_id, device_info.get("status"))        
        
        if gateway and gateway.hass:
            async_dispatcher_send(
                gateway.hass,
                SIGNAL_UPDATE_ENTITY,
                opening.unique_id
            )
