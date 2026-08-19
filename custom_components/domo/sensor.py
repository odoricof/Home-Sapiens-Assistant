"""
domo/sensor.py

Entities fed by:
- platforms/meters.py
- platforms/loadsctrl.py
- platforms/analogics.py
- platforms/sicu.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues

status: passed
"""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.analogics import DomoAnalogIn, get_all_analogics
from .platforms.loadsctrl import DomoLoadCtrlMeter, get_all_loadsctrl_meters
from .platforms.meters import DomoMeter, get_all_meters
from .platforms.sicu import (
    AREA_STATUS_MAP,
    INPUT_STATUS_MAP,
    get_security_device,
)

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensor platform for meters, load control, analog inputs and security."""

    meters = get_all_meters()
    analogics = get_all_analogics()
    security = get_security_device()
    loadsctrl_meters = get_all_loadsctrl_meters()

    entities = []

    # --- Energy meters ---
    for meter in meters:
        entities.append(DomoPowerSensor(meter, entry.entry_id))
        entities.append(DomoEnergySensor(meter, entry.entry_id))

    # --- Load control ---
    if loadsctrl_meters:
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, "loadsctrl_root")},
            name="Controlled loads",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )
        parent_device_info = DeviceInfo(
            identifiers={(DOMAIN, "loadsctrl_root")},
            name="Controlled loads",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

        for loadsctrl_meter in loadsctrl_meters:
            entities.append(DomoLoadCtrlPowerSensor(loadsctrl_meter, parent_device_info))
            _LOGGER.info("Added sensor for loadsctrl meter: %s (ID: %s)", loadsctrl_meter.name, loadsctrl_meter.meter_id)

    # --- Analog inputs ---
    if analogics:
        analog_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_analogics")},
            name="Analogic Inputs",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

        for analog_in in analogics:
            entities.append(DomoAnalogSensor(analog_in, analog_device_info, entry.entry_id))
        _LOGGER.debug("Added %d analog sensor entities", len(analogics))

    # --- Security inputs ---
    if security and hasattr(security, "_inputs") and security._inputs:
        security_inputs_device_info = DeviceInfo(
            identifiers={(DOMAIN, "burglar_alarm_inputs")},
            name="Security Inputs",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
            via_device=(DOMAIN, "burglar_alarm"),
        )

        for inp in security._inputs:
            input_id = inp.get("input_id")
            input_name = inp.get("name", f"Sensore {input_id}")
            entities.append(SecurityInputSensor(security, input_id, input_name, security_inputs_device_info))
            _LOGGER.info("Added sensor for security input: %s (ID: %s)", input_name, input_id)

    # --- Security areas ---
    if security and hasattr(security, "_areas") and security._areas:
        security_areas_device_info = DeviceInfo(
            identifiers={(DOMAIN, "burglar_alarm_areas")},
            name="Security Areas",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
            via_device=(DOMAIN, "burglar_alarm"),
        )

        for area in security._areas:
            area_id = area.get("area_id")
            area_name = area.get("name", f"Area {area_id}")
            entities.append(SecurityAreaSensor(security, area_id, area_name, security_areas_device_info))
            _LOGGER.info("Added sensor for security area: %s (ID: %s)", area_name, area_id)

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Added %d total sensor entities (meters + loadsctrl + analogics + security inputs + security areas)", len(entities))
    else:
        _LOGGER.debug("No sensors found to setup")


# ============================================================
# ===== ENERGY SENSORS =====
# ============================================================

class DomoPowerSensor(SensorEntity):
    """Instant power sensor."""

    _attr_should_poll = False
    _attr_entity_registry_visible_default = True
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, meter: DomoMeter, entry_id: str):
        self._meter = meter
        self._attr_unique_id = meter.unique_id_power
        self._attr_name = f"{meter.name} Potenza"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_sensors")},
            name="Energy Sensors",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

        if meter.is_production:
            self._attr_icon = "mdi:solar-power"
        else:
            self._attr_icon = "mdi:lightning-bolt"

        _LOGGER.debug("Power sensor created: %s", self._attr_name)

    @property
    def native_value(self):
        """Return the instant power."""
        return self._meter.instant_power

    @property
    def extra_state_attributes(self):
        """Additional attributes."""
        return {
            "meter_id": self._meter.meter_id,
            "meter_type": "production" if self._meter.is_production else "consumption",
            "last_month_avg": self._meter.last_month_avg,
            "energy_unit": self._meter.energy_unit,
        }

    async def async_added_to_hass(self):
        """Register for updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle updates."""
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


class DomoEnergySensor(SensorEntity):
    """Incremental energy sensor (consumption/production)."""

    _attr_should_poll = False
    _attr_entity_registry_visible_default = True
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, meter: DomoMeter, entry_id: str):
        self._meter = meter
        self._attr_unique_id = meter.unique_id_energy

        type_str = "Produzione" if meter.is_production else "Consumo"
        self._attr_name = f"{meter.name} {type_str}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_sensors")},
            name="Energy Sensors",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

        if meter.is_production:
            self._attr_icon = "mdi:solar-panel"
        else:
            self._attr_icon = "mdi:home-lightning-bolt-outline"

        _LOGGER.debug("Energy sensor created: %s", self._attr_name)

    @property
    def native_value(self):
        """Return the incremental value (last_24h_avg)."""
        return self._meter.last_24h_avg / 1000

    @property
    def extra_state_attributes(self):
        """Additional attributes."""
        return {
            "meter_id": self._meter.meter_id,
            "meter_type": "production" if self._meter.is_production else "consumption",
            "instant_power": self._meter.instant_power,
            "last_month_avg": self._meter.last_month_avg,
            "unit_of_measurement_original": self._meter.energy_unit,
        }

    async def async_added_to_hass(self):
        """Register for updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle updates."""
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


# ============================================================
# ===== LOAD CONTROL =====
# ============================================================

class DomoLoadCtrlPowerSensor(SensorEntity):
    """Instant power sensor for the power source (load control)."""

    _attr_should_poll = False
    _attr_entity_registry_visible_default = True
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:connection"

    def __init__(self, meter: DomoLoadCtrlMeter, device_info: DeviceInfo):
        self._meter = meter
        self._attr_unique_id = f"{meter.unique_id}_power"
        self._attr_name = meter.name
        self._attr_device_info = device_info

        _LOGGER.debug("Load control power sensor created: %s", self._attr_name)

    @property
    def native_value(self):
        """Return the instant power."""
        return self._meter.power

    @property
    def extra_state_attributes(self):
        """Additional attributes."""
        return {
            "max_power": self._meter.max_power,
            "hysteresis": self._meter.hysteresis,
            "energy_meter_id": self._meter.energy_meter_id,
            "load_count": len(self._meter.relays),
        }

    async def async_added_to_hass(self):
        """Register for updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle updates."""
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


# ============================================================
# ===== ANALOG SENSORS =====
# ============================================================

class DomoAnalogSensor(SensorEntity):
    """Sensor for ETI Domo analog inputs."""

    _attr_should_poll = False
    _attr_suggested_display_precision = 0
    _attr_device_class = None

    def __init__(self, analog_in: DomoAnalogIn, device_info: DeviceInfo, entry_id: str):
        self._analog_in = analog_in
        self._attr_unique_id = analog_in.unique_id
        self._attr_name = analog_in.name
        self._attr_device_info = device_info

        if analog_in.unit and analog_in.unit.strip():
            self._attr_native_unit_of_measurement = analog_in.unit
        else:
            self._attr_native_unit_of_measurement = None

        self._attr_icon = self._get_icon_for_unit(analog_in.unit)

        _LOGGER.debug("Analog sensor created: %s (ID: %d) - unit: %s, icon: %s",
                     self._attr_name, analog_in.act_id, self._attr_native_unit_of_measurement, self._attr_icon)

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

    def _get_icon_for_unit(self, unit: str) -> str:
        """Return the appropriate icon based on the unit of measurement."""
        if not unit:
            return "mdi:gauge"

        unit_lower = unit.lower()

        if unit_lower in ["°c", "c", "celsius", "°f", "f", "fahrenheit"]:
            return "mdi:thermometer"

        if unit_lower in ["%", "percent", "humidity"]:
            return "mdi:water-percent"

        if unit_lower in ["v", "volt", "mv", "millivolt"]:
            return "mdi:flash"

        if unit_lower in ["a", "ampere", "ma", "milliampere"]:
            return "mdi:current-ac"

        if unit_lower in ["bar", "psi", "kpa", "pa", "hpa"]:
            return "mdi:gauge"

        if unit_lower in ["m/s", "km/h", "mph", "knot"]:
            return "mdi:speedometer"

        if unit_lower in ["lux", "lm", "lumen"]:
            return "mdi:brightness-5"

        if unit_lower in ["db", "decibel"]:
            return "mdi:volume-high"

        if unit_lower in ["ppm", "co2"]:
            return "mdi:molecule-co2"

        if unit_lower in ["hz", "khz", "mhz"]:
            return "mdi:sine-wave"

        if unit_lower in ["°", "deg", "degree", "rad"]:
            return "mdi:rotate-3d"

        return "mdi:gauge"

    async def async_added_to_hass(self):
        """Register for updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle updates."""
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


# ============================================================
# ===== SECURITY INPUTS =====
# ============================================================

class SecurityInputSensor(SensorEntity):
    """Sensor for a security panel input."""

    _attr_should_poll = False

    def __init__(self, security, input_id: int, name: str, device_info: DeviceInfo):
        self._security = security
        self._input_id = input_id
        self._attr_unique_id = f"{security.unique_id}_input_{input_id}"
        self._attr_name = f"Security {name}"
        self._attr_device_info = device_info

        self._state = "Sconosciuto"
        self._raw_status = None
        self._areas = []

        for inp in security._inputs:
            if inp.get("input_id") == input_id:
                raw_status = inp.get("status")
                self._raw_status = raw_status
                self._state = INPUT_STATUS_MAP.get(raw_status, f"Sconosciuto ({raw_status})")
                self._areas = inp.get("areas", [])
                break

        _LOGGER.debug("Security input %s initial state: %s", name, self._state)

    @property
    def icon(self) -> str:
        """Icon based on the state."""
        if self._state == "Allarme":
            return "mdi:alarm-light"
        if self._state == "Aperto":
            return "mdi:lock-open-variant"
        if self._state == "Chiuso":
            return "mdi:lock"
        if self._state == "Escluso":
            return "mdi:shield-off"
        if self._state == "Memoria allarme":
            return "mdi:bell-alert"
        if self._state == "Batteria scarica":
            return "mdi:battery-low"
        return "mdi:sensor"

    @property
    def native_value(self) -> str:
        """Return the textual state of the sensor."""
        return self._state or "Sconosciuto"

    @property
    def extra_state_attributes(self) -> dict:
        """Additional attributes."""
        return {
            "raw_status": self._raw_status,
            "areas": self._areas,
        }

    def _refresh_from_snapshot(self) -> bool:
        """Update the state from the last received snapshot, return True if found."""
        snapshot = getattr(self._security, "_last_snapshot", None)
        if not snapshot:
            return False
        for inp in snapshot.get("inputs", []):
            if inp.get("input_id") == self._input_id:
                raw_status = inp.get("status")
                self._raw_status = raw_status
                self._state = INPUT_STATUS_MAP.get(raw_status, f"Sconosciuto ({raw_status})")
                self._areas = inp.get("areas", [])
                return True
        return False

    async def async_added_to_hass(self):
        """Register for updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle updates."""
        if entity_id and entity_id != self._attr_unique_id:
            return
        if self._refresh_from_snapshot():
            self.async_write_ha_state()


# ============================================================
# ===== SECURITY AREAS =====
# ============================================================

class SecurityAreaSensor(SensorEntity):
    """Sensor for a security panel area."""

    _attr_should_poll = False

    def __init__(self, security, area_id: int, name: str, device_info: DeviceInfo):
        self._security = security
        self._area_id = area_id
        self._attr_unique_id = f"{security.unique_id}_area_{area_id}"
        self._attr_name = f"Security {name}"
        self._attr_device_info = device_info
        self._state = "Sconosciuto"
        self._raw_status = None

        for area in security._areas:
            if area.get("area_id") == area_id:
                raw_status = area.get("status")
                self._raw_status = raw_status
                self._state = AREA_STATUS_MAP.get(raw_status, f"Sconosciuto ({raw_status})")
                break

        _LOGGER.debug("Security area %s initial state: %s", name, self._state)

    @property
    def icon(self) -> str:
        """Icon based on the state."""
        if self._state == "Inserita":
            return "mdi:shield-check"
        if self._state == "Inserimento in corso":
            return "mdi:shield-sync"
        if self._state == "Allarme intrusione in corso":
            return "mdi:alarm-light"
        if self._state == "Memoria allarme":
            return "mdi:bell-alert"
        if self._state == "Pronta con ingressi chiusi":
            return "mdi:shield-lock"
        if "Non pronta" in self._state:
            return "mdi:shield-lock-open"
        return "mdi:shield"

    @property
    def native_value(self) -> str:
        """Return the textual state of the area."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict:
        """Additional attributes."""
        return {
            "raw_status": self._raw_status,
            "area_id": self._area_id,
        }

    def _refresh_from_snapshot(self) -> bool:
        """Update the state from the last received snapshot, return True if found."""
        snapshot = getattr(self._security, "_last_snapshot", None)
        if not snapshot:
            return False
        for area in snapshot.get("areas", []):
            if area.get("area_id") == self._area_id:
                raw_status = area.get("status")
                self._raw_status = raw_status
                self._state = AREA_STATUS_MAP.get(raw_status, f"Sconosciuto ({raw_status})")
                return True
        return False

    async def async_added_to_hass(self):
        """Register for updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle updates."""
        if entity_id and entity_id != self._attr_unique_id:
            return
        if self._refresh_from_snapshot():
            self.async_write_ha_state()
