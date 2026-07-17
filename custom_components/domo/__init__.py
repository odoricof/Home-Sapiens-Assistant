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
from .platforms.activations import discover_activations, handle_activation_status_update
from .platforms.analogics import discover_analogics, handle_analogic_status_update
from .platforms.digital_in import discover_digital_ins, handle_digital_in_status_update
from .platforms.sicu import handle_security_status_update, discover_security
from .platforms.lights import discover_lights, handle_light_status_update 
from .platforms.thermoregulation import discover_thermostats, handle_thermostat_status_update
from .platforms.meters import discover_meters, handle_meter_status_update
from .platforms.openings import discover_openings, handle_opening_status_update
from .platforms.scenarios import discover_scenarios, handle_scenario_status_update
from .platforms.scheduler import discover_timers, handle_timer_status_update
from .platforms.tvcc import discover_tvcc_cameras
from .services.logger_security_events import SecurityEventsLogger
from .services.notifications import async_register_notification_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Domo from a config entry."""
    _LOGGER.debug("Setting up Domo integration via config flow")
    
    # Initialize data structures
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(CONF_PENDING, {})
    
    # Create gateway with data from config entry
    gateway = DomoGateway(
        hass,
        host=entry.data["host"],
        username=entry.data["username"],
        password=entry.data["password"],
    )
    
    # Register callbacks and start
    gateway.register_event_callback(handle_activation_status_update)
    gateway.register_event_callback(handle_analogic_status_update)
    gateway.register_event_callback(handle_digital_in_status_update)
    gateway.register_event_callback(handle_security_status_update)
    gateway.register_event_callback(handle_light_status_update)
    gateway.register_event_callback(handle_thermostat_status_update)
    gateway.register_event_callback(handle_meter_status_update)
    gateway.register_event_callback(handle_opening_status_update)
    gateway.register_event_callback(handle_scenario_status_update)
    gateway.register_event_callback(handle_timer_status_update)
    
    await gateway.start()
    await async_register_notification_services(hass, gateway)
    
    await discover_activations(gateway)
    await discover_analogics(gateway)
    await discover_digital_ins(gateway)
    await discover_lights(gateway)
    await discover_security(gateway)
    await discover_thermostats(gateway)
    await discover_meters(gateway)
    await discover_openings(gateway)
    await discover_scenarios(gateway)
    await discover_timers(gateway)
    await discover_tvcc_cameras(gateway)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)    
    
    hass.data[DOMAIN][entry.entry_id] = gateway   
    
    _LOGGER.debug("Initializing Security events logger")
    SecurityEventsLogger(hass)    
    

    _LOGGER.info("DOMO integration initialized")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Domo integration")
    
    # Stop gateway
    domo_gateway = hass.data[DOMAIN].pop(entry.entry_id)
    await domo_gateway.stop()
    
    # Unload plarforms
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # If no other entries remain, clean up
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)
    
    return True
