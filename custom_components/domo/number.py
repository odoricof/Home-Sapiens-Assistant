"""
domo/number.py

Entities fed by this file:
- platforms/thermoregulation.py
- platforms/irrigation.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging
from typing import Optional

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_DISCOVERY_NEW, SIGNAL_UPDATE_ENTITY
from .platforms.thermoregulation import DomoThermostat, get_all_thermostats
from .platforms.irrigation import (
    DomoIrrigationZone,
    get_all_irrigation_zones,
    async_set_irrigation_perc,
    DomoSprinkler,
    get_all_sprinklers,
    async_set_sprinkler_active,
    async_set_sprinkler_duty,
)

_LOGGER = logging.getLogger(__name__)

# attr_key -> (nome entità, icona, min, max, step, mode)
_PROFILE_ATTRS: dict[str, tuple[Optional[str], Optional[str], float, float, float, str]] = {
    "t1": ("T1", None, 5.0, 35.0, 0.1, NumberMode.BOX),
    "t2": ("T2", None, 5.0, 35.0, 0.1, NumberMode.BOX),
    "t3": ("T3", None, 5.0, 35.0, 0.1, NumberMode.BOX),
    "antifreeze": ("Antigelo", "mdi:snowflake-thermometer", 3.0, 8.0, 0.5, NumberMode.SLIDER),
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup number platform per i profili termici dei termostati, per la
    percentuale stagionale dei settori di irrigazione e per il tempo massimo
    / ciclo di lavoro dei singoli irrigatori."""

    # ----- TERMOSTATI (profili termici) -----
    thermostats = get_all_thermostats()

    if not thermostats:
        _LOGGER.debug("No thermostats found yet for number platform")
    else:
        entities = [
            DomoThermostatProfileNumber(thermostat, attr_key, entry.entry_id)
            for thermostat in thermostats
            for attr_key in _PROFILE_ATTRS
        ]
        entities.extend(
            DomoThermostatDiffNumber(thermostat, entry.entry_id)
            for thermostat in thermostats
        )

        async_add_entities(entities, update_before_add=True)
        _LOGGER.info("Added %d number entities for thermal profiles", len(entities))

    # ----- IRRIGAZIONE (percentuale stagionale) -----
    irrigation_added_ids: set[int] = set()

    def _add_irrigation_number(zone: DomoIrrigationZone):
        if zone.zone_id in irrigation_added_ids:
            return
        irrigation_added_ids.add(zone.zone_id)
        entities = [DomoIrrigationPercNumber(zone, entry.entry_id)]
        async_add_entities(entities)
        _LOGGER.info(
            "Added %d number entities for irrigation zone id=%s (%s)",
            len(entities), zone.zone_id, zone.name,
        )

    for zone in get_all_irrigation_zones():
        _add_irrigation_number(zone)

    @callback
    def _async_new_irrigation_zone(zone: DomoIrrigationZone):
        _add_irrigation_number(zone)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_DISCOVERY_NEW.format("irrigation_number"), _async_new_irrigation_zone
        )
    )

    # ----- IRRIGATORI (tempo massimo e duty cycle) -----
    sprinkler_added_ids: set[str] = set()

    def _add_sprinkler_numbers(sprinkler: DomoSprinkler):
        if sprinkler.unique_id in sprinkler_added_ids:
            return
        sprinkler_added_ids.add(sprinkler.unique_id)
        entities = [
            DomoIrrigationActiveNumber(sprinkler, entry.entry_id),
            DomoIrrigationDutyNumber(sprinkler, entry.entry_id),
        ]
        async_add_entities(entities)
        _LOGGER.info(
            "Added %d number entities for sprinkler act_id=%s (%s)",
            len(entities), sprinkler.act_id, sprinkler.name,
        )

    for sprinkler in get_all_sprinklers():
        _add_sprinkler_numbers(sprinkler)

    @callback
    def _async_new_sprinkler(sprinkler: DomoSprinkler):
        _add_sprinkler_numbers(sprinkler)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_DISCOVERY_NEW.format("number"), _async_new_sprinkler
        )
    )


