"""
platforms/digital_in.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_STATE_OFF = 0
BINARY_SENSOR_STATE_ON = 1

_DIGITAL_INS: dict[int, DomoDigitalIn] = {}


class DomoDigitalIn:
    """Ingresso digitale ETI Domo."""

    def __init__(self, gateway, digital_in_data: Dict[str, Any]):
        self._gateway = gateway
        self._act_id = digital_in_data["act_id"]
        self._name = digital_in_data.get("name", f"Digital {self._act_id}")
        self._state = digital_in_data.get("status", 1)
        
        _DIGITAL_INS[self._act_id] = self
        
        _LOGGER.debug("DIGITAL_IN created: %s (ID: %d) - stato: %s", 
             self._name, self._act_id, self._state)
    @property
    def act_id(self) -> int:
        return self._act_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"binary_sensor.domo_{self._act_id}"

    @property
    def is_on(self) -> bool:
        return self._state == BINARY_SENSOR_STATE_OFF

    def update_state(self, data: Dict[str, Any]) -> bool:
        if data.get("act_id") != self._act_id:
            return False
        if "status" in data:
            self._state = data["status"]
        return True


async def discover_digital_ins(gateway):
    """Scopri tutti gli ingressi digitali disponibili."""
    _LOGGER.debug("Discovering digital inputs")
    
    try:
        resp = await gateway.tx_command({
            "cmd_name": "digitalin_list_req",
            "topologic_scope": "plant"
        }, resp_command="digitalin_list_resp")
        
        if not resp:
            _LOGGER.error("No response from gateway")
            return []
        
        digital_ins = []
        for item in resp.get("array", []):
            if item.get("leaf", True):
                digital_in = DomoDigitalIn(gateway, item)
                digital_ins.append(digital_in)
        
        _LOGGER.debug("Discovered %d digital inputs", len(digital_ins))
        return digital_ins
        
    except Exception as err:
        _LOGGER.error("Digital inputs discovery failed: %s", err)
        return []


def get_all_digital_ins() -> List[DomoDigitalIn]:
    """Restituisce tutti gli ingressi digitali."""
    return list(_DIGITAL_INS.values())


def handle_digital_in_status_update(gateway, device_info):
    """Gestisce aggiornamenti di stato."""
    act_id = device_info.get("act_id")
    if not act_id:
        return
    
    digital_in = _DIGITAL_INS.get(act_id)
    if digital_in:
        digital_in.update_state(device_info)
        
        _LOGGER.debug(" ⓿/❶ DIGITAL_IN - act_id: %s, stato completo: %s", 
                     act_id, device_info)        
        
        if gateway and gateway.hass:
            async_dispatcher_send(
                gateway.hass,
                SIGNAL_UPDATE_ENTITY,
                digital_in.unique_id
            )
