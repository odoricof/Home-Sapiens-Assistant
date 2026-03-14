"""
domo/__init__.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, CONF_PENDING
from .gateway import DomoGateway
from .platforms.digital_in import discover_digital_ins, handle_digital_in_status_update
from .platforms.sicu import handle_security_status_update, discover_security
from .platforms.lights import discover_lights, handle_light_status_update 
from .platforms.thermoregulation import discover_thermostats, handle_thermostat_status_update
from .platforms.meters import discover_meters, handle_meter_status_update
from .platforms.scenarios import discover_scenarios, handle_scenario_status_update
from .services.logger_security_events import SecurityEventsLogger

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Domo from a config entry."""
    _LOGGER.debug("Setting up Domo integration via config flow")
    
    # Inizializza strutture dati
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(CONF_PENDING, {})
    
    # Crea gateway con i dati dalla config entry
    gateway = DomoGateway(
        hass,
        host=entry.data["host"],
        username=entry.data["username"],
        password=entry.data["password"],
    )
    
    # Registra callback e avvia
    gateway.register_event_callback(handle_digital_in_status_update)
    gateway.register_event_callback(handle_security_status_update)
    gateway.register_event_callback(handle_light_status_update)
    gateway.register_event_callback(handle_thermostat_status_update)
    gateway.register_event_callback(handle_meter_status_update)
    gateway.register_event_callback(handle_scenario_status_update)
    
    await gateway.start()
    

    await discover_digital_ins(gateway)
    await discover_lights(gateway)
    await discover_security(gateway)
    await discover_thermostats(gateway)
    await discover_meters(gateway)
    await discover_scenarios(gateway)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)    
    
    
    # Salva riferimento
    hass.data[DOMAIN][entry.entry_id] = gateway
    hass.data[DOMAIN]["gateway"] = gateway    
    
    # Inizializza il logger eventi
    _LOGGER.debug("Initializing Security events logger")
    SecurityEventsLogger(hass)    
    

    _LOGGER.info("DOMO integration initialized")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Domo integration")
    
    # Ferma gateway
    gateway = hass.data[DOMAIN].pop(entry.entry_id)
    await gateway.stop()
    
    # Unload piattaforme
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # Se non ci sono altre entry, pulisci
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)
    
    return True
