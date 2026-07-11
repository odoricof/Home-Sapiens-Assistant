"""
domo/climate.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations
import logging

from typing import Any, Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import callback

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.thermoregulation import DomoThermostat

_LOGGER = logging.getLogger(__name__)

# Modalità HVAC supportate
HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO, HVACMode.COOL]

# Modalità ventola supportate
FAN_MODES = ["auto", "low", "medium", "high"]


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup climate platform."""
    from .platforms.thermoregulation import get_all_thermostats
    
    thermostats = get_all_thermostats()
    
    if not thermostats:
        _LOGGER.debug("No thermostats found yet")
        return
    
    entities = []
    for thermostat in thermostats:
        if thermostat.support_fan:
            _LOGGER.info("Fan coil rilevato: %s → entità DomoFancoilClimateEntity", thermostat.name)
            entities.append(DomoFancoilClimateEntity(hass, thermostat, entry.entry_id))
        else:
            _LOGGER.info("Termostato rilevato: %s → entità DomoClimateEntity", thermostat.name)
            entities.append(DomoClimateEntity(hass, thermostat, entry.entry_id))
    
    async_add_entities(entities, update_before_add=True)
    
    _LOGGER.info("Added %d climate entities", len(entities))


class DomoClimateEntity(ClimateEntity):
    """ETI Domo climate entity base."""

    def __init__(self, hass, thermostat: DomoThermostat, entry_id: str):
        """Initialize the climate entity."""
        self.hass = hass
        self._thermostat = thermostat
        
        self._attr_unique_id = thermostat.unique_id
        self._attr_name = thermostat.name
        self._attr_should_poll = False
        
        # Unità di misura
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 0.1
        self._attr_precision = 0.1
        
        # Min e max temperature
        self._attr_min_temp = 5.0
        self._attr_max_temp = 35.0
        
        # Features base (ON/OFF sempre supportati)
        self._attr_supported_features = (
            ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        )
        
        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate")},
            name="Climate",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
            
        )
        #suggested_area=thermostat.room
        self._attr_suggested_area = thermostat.room
        
        _LOGGER.debug("Created climate entity: %s in room %s", 
                     self._attr_name, thermostat.room)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        features = self._attr_supported_features
        
        # Aggiungi TARGET_TEMPERATURE solo se in modalità HEAT o COOL
        if self.hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        elif self.hvac_mode == HVACMode.AUTO and self._thermostat.scheduled_setpoint is not None:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        elif self.hvac_mode == HVACMode.OFF and self._thermostat._season == "winter" and self._thermostat.antifreeze is not None:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
            
        return features

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        return self._thermostat.current_temperature

    @property
    def current_humidity(self) -> Optional[float]:
        """Return the current humidity."""
        return self._thermostat.current_humidity

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVACMode.AUTO:
            return self._thermostat.scheduled_setpoint
        if self.hvac_mode == HVACMode.OFF and self._thermostat._season == "winter":
            return self._thermostat.antifreeze       
        return self._thermostat.target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        eti_mode = self._thermostat.hvac_mode
        if eti_mode == "off":
            return HVACMode.OFF
        elif eti_mode == "manual":
            # In base alla stagione, manuale diventa HEAT o COOL
            if self._thermostat._season == "winter":
                return HVACMode.HEAT
            elif self._thermostat._season == "summer":
                return HVACMode.COOL
            return HVACMode.HEAT  # fallback
        elif eti_mode == "auto":
            return HVACMode.AUTO
        # JOLLY (3) non lo gestiamo, lo trattiamo come AUTO
        return HVACMode.AUTO

    @property
    def hvac_action(self) -> Optional[HVACAction]:
        """Return the current running hvac operation."""
        action = self._thermostat.hvac_action
        if action == "heating":
            return HVACAction.HEATING
        elif action == "cooling":
            return HVACAction.COOLING
        elif action == "idle":
            return HVACAction.IDLE
        return HVACAction.OFF

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available hvac operation modes."""
        modes = [HVACMode.OFF]
        
        # Determina le modalità in base alla stagione
        if self._thermostat._season == "winter":
            modes.extend([HVACMode.HEAT, HVACMode.AUTO])
        elif self._thermostat._season == "summer":
            modes.extend([HVACMode.COOL, HVACMode.AUTO])
        else:
            modes.append(HVACMode.AUTO)
            
        return modes

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "act_id": self._thermostat.act_id,
            "zone": self._thermostat.zone,
            "room": self._thermostat.room,
            "window_open": self._thermostat.is_window_open,
            "occupied": self._thermostat.is_occupied,
            "mode": self._thermostat.hvac_mode,
            "status": self._thermostat.status,
            "season": self._thermostat._season,
            #"profile_data": self._thermostat.profile_data,
            "thermal_profile_schedule": self._thermostat.thermal_profile_schedule,
            "t1": self._thermostat.t1,
            "t2": self._thermostat.t2,
            "t3": self._thermostat.t3,
            "antifreeze": self._thermostat.antifreeze,
            "scheduled_setpoint": self._thermostat.scheduled_setpoint,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        
        if hvac_mode == HVACMode.OFF:
            await self._thermostat.async_set_hvac_mode("off")
        elif hvac_mode == HVACMode.HEAT:
            await self._thermostat.async_set_hvac_mode("manual")
        elif hvac_mode == HVACMode.COOL:
            await self._thermostat.async_set_hvac_mode("manual")
        else:  # AUTO o qualsiasi altra cosa
            await self._thermostat.async_set_hvac_mode("auto")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if ATTR_TEMPERATURE not in kwargs:
            return

        temperature = kwargs[ATTR_TEMPERATURE]
        _LOGGER.debug("Setting temperature to %.1f°C", temperature)

        if self.hvac_mode in (HVACMode.AUTO, HVACMode.OFF):
            # L'utente muove il cursore mentre è in automatico o spento:
            # passa in manuale assecondando subito il valore richiesto.
            await self._thermostat.async_set_manual_temperature(temperature)
            return

        await self._thermostat.async_set_temperature(temperature)

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


class DomoFancoilClimateEntity(DomoClimateEntity):
    """ETI Domo fan coil climate entity."""

    def __init__(self, hass, thermostat: DomoThermostat, entry_id: str):
        """Initialize the fan coil climate entity."""
        super().__init__(hass, thermostat, entry_id)
        
        # Aggiungi FAN_MODE alle feature
        self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
        self._attr_fan_modes = FAN_MODES

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        features = super().supported_features
        
        # Aggiungi FAN_MODE solo se non in OFF
        if self.hvac_mode != HVACMode.OFF:
            features |= ClimateEntityFeature.FAN_MODE
            
        return features

    @property
    def fan_mode(self) -> Optional[str]:
        """Return the fan setting."""
        if self.hvac_mode == HVACMode.OFF:
            return None
        return self._thermostat.fan_mode

    @property
    def hvac_action(self) -> Optional[HVACAction]:
        """Return the current running hvac operation."""
        if self._thermostat._mode == 0:  # OFF
            return HVACAction.OFF
        if self._thermostat._status == 0:  # IDLE
            return HVACAction.IDLE
        if self._thermostat._season == "winter":
            return HVACAction.HEATING
        if self._thermostat._season == "summer":
            return HVACAction.COOLING
        return HVACAction.IDLE

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if self.hvac_mode == HVACMode.OFF:
            return
            
        if fan_mode not in FAN_MODES:
            return
            
        await self._thermostat.async_set_fan_mode(fan_mode)
