"""domo/binary_sensor.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""

from __future__ import annotations
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.digital_in import DomoDigitalIn

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup binary sensor platform."""
    from .platforms.digital_in import get_all_digital_ins
    
    digital_ins = get_all_digital_ins()
    if not digital_ins:
        return
    
    # Crea un dispositivo virtuale che contiene tutti gli ingressi digitali
    digital_inputs_device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_digital_inputs")},
        name="Digital Inputs",
        manufacturer="Home Sapiens",
        model=" ",
    )
    
    entities = [DomoBinarySensor(digital_in, digital_inputs_device_info) for digital_in in digital_ins]
    async_add_entities(entities)


class DomoBinarySensor(BinarySensorEntity):
    """Binary sensor entity."""

    def __init__(self, digital_in: DomoDigitalIn, device_info: DeviceInfo):
        self._digital_in = digital_in
        self._attr_unique_id = digital_in.unique_id
        self._attr_name = digital_in.name
        self._attr_should_poll = False
        self._attr_device_info = device_info

    @property
    def is_on(self):
        return self._digital_in.is_on

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
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()
