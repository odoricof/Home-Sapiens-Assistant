"""
domo/select.py

Entities fed by:
- platforms/thermoregulation.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import callback

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.thermoregulation import ALGO_MODE_TO_PARAMS, PROFILE_DAY_TO_ID
from .platforms.thermoregulation import get_all_thermostats
from .services.thermo_backup import (
    list_backup_files,
    get_selected_restore_file,
    set_selected_restore_file,
    get_restore_status,
    async_refresh_backup_files_cache,
    RESTORE_PLACEHOLDER,
)
_LOGGER = logging.getLogger(__name__)

_ALGO_MODE_OPTIONS = list(ALGO_MODE_TO_PARAMS.keys())

SEASON_OPTIONS = {
    "summer": "Estate",
    "winter": "Inverno",
    "plant_off": "Impianto Spento",
}
SEASON_OPTIONS_REVERSE = {v: k for k, v in SEASON_OPTIONS.items()}


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup select platform."""

    thermostats = get_all_thermostats()

    if not thermostats:
        _LOGGER.debug("No thermostats found yet, skipping plant mode select")
        return
    await async_refresh_backup_files_cache(hass)

    entities = [
        DomoPlantModeSelect(hass, entry.entry_id),
        DomoThermoRestoreFileSelect(hass, entry.entry_id),
    ]
    entities.extend(
        entity
        for thermostat in thermostats
        for entity in (
            DomoThermostatAlgoModeSelect(thermostat, entry.entry_id),
            DomoThermostatProfileDaySelect(thermostat, entry.entry_id),
        )
    )

    async_add_entities(entities)

    _LOGGER.info("Added plant mode select entity and %d algo mode select entities", len(thermostats))

class DomoPlantModeSelect(SelectEntity):
    """Select entity to display and set the plant-wide season mode."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(SEASON_OPTIONS.values())

    def __init__(self, hass, entry_id: str):
        """Initialize the plant mode select entity."""
        self.hass = hass
        self._entry_id = entry_id

        self._attr_unique_id = f"{entry_id}_plant_mode"
        self._attr_name = "Plant Mode"
        self._attr_should_poll = False

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate")},
            name="Climate",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
)

        _LOGGER.debug("Created plant mode select entity")

    @property
    def current_option(self) -> str | None:
        """Return the current plant season, read from any thermostat (plant-wide value)."""

        thermostats = get_all_thermostats()
        if not thermostats:
            return None

        season = thermostats[0]._season
        return SEASON_OPTIONS.get(season)

    async def async_select_option(self, option: str) -> None:
        """Imposta la stagione a livello di impianto."""

        season = SEASON_OPTIONS_REVERSE.get(option)
        if season is None:
            raise HomeAssistantError(f"Opzione non valida: {option}")

        thermostats = get_all_thermostats()
        if not thermostats:
            raise HomeAssistantError("Nessun termostato disponibile")

        gateway = thermostats[0]._gateway
        await gateway.tx_command(
            {"cmd_name": "thermo_season_req", "season": season},
            resp_command=None,
        )

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
        """Handle update from bus"""
        self.async_write_ha_state()
        
class DomoThermostatAlgoModeSelect(SelectEntity):
    """Modalità dell'algoritmo di regolazione (PI1/PI2/PI3/PI4/DIFF) di un termostato."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:tune-variant"
    _attr_options = _ALGO_MODE_OPTIONS
    _attr_name = "Modalità algoritmo"

    def __init__(self, thermostat, entry_id: str):
        self._thermostat = thermostat
        self._attr_unique_id = f"domo_thermostat_{thermostat.act_id}_algo_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate_{thermostat.unique_id}")},
        )

    @property
    def current_option(self) -> str | None:
        return self._thermostat.algo_mode

    async def async_select_option(self, option: str) -> None:
        try:
            ok = await self._thermostat.async_set_algo_mode(option)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
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
            
class DomoThermostatProfileDaySelect(SelectEntity):
    """Giorno (o Jolly) del profilo termico attualmente in editing per un termostato."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:calendar-week"
    _attr_options = list(PROFILE_DAY_TO_ID.keys())
    _attr_name = "Giorno del profilo termico"

    def __init__(self, thermostat, entry_id: str):
        self._thermostat = thermostat
        self._attr_unique_id = f"domo_thermostat_{thermostat.act_id}_profile_day"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate_{thermostat.unique_id}")},
        )

    @property
    def current_option(self) -> str | None:
        return self._thermostat.selected_profile_day

    async def async_select_option(self, option: str) -> None:
        try:
            self._thermostat.set_selected_profile_day(option)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        self.async_write_ha_state()
        async_dispatcher_send(self.hass, SIGNAL_UPDATE_ENTITY, self._thermostat.unique_id)
        
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

class DomoThermoRestoreFileSelect(SelectEntity):
    """Elenco dei file di backup profili termici disponibili per il ripristino."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:file-restore"
    _attr_name = "File backup profili termici"
    _attr_should_poll = False

    def __init__(self, hass, entry_id: str):
        self.hass = hass
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_thermo_restore_file"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate")},
        )

    @property
    def options(self) -> list[str]:
        files = list_backup_files(self.hass)
        base = [RESTORE_PLACEHOLDER] + files if files else ["Nessun backup disponibile"]
        status = get_restore_status()
        if status and status not in base:
            return [status] + base
        return base

    @property
    def current_option(self) -> str | None:
        status = get_restore_status()
        if status:
            return status
        selected = get_selected_restore_file()
        options = self.options
        if selected in options:
            return selected
        return options[0]

    async def async_select_option(self, option: str) -> None:
        set_selected_restore_file(option)
        self.async_write_ha_state()

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
        self.async_write_ha_state()
        
