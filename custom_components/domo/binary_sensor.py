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
from .platforms.digital_in import DomoDigitalIn, get_all_digital_ins
from .platforms.sicu import get_security_device

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup binary sensor platform."""
    entities = []

    # ------------------------------------------------------------------
    # Binary sensor: ingressi digitali
    # (raggruppati sotto il device "Digital Inputs")
    # ------------------------------------------------------------------
    digital_ins = get_all_digital_ins()
    if digital_ins:
        digital_inputs_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_digital_inputs")},
            name="Digital Inputs",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )

        entities.extend([DomoBinarySensor(digital_in, digital_inputs_device_info)
                        for digital_in in digital_ins])
        _LOGGER.info("Added %d binary sensors for digital inputs", len(digital_ins))

    # ------------------------------------------------------------------
    # Binary sensor: allarme - uscite sicurezza
    # (raggruppati sotto il subdevice "Security Outputs", figlio del
    # device "Alarm" creato dall'alarm panel)
    # ------------------------------------------------------------------
    security = get_security_device()
    if security and hasattr(security, "_outputs") and security._outputs:
        security_outputs_device_info = DeviceInfo(
            identifiers={(DOMAIN, "burlgar_alarm_outputs")},
            name="Security Outputs",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
            via_device=(DOMAIN, "burlgar_alarm"),
        )

        for output in security._outputs:
            output_id = output.get("output_id")
            output_name = output.get("name", f"Uscita {output_id}")
            entities.append(SecurityOutputBinarySensor(security, output_id, output_name, security_outputs_device_info))
            _LOGGER.info("Added binary sensor for security output: %s (ID: %s)", output_name, output_id)
    else:
        _LOGGER.debug("No security outputs available yet")

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added total %d binary sensor entities", len(entities))
    else:
        _LOGGER.debug("No binary sensor entities to add")


# ==========================================================================
# Classi entità: ingressi digitali
# ==========================================================================
class DomoBinarySensor(BinarySensorEntity):
    """Binary sensor entity for digital inputs."""

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


# ==========================================================================
# Classi entità: allarme - uscite sicurezza
# ==========================================================================
class SecurityOutputBinarySensor(BinarySensorEntity):
    """Binary sensor entity per le uscite della centrale sicurezza."""

    def __init__(self, security, output_id: int, name: str, device_info: DeviceInfo):
        self._security = security
        self._output_id = output_id
        self._attr_unique_id = f"{security.unique_id}_output_{output_id}"
        self._attr_name = f"Security {name}"
        self._attr_should_poll = False
        self._attr_device_info = device_info
        self._state = False
        for out in security._outputs:
            if out.get("output_id") == output_id:
                self._state = out.get("status", 0) == 1
                break

    @property
    def icon(self) -> str:
        """Icona per le uscite di sicurezza."""
        return "mdi:toggle-switch" if self._state else "mdi:toggle-switch-off"

    @property
    def device_class(self) -> str | None:
        """Device class per il sensore binario."""
        return None

    @property
    def is_on(self) -> bool:
        """Return true if output is active."""
        return self._state

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        @callback
        def handle_update(entity_id: str = None):
            """Handle update from bus."""
            if entity_id and entity_id != self._attr_unique_id:
                return
            snapshot = getattr(self._security, "_last_snapshot", None)
            if snapshot:
                for out in snapshot.get("outputs", []):
                    if out.get("output_id") == self._output_id:
                        new_state = out.get("status", 0) == 1
                        if new_state != self._state:
                            self._state = new_state
                            self.async_write_ha_state()
                        break

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, handle_update)
        )