class DomoThermostatProfileNumber(NumberEntity):
    """Valore di profilo termico (T1/T2/T3/Antigelo) di un termostato"""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, thermostat: DomoThermostat, attr_key: str, entry_id: str):
        self._thermostat = thermostat
        self._attr_key = attr_key

        label, icon, min_value, max_value, step, mode = _PROFILE_ATTRS[attr_key]
        self._attr_icon = icon
        self._attr_name = label
        self._attr_mode = mode
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_unique_id = f"domo_thermostat_{thermostat.act_id}_{attr_key}"
        # Si aggancia allo stesso device della climate entity (sub-device del termostato)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate_{thermostat.unique_id}")},
        )

    @property
    def native_value(self) -> Optional[float]:
        return getattr(self._thermostat, self._attr_key)

    async def async_set_native_value(self, value: float) -> None:
        value = self._enforce_profile_order(value)

        try:
            ok = await self._thermostat.async_set_thermal_profile_value(self._attr_key, value)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        except Exception as err:
            raise HomeAssistantError(f"Errore invio thermo_zone_config_req: {err}") from err

        if not ok:
            raise HomeAssistantError(
                "Comando ignorato: profilo termico non ancora completo per questo termostato."
            )

    def _enforce_profile_order(self, value: float) -> float:
        """Corregge value per garantire t1 < t2 < t3, replicando il clamp dell'app ufficiale."""
        t1 = self._thermostat.t1
        t2 = self._thermostat.t2
        t3 = self._thermostat.t3
        step = self._attr_native_step

        if self._attr_key == "t1" and t2 is not None and value >= t2:
            value = round(t2 - step, 1)

        elif self._attr_key == "t2":
            if t1 is not None and value <= t1:
                value = round(t1 + step, 1)
            elif t3 is not None and value >= t3:
                value = round(t3 - step, 1)

        elif self._attr_key == "t3" and t2 is not None and value <= t2:
            value = round(t2 + step, 1)

        return max(self._attr_native_min_value, min(self._attr_native_max_value, value))

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._thermostat.unique_id:
            self.async_write_ha_state()


class DomoThermostatDiffNumber(NumberEntity):
    """Differenziale termico (usato in modalità DIFF) di un termostato."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0.1
    _attr_native_max_value = 2.0
    _attr_native_step = 0.1
    _attr_icon = "mdi:delta"
    _attr_name = "Differenziale termico"

    def __init__(self, thermostat: DomoThermostat, entry_id: str):
        self._thermostat = thermostat
        self._attr_unique_id = f"domo_thermostat_{thermostat.act_id}_diff_t_dec"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate_{thermostat.unique_id}")},
        )

    @property
    def native_value(self) -> Optional[float]:
        return self._thermostat.diff_t_dec

    async def async_set_native_value(self, value: float) -> None:
        try:
            ok = await self._thermostat.async_set_diff_t_dec(value)
        except Exception as err:
            raise HomeAssistantError(f"Errore invio thermo_zone_config_req: {err}") from err

        if not ok:
            raise HomeAssistantError(
                "Comando ignorato: profilo termico non ancora completo per questo termostato."
            )

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._thermostat.unique_id:
            self.async_write_ha_state()


# ============================================================
# DEVICE INFO CONDIVISO PER I SETTORI DI IRRIGAZIONE
# ============================================================
def _irrigation_zone_device_info(zone: DomoIrrigationZone, entry_id: str) -> DeviceInfo:
    """DeviceInfo del device 'settore di irrigazione', condiviso da tutte le
    entita' agganciate alla zona (number, switch, time, ...)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_irrigation_{zone.zone_id}")},
        name=zone.name,
        manufacturer="Home Sapiens Assistant",
        model="Eti/Domo",
    )


# ============================================================
# ENTITA' NUMBER PER LA DURATA (PERC) DEI SETTORI DI IRRIGAZIONE
# ============================================================
class DomoIrrigationPercNumber(NumberEntity):
    """Entita' 'number' per la percentuale stagionale (% STAGIONALE) di un settore
    di irrigazione. 100 = durata nominale; range 50-150 confermato dalla UI nativa.
    """

    _attr_should_poll = False
    _attr_icon = "mdi:water-percent"
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 50
    _attr_native_max_value = 150
    _attr_native_step = 1

    def __init__(self, zone: DomoIrrigationZone, entry_id: str):
        self._zone = zone
        self._attr_unique_id = f"domo_irrigation_{zone.zone_id}_perc"
        self._attr_name = "% STAGIONALE"
        # Dispositivo condiviso con le altre entita' dello stesso settore
        self._attr_device_info = _irrigation_zone_device_info(zone, entry_id)

    @property
    def native_value(self) -> Optional[float]:
        return float(self._zone.perc)

    async def async_set_native_value(self, value: float) -> None:
        try:
            await async_set_irrigation_perc(
                self._zone.zone_id, int(value), self._zone.gateway
            )
        except Exception as err:
            raise HomeAssistantError(
                f"Errore invio irrigation_set_req (perc): {err}"
            ) from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._zone.unique_id:
            self.async_write_ha_state()


