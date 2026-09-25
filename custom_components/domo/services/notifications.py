"""
services/notifications.py

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
import time
from collections.abc import Callable
from typing import Any

from homeassistant.components.persistent_notification import async_create
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import SIGNAL_GATEWAY_OFFLINE, SIGNAL_GATEWAY_ONLINE

_LOGGER = logging.getLogger(__name__)

NOTIFICATION_TITLE = "Home Sapiens Assistant"
COLOR_ONLINE = "#00FF00"
COLOR_OFFLINE = "#FF0000"


# ============================================================
# ===== MOBILE NOTIFICATIONS =====
# ============================================================

async def _async_send_to_all_mobiles(
    hass: HomeAssistant, title: str, message: str, color: str
) -> None:
    """Send a high-priority notification to every registered mobile_app device."""
    all_services = hass.services.async_services()
    mobile_app_services = [
        service
        for service in all_services.get("notify", [])
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
                        "color": color,
                    },
                },
                blocking=False,
            )
        except Exception as err:
            _LOGGER.warning("Error sending notification to %s: %s", service, err)


# ============================================================
# ===== GATEWAY STATE HANDLERS =====
# ============================================================

async def _async_notify_gateway_state(hass: HomeAssistant, online: bool) -> None:
    """Create a persistent notification and push it to mobile devices."""
    timestamp = time.strftime("%d/%m/%Y - %H:%M:%S")

    if online:
        message = f"🟢 ETI/DOMO ONLINE - {timestamp}"
        notification_id = "domo_gateway_online"
        color = COLOR_ONLINE
    else:
        message = f"🔴 ETI/DOMO OFFLINE - {timestamp}"
        notification_id = "domo_gateway_offline"
        color = COLOR_OFFLINE

    async_create(
        hass,
        message=message,
        title=NOTIFICATION_TITLE,
        notification_id=notification_id,
    )

    await _async_send_to_all_mobiles(hass, NOTIFICATION_TITLE, message, color)


# ============================================================
# ===== SERVICE REGISTRATION =====
# ============================================================

async def async_register_notification_services(
    hass: HomeAssistant, gateway: Any
) -> list[Callable[[], None]]:
    """Register gateway online/offline notifications and return their unsubscribe callables."""

    async def _online_handler() -> None:
        await _async_notify_gateway_state(hass, True)

    async def _offline_handler() -> None:
        await _async_notify_gateway_state(hass, False)

    unsubscribers = [
        async_dispatcher_connect(hass, SIGNAL_GATEWAY_ONLINE, _online_handler),
        async_dispatcher_connect(hass, SIGNAL_GATEWAY_OFFLINE, _offline_handler),
    ]

    _LOGGER.info("DOMO notification services registered")
    return unsubscribers
