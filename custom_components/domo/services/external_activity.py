"""
domo/services/external_activity.py

Gives a cause to every state change that Home Assistant did not ask for
(wall buttons, official app, gateway scenarios): the change keeps its normal
text (e.g. "Off") and its "What happened" section shows the integration logo
as the author, like it does for a user action.

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
from collections import deque
from collections.abc import Callable

from homeassistant.const import (
    ATTR_DOMAIN,
    ATTR_ENTITY_ID,
    ATTR_SERVICE,
    ATTR_SERVICE_DATA,
    EVENT_CALL_SERVICE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.helpers import entity_platform, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import CONTEXT_RECENT_TIME_SECONDS, Entity

from ..const import DOMAIN, SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== CONSTANTS =====
# ============================================================

SERVICE_EXTERNAL_ACTION = "external_action"

EXTERNAL_ACTIVITY_DOMAINS = (
    "alarm_control_panel",
    "climate",
    "cover",
    "light",
    "switch",
)


# ============================================================
# ===== HELPERS =====
# ============================================================

def _has_recent_ha_context(entity: Entity, own_context_ids: deque[str]) -> bool:
    """Return True when a command, automation or user acted on the entity just now."""
    if not hasattr(entity, "_context") or not hasattr(entity, "_context_set"):
        return True
    context = entity._context
    context_set = entity._context_set
    if context is None or context_set is None or context.id in own_context_ids:
        return False
    return time.time() - context_set <= CONTEXT_RECENT_TIME_SECONDS


# ============================================================
# ===== SETUP =====
# ============================================================

@callback
def async_setup_external_activity(hass: HomeAssistant) -> Callable[[], None]:
    """Start watching gateway updates and return the function that stops it."""
    entity_registry = er.async_get(hass)
    own_context_ids: deque[str] = deque(maxlen=256)

    @callback
    def _entities_for(unique_id: str | None) -> list[Entity]:
        """Entities of the chosen domains touched by this gateway update."""
        platforms = [
            platform
            for platform in entity_platform.async_get_platforms(hass, DOMAIN)
            if platform.domain in EXTERNAL_ACTIVITY_DOMAINS
        ]
        if unique_id is None:
            return [e for p in platforms for e in p.entities.values()]
        for domain in EXTERNAL_ACTIVITY_DOMAINS:
            entity_id = entity_registry.async_get_entity_id(domain, DOMAIN, unique_id)
            if entity_id is None:
                continue
            for platform in platforms:
                if (entity := platform.entities.get(entity_id)) is not None:
                    return [entity]
        return []

    @callback
    def _mark_if_external(entity: Entity) -> None:
        """Give the upcoming state change a cause when nothing in HA asked for it."""
        if _has_recent_ha_context(entity, own_context_ids):
            return

        current = hass.states.get(entity.entity_id)
        if current is None or current.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        try:
            if not entity.available:
                return
            upcoming = entity.state
        except Exception:
            return
        if upcoming is None or str(upcoming) == current.state:
            return

        context = Context()
        own_context_ids.append(context.id)
        hass.bus.async_fire(
            EVENT_CALL_SERVICE,
            {
                ATTR_DOMAIN: DOMAIN,
                ATTR_SERVICE: SERVICE_EXTERNAL_ACTION,
                ATTR_SERVICE_DATA: {ATTR_ENTITY_ID: entity.entity_id},
            },
            context=context,
        )
        entity.async_set_context(context)

    @callback
    def _handle_gateway_update(unique_id: str | None = None, *_: object) -> None:
        """Runs before the entities write their state (it is connected first)."""
        for entity in _entities_for(unique_id if isinstance(unique_id, str) else None):
            _mark_if_external(entity)

    unsub_dispatcher = async_dispatcher_connect(
        hass, SIGNAL_UPDATE_ENTITY, _handle_gateway_update
    )

    return unsub_dispatcher
