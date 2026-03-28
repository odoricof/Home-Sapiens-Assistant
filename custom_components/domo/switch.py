"""
domo/switch.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""

from __future__ import annotations
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import callback

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.activations import DomoActivation

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup switch platform per le attivazioni"""
    from .platforms.activations import get_all_activations
    
    activations = get_all_activations()
    if not activations:
        _LOGGER.debug("No activations found yet")
        return
    
    # Crea un dispositivo virtuale che contiene tutte le attivazioni
    activations_device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_activations")},
        name="Activations",
        manufacturer="Home Sapiens",
        model="Relays Hub",
    )
    
    entities = [DomoSwitchEntity(activation, activations_device_info, entry.entry_id) 
                for activation in activations]
    async_add_entities(entities)
    
    _LOGGER.info("Added %d switch entities for activations", len(entities))


class DomoSwitchEntity(SwitchEntity):
    """Switch entity per attivazioni"""
    
    # Mappa degli icon_id alle icone MDI
    ICON_MAP = {
        1: "mdi:lightbulb-on-outline",
        2: "mdi:air-conditioner",
        3: "mdi:radiator",
        4: "mdi:television-classic",
        5: "mdi:pipe-valve",
        6: "mdi:pipe-valve",
        7: "mdi:doorbell",
        8: "mdi:power-socket-eu",
        9: "mdi:roller-shade",
        10: "mdi:roller-shade-closed",
        11: "mdi:gate-open",
        12: "mdi:gate",
        13: "mdi:gate-open",
        14: "mdi:gate",
        15: "mdi:boom-gate-arrow-up-outline",
        16: "mdi:boom-gate-arrow-down-outline",
        17: "mdi:car-off",
        18: "mdi:car-off",
        19: "mdi:turnstile-outline",
        20: "mdi:turnstile",
        21: "mdi:door-sliding-open",
        22: "mdi:door-sliding",
        23: "mdi:garage-open-variant",
        24: "mdi:garage-variant",
        25: "mdi:speaker",
        26: "mdi:projector-screen-variant-off-outline",
        27: "mdi:projector-screen-variant-outline",
        28: "mdi:fridge-outline",
        29: "mdi:washing-machine",
        30: "mdi:toaster-oven",
        31: "mdi:key",
        32: "mdi:solar-power-variant-outline",
        33: "mdi:heat-pump",
        34: "mdi:wind-power",
        35: "mdi:hvac",
        36: "mdi:ceiling-fan",
    }    
    
    def __init__(self, activation: DomoActivation, device_info: DeviceInfo, entry_id: str):
        """Initialize the switch entity."""
        self._activation = activation
        self._attr_unique_id = activation.unique_id
        self._attr_name = activation.name
        self._attr_should_poll = False
        self._attr_device_info = device_info
        
    @property
    def icon(self) -> str | None:
        """Restituisce l'icona basata su icon_id."""
        icon_id = self._activation.icon_id
        if icon_id and icon_id in self.ICON_MAP:
            return self.ICON_MAP[icon_id]
        return self.DEFAULT_ICON        
        
    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._activation.is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self._activation.async_turn_on()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self._activation.async_turn_off()

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
