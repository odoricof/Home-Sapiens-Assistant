"""
domo/select.py

Entities fed by:
- platforms/loadsctrl.py
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

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY, SIGNAL_DISCOVERY_NEW
from .platforms.loadsctrl import (
    DomoLoadCtrlMeter,
    LOADCTRL_DAY_TO_INDEX,
    get_all_loadsctrl_meters,
)
from .platforms.thermoregulation import ALGO_MODE_TO_PARAMS, PROFILE_DAY_TO_ID, get_all_thermostats
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
_WEEKDAY_OPTIONS = [day for day in PROFILE_DAY_TO_ID if day != "Jolly"]
_COPY_PLACEHOLDER = "Selezionare"
_COPY_ALL_WEEK = "Tutta la settimana"
_LOADCTRL_WEEKDAY_OPTIONS = list(LOADCTRL_DAY_TO_INDEX.keys())


SEASON_OPTIONS = {
    "summer": "Estate",
    "winter": "Inverno",
    "plant_off": "Impianto Spento",
}
SEASON_OPTIONS_REVERSE = {v: k for k, v in SEASON_OPTIONS.items()}


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the select platform."""

    thermostats = get_all_thermostats()
    loadsctrl_meters = get_all_loadsctrl_meters()

    entities = []

    # --- Thermostats ---
    if thermostats:
        await async_refresh_backup_files_cache(hass)
        entities.extend([
            DomoPlantModeSelect(hass, entry.entry_id),
            DomoThermoRestoreFileSelect(hass, entry.entry_id),
        ])
        entities.extend(
            entity
            for thermostat in thermostats
            for entity in (
                DomoThermostatAlgoModeSelect(thermostat, entry.entry_id),
                DomoThermostatProfileDaySelect(thermostat, entry.entry_id),
                DomoThermostatProfileCopySelect(thermostat, entry.entry_id),
            )
        )
    else:
        _LOGGER.debug("No thermostat found, skipping climate select entities")

    # --- Load Control ---
    entities.extend(
        DomoLoadCtrlProfileDaySelect(meter) for meter in loadsctrl_meters
    )

    if not entities:
        _LOGGER.debug("No thermostat or load control manager found, skipping select setup")
        return

    async_add_entities(entities)

    _LOGGER.info(
        "Added %d select entities (%d thermostats, %d load control managers)",
        len(entities), len(thermostats), len(loadsctrl_meters),
    )

    loadsctrl_added_ids: set[int] = set()
    for meter in loadsctrl_meters:
        loadsctrl_added_ids.add(meter.meter_id)

    @callback
    def _async_new_loadsctrl_meter(meter: DomoLoadCtrlMeter):
        if meter.meter_id in loadsctrl_added_ids:
            return
        loadsctrl_added_ids.add(meter.meter_id)
        async_add_entities([DomoLoadCtrlProfileDaySelect(meter)])
        _LOGGER.info("Added select entity for load control manager id=%s (%s)", meter.meter_id, meter.name)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_select"), _async_new_loadsctrl_meter
        )
    )


# ============================================================
# ===== THERMOSTATS =====
# ============================================================

class DomoPlantModeSelect(SelectEntity):
    """Select entity to view and set the plant-wide season mode."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(SEASON_OPTIONS.values())

    def __init__(self, hass, entry_id: str):
        """Initialize the select entity for the plant mode."""
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

        _LOGGER.debug("Created select entity for plant mode")

    @property
    def current_option(self) -> str | None:
        """Return the current season read from the first thermostat (global value)."""
        thermostats = get_all_thermostats()
        if not thermostats:
            return None

        return SEASON_OPTIONS.get(thermostats[0].season)

    async def async_select_option(self, option: str) -> None:
        """Set the plant-wide season."""
        season = SEASON_OPTIONS_REVERSE.get(option)
        if season is None:
            raise HomeAssistantError(f"Opzione non valida: {option}")

        thermostats = get_all_thermostats()
        if not thermostats:
            raise HomeAssistantError("Nessun termostato disponibile")

        gateway = thermostats[0].gateway
        await gateway.tx_command(
            {"cmd_name": "thermo_season_req", "season": season},
            resp_command=None,
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
        self.async_write_ha_state()


class DomoThermostatAlgoModeSelect(SelectEntity):
    """Regulation algorithm mode (PI1/PI2/PI3/PI4/DIFF) of a thermostat."""

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
    """Day (or Jolly) of the thermal profile currently being edited for a thermostat."""

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


class DomoThermostatProfileCopySelect(SelectEntity):
    """Copy the thermal profile of the currently selected day to another day (or to the whole week)."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:content-copy"
    _attr_name = "Copia profilo termico su"

    def __init__(self, thermostat, entry_id: str):
        self._thermostat = thermostat
        self._attr_unique_id = f"domo_thermostat_{thermostat.act_id}_profile_copy"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate_{thermostat.unique_id}")},
        )

    @property
    def options(self) -> list[str]:
        current_day = self._thermostat.selected_profile_day
        days = [day for day in _WEEKDAY_OPTIONS if day != current_day]
        return [_COPY_PLACEHOLDER] + days + [_COPY_ALL_WEEK]

    @property
    def current_option(self) -> str | None:
        return _COPY_PLACEHOLDER

    async def async_select_option(self, option: str) -> None:
        if option == _COPY_PLACEHOLDER:
            return

        source_day = self._thermostat.selected_profile_day
        source_id = PROFILE_DAY_TO_ID[source_day]
        profile_data = self._thermostat.profile_raw_by_day.get(source_id)
        if not profile_data:
            raise HomeAssistantError(
                f"Nessun profilo disponibile da copiare per il giorno {source_day}."
            )

        if option == _COPY_ALL_WEEK:
            targets = [day for day in _WEEKDAY_OPTIONS if day != source_day]
        elif option in _WEEKDAY_OPTIONS:
            targets = [option]
        else:
            raise HomeAssistantError(f"Opzione non valida: {option}")

        for day in targets:
            await self._thermostat.async_write_raw_profile(PROFILE_DAY_TO_ID[day], profile_data)

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
    """List of available thermal profile backup files for restore."""

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


# ============================================================
# ===== LOAD CONTROL (ENERGY PROFILE) =====
# ============================================================

def _loadsctrl_meter_device_info(meter: DomoLoadCtrlMeter) -> DeviceInfo:
    """DeviceInfo of the load control manager (e.g. 'Generale'). Same identifiers
    used in domo/sensor.py and domo/switch.py."""
    return DeviceInfo(
        identifiers={(DOMAIN, meter.unique_id)},
        name=meter.name,
        manufacturer="Home Sapiens Assistant",
        model="Eti/Domo",
    )


class DomoLoadCtrlProfileDaySelect(SelectEntity):
    """Day of the week of the energy profile currently being edited for a
    load control manager."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:calendar-week"
    _attr_options = _LOADCTRL_WEEKDAY_OPTIONS
    _attr_name = "Giorno del profilo energetico"

    def __init__(self, meter: DomoLoadCtrlMeter):
        self._meter = meter
        self._attr_unique_id = f"{meter.unique_id}_profile_day"
        self._attr_device_info = _loadsctrl_meter_device_info(meter)

    @property
    def current_option(self) -> str | None:
        return self._meter.selected_profile_day

    async def async_select_option(self, option: str) -> None:
        try:
            self._meter.set_selected_profile_day(option)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        self.async_write_ha_state()
        async_dispatcher_send(self.hass, SIGNAL_UPDATE_ENTITY, self._meter.unique_id)

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
        if entity_id is None or entity_id == self._meter.unique_id:
            self.async_write_ha_state()
