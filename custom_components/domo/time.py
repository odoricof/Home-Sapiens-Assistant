"""
domo/time.py

Entities fed by:
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
from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_DISCOVERY_NEW, SIGNAL_UPDATE_ENTITY
from .platforms.irrigation import (
    DomoIrrigationZone,
    get_all_irrigation_zones,
    async_set_irrigation_start,
)

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ENTITA' TIME PER L'ORARIO DI PARTENZA DEI SETTORI DI IRRIGAZIONE
# ============================================================
class DomoIrrigationStartTime(TimeEntity):
    """Entita' 'time' per l'orario di partenza programmato di un settore di irrigazione."""

    _attr_should_poll = False
    _attr_icon = "mdi:clock-start"

    def __init__(self, zone: DomoIrrigationZone, entry_id: str):
        self._zone = zone
        self._attr_unique_id = f"domo_irrigation_{zone.zone_id}_start"
        self._attr_name = "ORA INIZIO"

        # Dispositivo condiviso con le altre entita' dello stesso settore
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_irrigation_{zone.zone_id}")},
            name=zone.name,
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

    @property
    def native_value(self) -> dt_time | None:
        start = self._zone.start
        if start is None:
            return None
        return dt_time(hour=start["hour"], minute=start["min"], second=start["sec"])

    async def async_set_value(self, value: dt_time) -> None:
        try:
            await async_set_irrigation_start(
                self._zone.zone_id,
                value.hour,
                value.minute,
                value.second,
                self._zone.gateway,
            )
        except Exception as err:
            raise HomeAssistantError(
                f"Errore invio irrigation_set_req (start): {err}"
            ) from err

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._zone.unique_id:
            self.async_write_ha_state()

class DomoIrrigationEndTime(TimeEntity):
    """Entita' 'time' di sola lettura per l'ora di fine irrigazione.
    (start + durata nominale * % stagionale)."""

    _attr_should_poll = False
    _attr_icon = "mdi:clock-end"

    def __init__(self, zone: DomoIrrigationZone, entry_id: str):
        self._zone = zone
        self._attr_unique_id = f"domo_irrigation_{zone.zone_id}_end"
        self._attr_name = "ORA FINE"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_irrigation_{zone.zone_id}")},
            name=zone.name,
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

    @property
    def native_value(self) -> dt_time | None:
        end = self._zone.end
        if end is None:
            return None
        return dt_time(hour=end["hour"], minute=end["min"], second=end["sec"])

    async def async_set_value(self, value: dt_time) -> None:
        raise HomeAssistantError(
            "Ora fine calcolata automaticamente dal gateway: non modificabile."
        )

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    """@callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._zone.unique_id:
            self.async_write_ha_state()"""
    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._zone.unique_id:
            _LOGGER.debug("ENDTIME AGGIORNAMENTO | nuovo valore: %s", self.native_value)
            self.async_schedule_update_ha_state(force_refresh=True)       
# ============================================================
# SETUP ENTRY
# ============================================================
async def async_setup_entry(hass, entry, async_add_entities):
    """Setup piattaforma time per l'orario di partenza dei settori di irrigazione (IRRIGATION)."""
    _LOGGER.debug("Setup piattaforma time (IRRIGATION)")

    added_ids: set[int] = set()

    def _add_zone(zone: DomoIrrigationZone):
        if zone.zone_id in added_ids:
            return
        added_ids.add(zone.zone_id)
        entities = [
            DomoIrrigationStartTime(zone, entry.entry_id),
            DomoIrrigationEndTime(zone, entry.entry_id),
        ]
        async_add_entities(entities)
        _LOGGER.info(
            "Added %d time entities for irrigation zone id=%s (%s)",
            len(entities), zone.zone_id, zone.name,
        )

    for zone in get_all_irrigation_zones():
        _add_zone(zone)

    @callback
    def _async_new_zone(zone: DomoIrrigationZone):
        _add_zone(zone)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_DISCOVERY_NEW.format("time"), _async_new_zone)
    )
