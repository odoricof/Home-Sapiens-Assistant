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
from .platforms.analogics import DomoAnalogIn, get_all_analogics
from .platforms.meters import DomoMeter
from .platforms.meters import get_all_meters

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensor platform"""
    
    meters = get_all_meters()
    analogics = get_all_analogics()
    
    entities = []
    
    # Sensori per i misuratori di energia
    for meter in meters:
        # Crea due entità per ogni meter: potenza istantanea e energia incrementale
        entities.append(DomoPowerSensor(meter, entry.entry_id))
        entities.append(DomoEnergySensor(meter, entry.entry_id))
    
    # Sensori per gli ingressi analogici
    if analogics:
        analog_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_analogics")},
            name="Analogic Inputs",
            manufacturer="Home Sapiens Assistant",
            model="Eti/domo",
        )
        
        for analog_in in analogics:
            entities.append(DomoAnalogSensor(analog_in, analog_device_info, entry.entry_id))
        _LOGGER.debug("Added %d analog sensor entities", len(analogics))
    
    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Added %d total sensor entities (meters + analogics)", len(entities))
    else:
        _LOGGER.debug("No sensors found to setup")


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
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
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

class DomoAnalogSensor(SensorEntity):
    """Sensore per ingressi analogici ETI Domo."""

    def __init__(self, analog_in: DomoAnalogIn, device_info: DeviceInfo, entry_id: str):
        """Initialize the analog sensor."""
        self._analog_in = analog_in
        self._attr_unique_id = analog_in.unique_id
        self._attr_name = analog_in.name
        self._attr_should_poll = False
        self._attr_device_info = device_info
        
        # Imposta l'unità di misura SOLO se non è vuota
        if analog_in.unit and analog_in.unit.strip():
            self._attr_native_unit_of_measurement = analog_in.unit
        else:
            self._attr_native_unit_of_measurement = None  # Nessuna unità
        
        self._attr_suggested_display_precision = 0
        
        # Imposta l'icona in base all'unità di misura
        self._attr_icon = self._get_icon_for_unit(analog_in.unit)
        
        # Device class per sensori analogici (opzionale)
        self._attr_device_class = None  # Generico, non c'è una classe specifica
        
        _LOGGER.debug("Created analog sensor: %s (ID: %d) - unit: %s, icon: %s", 
                     self._attr_name, analog_in.act_id, self._attr_native_unit_of_measurement, self._attr_icon)

    def _get_icon_for_unit(self, unit: str) -> str:
        """Restituisce l'icona appropriata in base all'unità di misura."""
        if not unit:
            return "mdi:gauge"  # Icona generica per numero puro
        
        unit_lower = unit.lower()
        
        # Temperatura
        if unit_lower in ["°c", "c", "celsius", "°f", "f", "fahrenheit"]:
            return "mdi:thermometer"
        
        # Umidità
        if unit_lower in ["%", "percent", "humidity"]:
            return "mdi:water-percent"
        
        # Tensione
        if unit_lower in ["v", "volt", "mv", "millivolt"]:
            return "mdi:flash"
        
        # Corrente
        if unit_lower in ["a", "ampere", "ma", "milliampere"]:
            return "mdi:current-ac"
        
        # Pressione
        if unit_lower in ["bar", "psi", "kpa", "pa", "hpa"]:
            return "mdi:gauge"
        
        # Velocità
        if unit_lower in ["m/s", "km/h", "mph", "knot"]:
            return "mdi:speedometer"
        
        # Luminosità
        if unit_lower in ["lux", "lm", "lumen"]:
            return "mdi:brightness-5"
        
        # Suono
        if unit_lower in ["db", "decibel"]:
            return "mdi:volume-high"
        
        # CO2 / qualità aria
        if unit_lower in ["ppm", "co2"]:
            return "mdi:molecule-co2"
        
        # Frequenza
        if unit_lower in ["hz", "khz", "mhz"]:
            return "mdi:sine-wave"
        
        # Angolo
        if unit_lower in ["°", "deg", "degree", "rad"]:
            return "mdi:rotate-3d"
        
        # Icona generica per unità sconosciuta
        return "mdi:gauge"

    @property
    def native_value(self) -> int | float | None:
        """Return the current value."""
        return self._analog_in.value

    @property
    def extra_state_attributes(self) -> dict:
        """Additional attributes."""
        return {
            "act_id": self._analog_in.act_id,
            "percentage": self._analog_in.percentage,
            "unit_raw": self._analog_in.unit,
        }

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle update from bus."""
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()
