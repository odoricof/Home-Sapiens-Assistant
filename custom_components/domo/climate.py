"""
domo/climate.py

Entities fed by:
- platforms/thermoregulation.py

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
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.thermoregulation import (
    current_weekday_name,
    DomoThermostat,
    get_all_thermostats,
)

_LOGGER = logging.getLogger(__name__)


FAN_MODES = ["auto", "low", "medium", "high"]
PRESET_JOLLY = "Jolly"


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the climate platform."""
    thermostats = get_all_thermostats()

    if not thermostats:
        _LOGGER.debug("No thermostats found yet")
        return

    entities = []
    for thermostat in thermostats:
        if thermostat.support_fan:
            _LOGGER.info("Fan coil detected: %s -> DomoFancoilClimateEntity entity", thermostat.name)
            entities.append(DomoFancoilClimateEntity(hass, thermostat, entry.entry_id))
        else:
            _LOGGER.info("Thermostat detected: %s -> DomoClimateEntity entity", thermostat.name)
            entities.append(DomoClimateEntity(hass, thermostat, entry.entry_id))

    async_add_entities(entities, update_before_add=True)

    _LOGGER.info("Added %d climate entities", len(entities))


# ============================================================
# ===== CLIMATE ENTITY =====
# ============================================================

class DomoClimateEntity(ClimateEntity):
    """Base climate entity for ETI Domo thermostats."""

    def __init__(self, hass, thermostat: DomoThermostat, entry_id: str):
        """Initialize the climate entity."""
        self.hass = hass
        self._thermostat = thermostat

        self._attr_unique_id = thermostat.unique_id
        self._attr_name = thermostat.name
        self._attr_should_poll = False

        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 0.1
        self._attr_precision = 0.1

        self._attr_min_temp = 5.0
        self._attr_max_temp = 35.0

        self._attr_supported_features = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.PRESET_MODE
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate_{thermostat.unique_id}")},
            name=thermostat.name,
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
            via_device=(DOMAIN, f"{entry_id}_climate"),
        )

        _LOGGER.debug("Created climate entity: %s in room %s", self._attr_name, thermostat.room)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the supported features."""
        features = self._attr_supported_features

        if self._thermostat.season == "plant_off":
            return features & ~ClimateEntityFeature.PRESET_MODE & ~ClimateEntityFeature.FAN_MODE

        if self.hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        elif self.hvac_mode == HVACMode.AUTO and self._thermostat.scheduled_setpoint is not None:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        elif self.hvac_mode == HVACMode.OFF and self._thermostat.season == "winter" and self._thermostat.antifreeze is not None:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE

        return features

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._thermostat.current_temperature

    @property
    def current_humidity(self) -> float | None:
        """Return the current humidity."""
        return self._thermostat.current_humidity

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if self.hvac_mode == HVACMode.AUTO:
            return self._thermostat.scheduled_setpoint
        if self.hvac_mode == HVACMode.OFF and self._thermostat.season == "winter":
            return self._thermostat.antifreeze
        return self._thermostat.target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if self._thermostat.season == "plant_off":
            return HVACMode.OFF

        eti_mode = self._thermostat.hvac_mode
        if eti_mode == "off":
            return HVACMode.OFF
        if eti_mode == "manual":
            if self._thermostat.season == "winter":
                return HVACMode.HEAT
            if self._thermostat.season == "summer":
                return HVACMode.COOL
            return HVACMode.HEAT
        if eti_mode == "auto":
            return HVACMode.AUTO
        return HVACMode.AUTO

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        action = self._thermostat.hvac_action
        if action == "heating":
            return HVACAction.HEATING
        if action == "cooling":
            return HVACAction.COOLING
        if action == "idle":
            return HVACAction.IDLE
        return HVACAction.OFF

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available HVAC modes."""
        modes = [HVACMode.OFF]

        if self._thermostat.season == "plant_off":
            return modes

        if self._thermostat.season == "winter":
            modes.extend([HVACMode.HEAT, HVACMode.AUTO])
        elif self._thermostat.season == "summer":
            modes.extend([HVACMode.COOL, HVACMode.AUTO])
        else:
            modes.append(HVACMode.AUTO)

        return modes

    @property
    def preset_modes(self) -> list[str]:
        """Return the list of available preset modes."""
        if self._thermostat.season == "plant_off":
            return []
        return [current_weekday_name(), PRESET_JOLLY]

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        if self._thermostat.season == "plant_off":
            return None
        if self._thermostat.hvac_mode == "jolly":
            return PRESET_JOLLY
        return current_weekday_name()

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
            "thermal_profile_schedule": self._thermostat.thermal_profile_schedule,
            "scheduled_setpoint": self._thermostat.scheduled_setpoint,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the new HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self._thermostat.async_set_hvac_mode("off")
        elif hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
            await self._thermostat.async_set_hvac_mode("manual")
        else:
            await self._thermostat.async_set_hvac_mode("auto")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Enable or disable the Jolly profile."""
        if preset_mode == PRESET_JOLLY:
            await self._thermostat.async_set_hvac_mode("jolly")
        else:
            await self._thermostat.async_set_hvac_mode("auto")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the new target temperature."""
        if ATTR_TEMPERATURE not in kwargs:
            return

        temperature = kwargs[ATTR_TEMPERATURE]
        _LOGGER.debug("Setting temperature to %.1f°C", temperature)

        if self.hvac_mode in (HVACMode.AUTO, HVACMode.OFF):
            await self._thermostat.async_set_manual_temperature(temperature)
            return

        await self._thermostat.async_set_temperature(temperature)

    async def async_added_to_hass(self) -> None:
        """Run when the entity is added to Home Assistant."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str | None = None) -> None:
        """Handle an update from the dispatcher."""
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()


# ============================================================
# ===== FANCOIL ENTITY =====
# ============================================================

class DomoFancoilClimateEntity(DomoClimateEntity):
    """Climate entity for ETI Domo fan coil units."""

    def __init__(self, hass, thermostat: DomoThermostat, entry_id: str):
        """Initialize the fan coil climate entity."""
        super().__init__(hass, thermostat, entry_id)

        self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
        self._attr_fan_modes = FAN_MODES

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the supported features."""
        features = super().supported_features
        if self.hvac_mode != HVACMode.OFF:
            features |= ClimateEntityFeature.FAN_MODE
        return features

    @property
    def fan_mode(self) -> str | None:
        """Return the fan speed setting."""
        if self.hvac_mode == HVACMode.OFF:
            return None
        return self._thermostat.fan_mode

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the new fan mode."""
        if self.hvac_mode == HVACMode.OFF:
            return
        if fan_mode not in FAN_MODES:
            return
        await self._thermostat.async_set_fan_mode(fan_mode)
