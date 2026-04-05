"""
platforms/analogics.py

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

ANALOG_MIN_VALUE = 0
ANALOG_MAX_VALUE = 100

_ANALOGICS: dict[int, DomoAnalogIn] = {}


class DomoAnalogIn:
    """Ingresso analogico ETI Domo."""

    def __init__(self, gateway, analog_data: Dict[str, Any]):
        """Inizializza un ingresso analogico."""
        self._gateway = gateway
        self._act_id = analog_data.get("act_id")
        self._name = analog_data.get("name", f"Analog Input {self._act_id}")
        self._value = analog_data.get("value", 0)
        self._unit = analog_data.get("unit", "")
        self._cmd_name = analog_data.get("cmd_name")
        
        if self._act_id:
            _ANALOGICS[self._act_id] = self
        
        _LOGGER.debug("ANALOG IN created: %s (ID: %d) - value: %s %s", 
                     self._name, self._act_id, self._value, self._unit)

    @property
    def act_id(self) -> Optional[int]:
        return self._act_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"sensor.domo_analog_{self._act_id}"

    @property
    def value(self) -> int:
        """Restituisce il valore corrente (0-100)."""
        return self._value

    @property
    def unit(self) -> str:
        """Restituisce l'unità di misura."""
        return self._unit

    @property
    def percentage(self) -> float:
        """Restituisce il valore percentuale (0-100%)."""
        return float(self._value)

    def update_state(self, data: Dict[str, Any]) -> bool:
        """Aggiorna lo stato dell'ingresso analogico."""
        if data.get("act_id") != self._act_id:
            return False
        
        old_value = self._value
        old_unit = self._unit
        
        if "value" in data:
            self._value = data["value"]
        if "unit" in data:
            self._unit = data["unit"]
        
        if old_value != self._value or old_unit != self._unit:
            _LOGGER.debug("ANALOG IN %s (ID: %d) - cambiato: %s%s -> %s%s", 
                         self._name, self._act_id, old_value, old_unit, 
                         self._value, self._unit)
        return True


async def discover_analogics(gateway):
    """Scopri tutti gli ingressi analogici disponibili."""
    _LOGGER.debug("Discovering analog inputs")
    
    try:
        # Richiedi la lista degli ingressi analogici
        resp = await gateway.tx_command({
            "cmd_name": "analogin_list_req",
            "topologic_scope": "plant"
        }, resp_command="analogin_list_resp")
        
        if not resp:
            _LOGGER.debug("No analog inputs found or response empty")
            return []
        
        analogics = []
        for item in resp.get("array", []):
            if item.get("leaf", True):
                analog_in = DomoAnalogIn(gateway, item)
                analogics.append(analog_in)
        
        _LOGGER.debug("Discovered %d analog inputs", len(analogics))
        return analogics
        
    except Exception as err:
        _LOGGER.error("Analog inputs discovery failed: %s", err)
        return []


def get_all_analogics() -> List[DomoAnalogIn]:
    """Restituisce tutti gli ingressi analogici."""
    return list(_ANALOGICS.values())


def get_analogic(act_id: int) -> Optional[DomoAnalogIn]:
    """Restituisce un ingresso analogico per ID."""
    return _ANALOGICS.get(act_id)


def handle_analogic_status_update(gateway, device_info):
    """Gestisce aggiornamenti di stato degli ingressi analogici."""
    act_id = device_info.get("act_id")
    if not act_id:
        return
    
    analogic = _ANALOGICS.get(act_id)
    if analogic:
        analogic.update_state(device_info)
        
        _LOGGER.debug("📊 ANALOG IN - act_id: %s, value: %s %s", 
                     act_id, device_info.get("value"), device_info.get("unit"))        
        
        if gateway and gateway.hass:
            async_dispatcher_send(
                gateway.hass,
                SIGNAL_UPDATE_ENTITY,
                analogic.unique_id
            )
