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
from .services.i18n import async_get_translated_strings
from .services.thermo_backup import (
    list_backup_files,
    get_selected_restore_file,
    set_selected_restore_file,
    get_restore_status,
    async_refresh_backup_files_cache,
    RESTORE_PLACEHOLDER,
)

_LOGGER = logging.getLogger(__name__)


_ALGO_MODE_KEYS = list(ALGO_MODE_TO_PARAMS.keys())
_WEEKDAY_OPTIONS = [day for day in PROFILE_DAY_TO_ID if day != "jolly"]
_COPY_PLACEHOLDER = "Selezionare"
_COPY_ALL_WEEK = "Tutta la settimana"
_LOADCTRL_WEEKDAY_OPTIONS = list(LOADCTRL_DAY_TO_INDEX.keys())

# "Jolly" is a fixed technical term (not a real weekday), left untranslated
# in every language by explicit project decision.
_JOLLY_LABEL = "Jolly"

# Stable (English) season keys, order used to build the translated options list.
SEASON_KEYS = ("summer", "winter", "plant_off")


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

    def __init__(self, hass, entry_id: str):
        """Initialize the select entity for the plant mode."""
        self.hass = hass
        self._entry_id = entry_id
        self._i18n: dict[str, str] = {}

        self._attr_unique_id = f"{entry_id}_plant_mode"
        self._attr_should_poll = False

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate")},
            name="Climate",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

        _LOGGER.debug("Created select entity for plant mode")

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.plant_mode", "Season")

    @property
    def options(self) -> list[str]:
        """Return the translated season options, in stable key order."""
        return [self._i18n.get(f"season_options.{key}", key) for key in SEASON_KEYS]

    @property
    def current_option(self) -> str | None:
        """Return the current season read from the first thermostat (global value)."""
        thermostats = get_all_thermostats()
        if not thermostats:
            return None

        return self._i18n.get(f"season_options.{thermostats[0].season}")

    async def async_select_option(self, option: str) -> None:
        """Set the plant-wide season."""
        reverse = {
            self._i18n.get(f"season_options.{key}", key): key for key in SEASON_KEYS
        }
        season = reverse.get(option)
        if season is None:
            strings = await async_get_translated_strings(self.hass, "thermoregulation_entities")
            raise HomeAssistantError(strings["errors.invalid_option"].format(option=option))

        thermostats = get_all_thermostats()
        if not thermostats:
            strings = await async_get_translated_strings(self.hass, "thermoregulation_entities")
            raise HomeAssistantError(strings["errors.no_thermostat_available"])

        gateway = thermostats[0].gateway
        await gateway.tx_command(
            {"cmd_name": "thermo_season_req", "season": season},
            resp_command=None,
        )

    async def async_added_to_hass(self):
        self._i18n = await async_get_translated_strings(self.hass, "thermoregulation_entities")
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

    def __init__(self, thermostat, entry_id: str):
        self._thermostat = thermostat
        self._i18n: dict[str, str] = {}
        self._attr_unique_id = f"domo_thermostat_{thermostat.act_id}_algo_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate_{thermostat.unique_id}")},
        )

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.algo_mode", "Algorithm mode")

    @property
    def options(self) -> list[str]:
        """Return the translated algorithm mode options, in stable key order."""
        return [self._i18n.get(f"algo_mode_options.{key}", key) for key in _ALGO_MODE_KEYS]

    @property
    def current_option(self) -> str | None:
        mode = self._thermostat.algo_mode
        if mode is None:
            return None
        return self._i18n.get(f"algo_mode_options.{mode}", mode)

    async def async_select_option(self, option: str) -> None:
        reverse = {
            self._i18n.get(f"algo_mode_options.{key}", key): key for key in _ALGO_MODE_KEYS
        }
        mode = reverse.get(option, option)
        try:
            ok = await self._thermostat.async_set_algo_mode(mode)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        except Exception as err:
            strings = await async_get_translated_strings(self.hass, "thermoregulation_entities")
            raise HomeAssistantError(
                strings["action_feedback.algo_mode_send_error"].format(err=err)
            ) from err

        if not ok:
            strings = await async_get_translated_strings(self.hass, "thermoregulation_entities")
            raise HomeAssistantError(strings["action_feedback.command_ignored_profile_incomplete"])

    async def async_added_to_hass(self):
        self._i18n = await async_get_translated_strings(self.hass, "thermoregulation_entities")
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

    def __init__(self, thermostat, entry_id: str):
        self._thermostat = thermostat
        self._i18n: dict[str, str] = {}
        self._attr_unique_id = f"domo_thermostat_{thermostat.act_id}_profile_day"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate_{thermostat.unique_id}")},
        )

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.profile_day", "Thermal profile day")

    @property
    def options(self) -> list[str]:
        """Return the translated weekday options, plus the fixed 'Jolly' entry."""
        return [
            self._i18n.get(f"weekday_options.{day}", day) for day in _WEEKDAY_OPTIONS
        ] + [_JOLLY_LABEL]

    @property
    def current_option(self) -> str | None:
        day = self._thermostat.selected_profile_day
        if day == "jolly":
            return _JOLLY_LABEL
        return self._i18n.get(f"weekday_options.{day}", day)

    async def async_select_option(self, option: str) -> None:
        if option == _JOLLY_LABEL:
            day = "jolly"
        else:
            reverse = {
                self._i18n.get(f"weekday_options.{key}", key): key for key in _WEEKDAY_OPTIONS
            }
            day = reverse.get(option, option)
        try:
            self._thermostat.set_selected_profile_day(day)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        self.async_write_ha_state()
        async_dispatcher_send(self.hass, SIGNAL_UPDATE_ENTITY, self._thermostat.unique_id)

    async def async_added_to_hass(self):
        self._i18n = await async_get_translated_strings(self.hass, "thermoregulation_entities")
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

    def __init__(self, thermostat, entry_id: str):
        self._thermostat = thermostat
        self._i18n: dict[str, str] = {}
        self._attr_unique_id = f"domo_thermostat_{thermostat.act_id}_profile_copy"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate_{thermostat.unique_id}")},
        )

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.profile_copy", "Copy thermal profile to")

    @property
    def options(self) -> list[str]:
        current_day = self._thermostat.selected_profile_day
        days = [
            self._i18n.get(f"weekday_options.{day}", day)
            for day in _WEEKDAY_OPTIONS if day != current_day
        ]
        placeholder = self._i18n.get("copy_profile.placeholder", _COPY_PLACEHOLDER)
        all_week = self._i18n.get("copy_profile.all_week", _COPY_ALL_WEEK)
        return [placeholder] + days + [all_week]

    @property
    def current_option(self) -> str | None:
        return self._i18n.get("copy_profile.placeholder", _COPY_PLACEHOLDER)

    async def async_select_option(self, option: str) -> None:
        placeholder = self._i18n.get("copy_profile.placeholder", _COPY_PLACEHOLDER)
        all_week = self._i18n.get("copy_profile.all_week", _COPY_ALL_WEEK)

        if option == placeholder:
            return

        source_day = self._thermostat.selected_profile_day
        source_id = PROFILE_DAY_TO_ID[source_day]
        profile_data = self._thermostat.profile_raw_by_day.get(source_id)
        if not profile_data:
            # Defensive branch, not reachable in practice (confirmed) - left untranslated.
            raise HomeAssistantError(
                f"Nessun profilo disponibile da copiare per il giorno {source_day}."
            )

        reverse = {
            self._i18n.get(f"weekday_options.{day}", day): day for day in _WEEKDAY_OPTIONS
        }

        if option == all_week:
            targets = [day for day in _WEEKDAY_OPTIONS if day != source_day]
        elif option in reverse:
            targets = [reverse[option]]
        else:
            strings = await async_get_translated_strings(self.hass, "thermoregulation_entities")
            raise HomeAssistantError(strings["errors.invalid_option"].format(option=option))

        for day in targets:
            await self._thermostat.async_write_raw_profile(PROFILE_DAY_TO_ID[day], profile_data)

        self.async_write_ha_state()
        async_dispatcher_send(self.hass, SIGNAL_UPDATE_ENTITY, self._thermostat.unique_id)

    async def async_added_to_hass(self):
        self._i18n = await async_get_translated_strings(self.hass, "thermoregulation_entities")
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
    _attr_should_poll = False

    def __init__(self, hass, entry_id: str):
        self.hass = hass
        self._entry_id = entry_id
        self._i18n: dict[str, str] = {}
        self._attr_unique_id = f"{entry_id}_thermo_restore_file"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_climate")},
        )

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.restore_file", "Thermal profile backup file")

    @property
    def options(self) -> list[str]:
        placeholder = self._i18n.get("restore_file.placeholder", "-- seleziona un file --")
        files = list_backup_files(self.hass)
        no_backup = self._i18n.get("errors.no_backup_available", "Nessun backup disponibile")
        base = [placeholder] + files if files else [no_backup]
        status_key = get_restore_status()
        status = self._i18n.get(f"restore_file.status.{status_key}") if status_key else None
        if status and status not in base:
            return [status] + base
        return base

    @property
    def current_option(self) -> str | None:
        status_key = get_restore_status()
        if status_key:
            return self._i18n.get(f"restore_file.status.{status_key}")
        selected = get_selected_restore_file()
        options = self.options
        if selected in options:
            return selected
        return options[0]

    async def async_select_option(self, option: str) -> None:
        placeholder = self._i18n.get("restore_file.placeholder", "-- seleziona un file --")
        selected = RESTORE_PLACEHOLDER if option == placeholder else option
        set_selected_restore_file(selected)
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self._i18n = await async_get_translated_strings(self.hass, "thermoregulation_entities")
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

    def __init__(self, meter: DomoLoadCtrlMeter):
        self._meter = meter
        self._i18n: dict[str, str] = {}
        self._attr_unique_id = f"{meter.unique_id}_profile_day"
        self._attr_device_info = _loadsctrl_meter_device_info(meter)

    @property
    def name(self) -> str:
        return self._i18n.get("entity_names.profile_day", "Energy profile day")

    @property
    def options(self) -> list[str]:
        return [
            self._i18n.get(f"weekday_options.{key}", key)
            for key in _LOADCTRL_WEEKDAY_OPTIONS
        ]

    @property
    def current_option(self) -> str | None:
        return self._i18n.get(
            f"weekday_options.{self._meter.selected_profile_day}",
            self._meter.selected_profile_day,
        )

    async def async_select_option(self, option: str) -> None:
        reverse = {
            self._i18n.get(f"weekday_options.{key}", key): key
            for key in _LOADCTRL_WEEKDAY_OPTIONS
        }
        day = reverse.get(option, option)
        try:
            self._meter.set_selected_profile_day(day)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        self.async_write_ha_state()
        async_dispatcher_send(self.hass, SIGNAL_UPDATE_ENTITY, self._meter.unique_id)

    async def async_added_to_hass(self):
        self._i18n = await async_get_translated_strings(self.hass, "loadsctrl_entities")
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
