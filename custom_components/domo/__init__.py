from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .gateway import DomoGateway
from .const import DOMAIN, CONF_PENDING, PLATFORMS
from .platforms.sicu import handle_security_status_update
from .platforms.sicu import discover_security
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
    gateway.register_event_callback(handle_security_status_update)
    await gateway.start()

    # Update security platform
    await discover_security(gateway)

    # Salva riferimento
    hass.data[DOMAIN][entry.entry_id] = gateway
    hass.data[DOMAIN]["gateway"] = gateway  # Per compatibilità con codice esistente

    # Inizializza il logger eventi
    _LOGGER.debug("Initializing Security events logger")
    SecurityEventsLogger(hass)
    
    # Forward setup alle piattaforme
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
