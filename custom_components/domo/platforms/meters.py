"""
platforms/meters.py

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

METER_TYPE_CONSUMPTION = 0  
METER_TYPE_PRODUCTION = 1   

_METERS: dict[int, DomoMeter] = {}


class DomoMeter:
    """Misuratore di energia ETI Domo."""

    def __init__(self, gateway, meter_data: Dict[str, Any]):
        self._gateway = gateway
        self._meter_id = meter_data["id"]
        self._name = meter_data.get("name", f"Meter {self._meter_id}")
        self._meter_type = meter_data.get("meter_type", 1)
        self._produced = meter_data.get("produced", 0)
        self._instant_power = meter_data.get("instant_power", 0)
        self._last_24h_avg = meter_data.get("last_24h_avg", 0)
        self._last_month_avg = meter_data.get("last_month_avg", 0)
        self._unit = meter_data.get("unit", "W")
        self._energy_unit = meter_data.get("energy_unit", "Wh")
        
        _METERS[self._meter_id] = self
        
        _LOGGER.debug(
            "METER created: %s (ID: %d) - Type: %s, Produced: %s",
            self._name, self._meter_id,
            "Production" if self._produced == 1 else "Consumption",
            self._produced
        )

    @property
    def meter_id(self) -> int:
        return self._meter_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id_power(self) -> str:
        """Unique ID per il sensore di potenza istantanea."""
        return f"sensor.domo_{self._meter_id}_power"

    @property
    def unique_id_energy(self) -> str:
        """Unique ID per il sensore di energia (consumo/produzione)."""
        suffix = "production" if self._produced == 1 else "consumption"
        return f"sensor.domo_{self._meter_id}_{suffix}"

    @property
    def instant_power(self) -> float:
        """Potenza istantanea in Watt."""
        return self._instant_power

    @property
    def last_24h_avg(self) -> float:
        """Consumo/produzione delle ultime 24 ore."""
        return self._last_24h_avg

    @property
    def last_month_avg(self) -> float:
        """Consumo/produzione dell'ultimo mese."""
        return self._last_month_avg

    @property
    def is_production(self) -> bool:
        """True se è un meter di produzione, False se è di consumo."""
        return self._produced == 1

    @property
    def unit(self) -> str:
        return self._unit

    @property
    def energy_unit(self) -> str:
        return self._energy_unit

    def update_state(self, data: Dict[str, Any]) -> bool:
        """Aggiorna lo stato del meter con nuovi dati."""
        if data.get("id") != self._meter_id:
            return False
        
        if "instant_power" in data:
            self._instant_power = data["instant_power"]
        if "last_24h_avg" in data:
            self._last_24h_avg = data["last_24h_avg"]
        if "last_month_avg" in data:
            self._last_month_avg = data["last_month_avg"]
        if "produced" in data:
            # Aggiorna il flag produced nel caso cambi
            old_produced = self._produced
            self._produced = data["produced"]
            if old_produced != self._produced:
                _LOGGER.info(
                    "Meter %d changed type: %s -> %s",
                    self._meter_id,
                    "Consumption" if old_produced == 0 else "Production",
                    "Consumption" if self._produced == 0 else "Production"
                )
        
        return True


async def discover_meters(gateway):
    """Scopri tutti i misuratori di energia disponibili."""
    _LOGGER.debug("Discovering energy meters")
    
    try:
        # Richiedi la lista dei meter
        resp = await gateway.tx_command({
            "cmd_name": "meters_list_req",
            "topologic_scope": "plant"
        }, resp_command="meters_list_resp")
        
        if not resp:
            _LOGGER.error("No response from gateway for meter list")
            return []
        
        meters = []
        for item in resp.get("array", []):
            if item.get("leaf", True):
                meter = DomoMeter(gateway, item)
                meters.append(meter)
        
        _LOGGER.debug("Discovered %d energy meters", len(meters))
        return meters
        
    except Exception as err:
        _LOGGER.error("Energy meters discovery failed: %s", err)
        return []


def get_all_meters() -> List[DomoMeter]:
    """Restituisce tutti i misuratori."""
    return list(_METERS.values())


def get_meter_by_id(meter_id: int) -> DomoMeter | None:
    """Restituisce un meter specifico per ID."""
    return _METERS.get(meter_id)


def handle_meter_status_update(gateway, device_info):
    """Gestisce aggiornamenti di stato dei meter."""
    meter_id = device_info.get("id")
    if not meter_id:
        return
    
    meter = _METERS.get(meter_id)
    if meter:
        meter.update_state(device_info)
        
        if gateway and gateway.hass:
            # Invia update per entrambi i sensori associati a questo meter
            async_dispatcher_send(
                gateway.hass,
                SIGNAL_UPDATE_ENTITY,
                meter.unique_id_power
            )
            async_dispatcher_send(
                gateway.hass,
                SIGNAL_UPDATE_ENTITY,
                meter.unique_id_energy
            )
