"""
services/notifications.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""

import time
import logging
from homeassistant.core import HomeAssistant
from homeassistant.components.persistent_notification import async_create
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import SIGNAL_GATEWAY_ONLINE, SIGNAL_GATEWAY_OFFLINE

_LOGGER = logging.getLogger(__name__)


async def async_register_notification_services(hass: HomeAssistant, gateway):
    """Register notification services using the gateway."""
    
    async def send_to_all_mobiles(title: str, message: str):
        """Send notification to all mobile devices."""
        all_services = hass.services.async_services()
        mobile_app_services = [
            service for service in all_services.get("notify", [])
            if service.startswith("mobile_app_")
        ]
        
        if not mobile_app_services:
            _LOGGER.debug("No mobile_app devices registered")
            return
        
        for service in mobile_app_services:
            try:
                await hass.services.async_call(
                    "notify",
                    service,
                    {
                        "title": title,
                        "message": message,
                        "data": {
                            "priority": "high",
                            "importance": "max",
                            "color": "#FF0000" if "OFFLINE" in title else "#00FF00"
                        }
                    },
                    blocking=False
                )
            except Exception as err:
                _LOGGER.debug("Error sending notification to %s: %s", service, err)
    
    async def handle_online_offline_notification(event: str):
        """Handle online/offline state change notifications."""
        timestamp = time.strftime("%d/%m/%Y - %H:%M:%S")
        
        if event == "online":
            title = "Home Sapiens Assistant"
            message = f"🟢 ETI/DOMO ONLINE - {timestamp}"
            notification_id = "domo_gateway_online"
        else:
            title = "Home Sapiens Assistant"  
            message = f"🔴 ETI/DOMO OFFLINE - {timestamp}"
            notification_id = "domo_gateway_offline"
        

        async_create(
            hass,
            message=message,
            title=title,
            notification_id=notification_id
        )
        
        await send_to_all_mobiles(title, message)
    
    async def online_handler():
        await handle_online_offline_notification("online")
        
    async def offline_handler():
        await handle_online_offline_notification("offline")
    
    async_dispatcher_connect(hass, SIGNAL_GATEWAY_ONLINE, online_handler)
    async_dispatcher_connect(hass, SIGNAL_GATEWAY_OFFLINE, offline_handler)
    
    _LOGGER.info("DOMO notification services registered")
