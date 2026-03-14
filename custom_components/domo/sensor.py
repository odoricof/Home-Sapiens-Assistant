"""
domo/sensor.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import callback

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.meters import DomoMeter

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensor platform per i misuratori di energia."""
    from .platforms.meters import get_all_meters
    
    meters = get_all_meters()
    if not meters:
        _LOGGER.debug("No meters found to setup")
        return
    
    entities = []
    for meter in meters:
        # Crea due entità per ogni meter: potenza istantanea e energia incrementale
        entities.append(DomoPowerSensor(meter, entry.entry_id))
        entities.append(DomoEnergySensor(meter, entry.entry_id))
    
    async_add_entities(entities)
    _LOGGER.debug("Added %d sensor entities for energy meters", len(entities))


class DomoPowerSensor(SensorEntity):
    """Sensore di potenza istantanea."""

    def __init__(self, meter: DomoMeter, entry_id: str): 
        self._meter = meter
        self._attr_unique_id = meter.unique_id_power
        self._attr_name = f"{meter.name} Potenza"
        self._attr_should_poll = False
        self._attr_entity_registry_visible_default = True
        
        # Configurazione device class
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        
        # DEVICE INFO
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_sensors")},
            name="Sensors",
            manufacturer="Home Sapiens",
            model=" ",
        )        
        
        
        
        # Icona appropriata in base al tipo
        if meter.is_production:
            self._attr_icon = "mdi:solar-power"
        else:
            self._attr_icon = "mdi:lightning-bolt"
        
        _LOGGER.debug("Created power sensor: %s", self._attr_name)

    @property
    def native_value(self):
        """Restituisce la potenza istantanea."""
        return self._meter.instant_power

    @property
    def extra_state_attributes(self):
        """Attributi aggiuntivi."""
        return {
            "meter_id": self._meter.meter_id,
            "meter_type": "production" if self._meter.is_production else "consumption",
            "last_month_avg": self._meter.last_month_avg,
            "energy_unit": self._meter.energy_unit,
        }

    async def async_added_to_hass(self):
        """Registra per gli aggiornamenti."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Gestisce aggiornamenti."""
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


class DomoEnergySensor(SensorEntity):
    """Sensore di energia incrementale (consumo/produzione)."""

    def __init__(self, meter: DomoMeter, entry_id: str):
        self._meter = meter
        
        # Unique ID diverso per consumo e produzione
        self._attr_unique_id = meter.unique_id_energy
        
        # Nome appropriato
        type_str = "Produzione" if meter.is_production else "Consumo"
        self._attr_name = f"{meter.name} {type_str}"
        
        self._attr_should_poll = False
        self._attr_entity_registry_visible_default = True
        
        # Configurazione device class
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        
        # DEVICE INFO
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_sensors")},
            name="Sensors",
            manufacturer="Home Sapiens",
            model=" ",
        )        
        
        # Icona appropriata
        if meter.is_production:
            self._attr_icon = "mdi:solar-panel"
        else:
            self._attr_icon = "mdi:home-lightning-bolt-outline"
        
        _LOGGER.debug("Created energy sensor: %s", self._attr_name)

    @property
    def native_value(self):
        """Restituisce il valore incrementale (last_24h_avg)."""
        return self._meter.last_24h_avg / 1000

    @property
    def extra_state_attributes(self):
        """Attributi aggiuntivi."""
        return {
            "meter_id": self._meter.meter_id,
            "meter_type": "production" if self._meter.is_production else "consumption",
            "instant_power": self._meter.instant_power,
            "last_month_avg": self._meter.last_month_avg,
            "unit_of_measurement_original": self._meter.energy_unit,
        }

    async def async_added_to_hass(self):
        """Registra per gli aggiornamenti."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Gestisce aggiornamenti."""
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()
