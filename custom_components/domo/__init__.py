"""
domo/__init__.py

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

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import CONF_PENDING, DOMAIN, PLATFORMS, SIGNAL_GATEWAY_ONLINE
from .gateway import DomoGateway
from .platforms.activations import discover_activations, handle_activation_status_update, refresh_all_activations
from .platforms.analogics import discover_analogics, handle_analogic_status_update, refresh_all_analogics
from .platforms.digital_in import discover_digital_ins, handle_digital_in_status_update, refresh_all_digital_ins
from .platforms.irrigation import discover_irrigation_zones, handle_irrigation_status_update, refresh_all_irrigation
from .platforms.lights import discover_lights, handle_light_status_update, refresh_all_lights
from .platforms.loadsctrl import discover_loadsctrl, handle_loadsctrl_status_update, refresh_all_loadsctrl
from .platforms.meters import discover_meters, handle_meter_status_update
from .platforms.openings import discover_openings, handle_opening_status_update, refresh_all_openings
from .platforms.scenarios import discover_scenarios, handle_scenario_status_update
from .platforms.scheduler import discover_timers, handle_timer_status_update, refresh_all_timers
from .platforms.sicu import discover_security, handle_security_status_update, refresh_all_security
from .platforms.thermoregulation import discover_thermostats, handle_thermostat_status_update, refresh_all_thermostats
from .platforms.tvcc import discover_tvcc_cameras
from .services.logger_security_events import SecurityEventsLogger
from .services.notifications import async_register_notification_services

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Domo from a config entry."""
    _LOGGER.debug("Setting up Domo integration via config flow")

    # --- Initialize data structures ---
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(CONF_PENDING, {})

    # --- Create gateway ---
    gateway = DomoGateway(
        hass,
        host=entry.data["host"],
        username=entry.data["username"],
        password=entry.data["password"],
    )

    # --- Register callbacks and start ---
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
    gateway.register_event_callback(handle_irrigation_status_update)
    gateway.register_event_callback(handle_loadsctrl_status_update)

    await gateway.start()
    for unsub in await async_register_notification_services(hass, gateway):
        entry.async_on_unload(unsub)
        
    async def _handle_gateway_reconnect() -> None:
        _LOGGER.info("DOMO gateway back online, resyncing entity states")
        await refresh_all_lights(gateway)
        await refresh_all_activations(gateway)
        await refresh_all_digital_ins(gateway)
        await refresh_all_thermostats(gateway)
        await refresh_all_security(gateway)
        await refresh_all_irrigation(gateway)
        await refresh_all_timers(gateway)
        await refresh_all_loadsctrl(gateway)
        await refresh_all_openings(gateway)
        await refresh_all_analogics(gateway)

    unsub_gateway_reconnect = async_dispatcher_connect(hass, SIGNAL_GATEWAY_ONLINE, _handle_gateway_reconnect)
    hass.data[DOMAIN].setdefault("unsub_dispatchers", {})[entry.entry_id] = unsub_gateway_reconnect

    # --- Discover entities ---
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
    await discover_irrigation_zones(gateway)
    await discover_loadsctrl(gateway)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    hass.data[DOMAIN][entry.entry_id] = gateway

    _LOGGER.debug("Initializing Security events logger")
    security_logger = SecurityEventsLogger(hass)
    hass.data[DOMAIN].setdefault("security_loggers", {})[entry.entry_id] = security_logger

    _LOGGER.info("DOMO integration initialized")
    return True


# ============================================================
# ===== UNLOAD ENTRY =====
# ============================================================

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Domo integration")

    # --- Stop gateway reconnect listener ---
    unsub_gateway_reconnect = hass.data[DOMAIN].get("unsub_dispatchers", {}).pop(entry.entry_id, None)
    if unsub_gateway_reconnect is not None:
        unsub_gateway_reconnect()

    # --- Stop security events logger ---
    security_logger = hass.data[DOMAIN].get("security_loggers", {}).pop(entry.entry_id, None)
    if security_logger is not None:
        security_logger.unload()

    # --- Stop gateway ---
    domo_gateway = hass.data[DOMAIN].pop(entry.entry_id)
    await domo_gateway.stop()

    # --- Unload platforms ---
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # --- Cleanup ---
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return True
