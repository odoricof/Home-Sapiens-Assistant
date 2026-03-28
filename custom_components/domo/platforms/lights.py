"""
domo/platforms/lights.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)

# Mappa dei tipi luce supportati
LIGHT_TYPES = ["STEP_STEP", "DIMMER", "rgb"]

# Dizionario globale per tenere traccia di tutte le luci
_LIGHTS: dict[int, "DomoLight"] = {}


async def discover_lights(gateway):
    """Scopri tutte le luci disponibili."""
    _LOGGER.info("LIGHTS starting discovery")
    
    try:
        # Richiedi lista luci
        resp = await gateway.tx_command({
            "cmd_name": "nested_light_list_req",
            "topologic_scope": "plant"
        }, resp_command="light_list_resp")
        
        if not resp:
            _LOGGER.error("LIGHTS discovery: no response")
            return None
        
        # Parsing della struttura annidata
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


def get_light(act_id: int) -> Optional["DomoLight"]:
    """Restituisce un oggetto luce dal suo act_id."""
    return _LIGHTS.get(act_id)


def get_all_lights() -> List["DomoLight"]:
    """Restituisce tutte le luci."""
    return list(_LIGHTS.values())



class DomoLight:
    """Rappresentazione logica di una luce ETI Domo."""

    def __init__(self, gateway, light_data: Dict[str, Any], floor: str, room: str):
        """Inizializza la luce."""
        self._gateway = gateway
        self._act_id = light_data.get("act_id")
        self._name = light_data.get("name")
        self._type = light_data.get("type", "STEP_STEP")
        self._floor = floor
        self._room = room
        
        # Stato corrente
        self._state = light_data.get("status", 0)
        self._brightness = light_data.get("perc", 0)
        self._rgb = light_data.get("rgb", [0, 0, 0])
        
        _LOGGER.debug("LIGHT created: %s (ID: %d, type: %s)", 
                     self._name, self._act_id, self._type)

    @property
    def act_id(self) -> int:
        """Restituisce l'ID attuatore."""
        return self._act_id

    @property
    def name(self) -> str:
        """Restituisce il nome della luce."""
        return self._name


    @property
    def unique_id(self) -> str:
        """Restituisce l'ID univoco per HA."""
        return f"light.domo_{self._act_id}_{self._name.lower().replace(' ', '_')}"

    @property
    def floor(self) -> str:
        """Restituisce il piano."""
        return self._floor

    @property
    def room(self) -> str:
        """Restituisce la stanza."""
        return self._room

    @property
    def light_type(self) -> str:
        """Restituisce il tipo di luce."""
        return self._type

    @property
    def is_on(self) -> bool:
        """Restituisce True se la luce è accesa."""
        return self._state == 1

    @property
    def brightness(self) -> int:
        """Restituisce la luminosità in percentuale."""
        return self._brightness

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Restituisce il colore RGB."""
        r, g, b = self._rgb
        return (r, g, b)

    async def turn_on(self, brightness: Optional[int] = None, rgb: Optional[tuple] = None):
        payload = {
            "cmd_name": "light_switch_req",
            "act_id": self._act_id,
            "wanted_status": 1,
        }
        
        # Aggiungi perc SOLO se brightness è specificato
        if brightness is not None:
            payload["perc"] = brightness
            
        # Gestione RGB
        if self._type == "rgb" and rgb is not None:
            payload["rgb"] = list(rgb)
            
        return await self._gateway.tx_command(payload, resp_command=None)

    async def turn_off(self):
        payload = {
            "cmd_name": "light_switch_req",
            "act_id": self._act_id,
            "wanted_status": 0,
            "perc": 0,
        }

        return await self._gateway.tx_command(payload, resp_command=None)

    def update_state(self, data: Dict[str, Any]):
        """Aggiorna lo stato in base ai dati ricevuti."""
        if data.get("act_id") != self._act_id:
            return False
        # Aggiorna stato per eventi light_switch_ind
        if data.get("cmd_name") == "light_switch_ind":
            old_state = self._state
            self._state = data.get("status", self._state)
            if old_state != self._state:
                _LOGGER.debug("Light %s changed to %s", self._name, self._state)      
        #self._state = data.get("status", self._state)
        if "perc" in data:
            self._brightness = data.get("perc")
        if "rgb" in data:
            self._rgb = data.get("rgb")
        
        return True


def handle_light_status_update(gateway, device_info: Dict[str, Any]) -> bool:
    """Gestisce gli aggiornamenti di stato delle luci."""
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
    
    
    
    
    