# ============================================================
# ENTITA' NUMBER PER GLI IRRIGATORI (tempo massimo / ciclo di lavoro)
# ============================================================
def _sprinkler_device_info(sprinkler: DomoSprinkler, entry_id: str) -> DeviceInfo:
    """DeviceInfo del device 'settore di irrigazione' a cui appartiene lo
    sprinkler: le entita' irrigatore condividono lo stesso device della zona
    (nessun sub-device separato), distinte tra loro solo tramite il nome."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_irrigation_{sprinkler.zone_id}")},
    )


class DomoIrrigationActiveNumber(NumberEntity):
    """Tempo massimo di irrigazione del singolo irrigatore.
    Sotto 60 min mostra minuti interi (1-59), da 60 min in su mostra ore
    con un decimo di precisione (1,0 - 6,0)."""

    _attr_should_poll = False
    _attr_icon = "mdi:timer-outline"
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, sprinkler: DomoSprinkler, entry_id: str):
        self._sprinkler = sprinkler
        self._attr_unique_id = f"{sprinkler.unique_id}_active"
        self._attr_name = f"{sprinkler.name} Tempo max irrigazione"
        self._attr_device_info = _sprinkler_device_info(sprinkler, entry_id)

    @property
    def _use_hours(self) -> bool:
        active = self._sprinkler.active or 0
        return active >= 3600

    @property
    def native_unit_of_measurement(self) -> str:
        return UnitOfTime.HOURS if self._use_hours else UnitOfTime.MINUTES

    @property
    def native_step(self) -> float:
        return 0.1 if self._use_hours else 1

    @property
    def native_min_value(self) -> float:
        return 1

    @property
    def native_max_value(self) -> float:
        return 6.0 if self._use_hours else 59

    @property
    def native_value(self) -> Optional[float]:
        active = self._sprinkler.active
        if active is None:
            return None
        if self._use_hours:
            return round(active / 3600, 1)
        return round(active / 60)

    async def async_set_native_value(self, value: float) -> None:
        use_hours = self._use_hours  # modalita' corrente (prima dell'aggiornamento)

        if use_hours and value <= self.native_min_value:
            # Slider spinto al minimo della scala ore -> passa a minuti (59)
            seconds = 59 * 60
        elif not use_hours and value >= self.native_max_value:
            # Slider spinto al massimo della scala minuti -> passa a ore (1,0)
            seconds = 3600
        elif use_hours:
            seconds = int(round(value * 3600))
        else:
            seconds = int(round(value)) * 60

        try:
            await async_set_sprinkler_active(
                self._sprinkler.zone_id, self._sprinkler.act_id, seconds, self._sprinkler.gateway
            )
        except Exception as err:
            raise HomeAssistantError(f"Errore invio irrigation_set_req (active): {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._sprinkler.unique_id:
            self.async_write_ha_state()


class DomoIrrigationDutyNumber(NumberEntity):
    """Ciclo di lavoro (duty cycle) del singolo irrigatore."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:percent-outline"
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1

    def __init__(self, sprinkler: DomoSprinkler, entry_id: str):
        self._sprinkler = sprinkler
        self._attr_unique_id = f"{sprinkler.unique_id}_duty"
        self._attr_name = f"{sprinkler.name} Ciclo di lavoro"
        self._attr_device_info = _sprinkler_device_info(sprinkler, entry_id)

    @property
    def native_value(self) -> Optional[float]:
        return self._sprinkler.duty

    async def async_set_native_value(self, value: float) -> None:
        try:
            await async_set_sprinkler_duty(
                self._sprinkler.zone_id, self._sprinkler.act_id, int(round(value)), self._sprinkler.gateway
            )
        except Exception as err:
            raise HomeAssistantError(f"Errore invio irrigation_set_req (duty): {err}") from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._sprinkler.unique_id:
            self.async_write_ha_state()
