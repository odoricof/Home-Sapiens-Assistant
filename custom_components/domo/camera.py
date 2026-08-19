"""
domo/camera.py

Entities fed by:
- platforms/tvcc.py

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
import aiohttp

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.tvcc import DomoTVCamera, get_all_tvcc_cameras

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the camera platform for TVCC cameras."""
    cameras = get_all_tvcc_cameras()
    if not cameras:
        _LOGGER.debug("No TVCC cameras found")
        return

    cameras_device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_cameras")},
        name="Cameras",
        manufacturer="Home Sapiens Assistant",
        model="Eti/Domo",
    )

    entities = [
        DomoCameraEntity(camera, cameras_device_info)
        for camera in cameras
    ]
    async_add_entities(entities)

    _LOGGER.info("Added %d camera entities for TVCC cameras", len(entities))


# ============================================================
# ===== TVCC CAMERAS =====
# ============================================================

class DomoCameraEntity(Camera):
    """Camera entity for Domo TVCC cameras."""

    def __init__(self, camera: DomoTVCamera, device_info: DeviceInfo):
        """Initialize the camera entity."""
        super().__init__()
        self._camera = camera
        self._attr_unique_id = camera.unique_id
        self._attr_name = camera.name
        self._attr_device_info = device_info
        self._attr_is_streaming = True

        self._stream_source = camera.uri2 if camera.uri2 else camera.uri

        if self._stream_source:
            self._attr_supported_features = CameraEntityFeature.STREAM

        _LOGGER.debug(
            "Created camera entity: %s - low quality stream: %s",
            self._attr_name,
            self._stream_source,
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Additional attributes for the camera."""
        attrs = {
            "camera_id": self._camera.camera_id,
            "stream_type": self._camera.stream_type,
            "uri_still": self._camera.uri_still,
        }

        if self._camera.uri:
            attrs["stream_high_quality"] = self._camera.uri

        return attrs

    async def async_camera_image(self, width=None, height=None):
        """Return still image."""
        if not self._camera.uri_still:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self._camera.uri_still) as resp:
                    return await resp.read()
        except Exception as err:
            _LOGGER.error("Error retrieving image: %s", err)
            return None

    async def stream_source(self) -> str | None:
        """Return the stream URL."""
        return self._camera.uri

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update)
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        if entity_id is None or entity_id == self._attr_unique_id:
            self.async_write_ha_state()
