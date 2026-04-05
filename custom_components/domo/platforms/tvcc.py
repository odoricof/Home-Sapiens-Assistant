"""
platforms/tvcc.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)

_TVCC_CAMERAS: dict[int, DomoTVCamera] = {}


class DomoTVCamera:
    """Telecamera TVCC ETI Domo."""

    def __init__(self, gateway, camera_data: Dict[str, Any]):
        """Inizializza una telecamera."""
        self._gateway = gateway
        self._camera_id = camera_data["id"]
        self._name = camera_data.get("name", f"Camera {self._camera_id}")
        self._stream_type = camera_data.get("stream_type", "mjpg")
        self._uri = camera_data.get("uri")
        self._uri2 = camera_data.get("uri2")
        self._uri_still = camera_data.get("uri_still")
        self._proxy1 = camera_data.get("proxy1")
        self._proxy2 = camera_data.get("proxy2")
        self._proxy_still = camera_data.get("proxy_still")
        
        _TVCC_CAMERAS[self._camera_id] = self
        
        _LOGGER.debug("TVCC CAMERA created: %s (ID: %d) - stream_type: %s", 
                     self._name, self._camera_id, self._stream_type)

    @property
    def camera_id(self) -> int:
        return self._camera_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"camera.domo_{self._camera_id}"

    @property
    def stream_type(self) -> str:
        return self._stream_type

    @property
    def uri(self) -> str | None:
        return self._uri

    @property
    def uri2(self) -> str | None:
        return self._uri2

    @property
    def uri_still(self) -> str | None:
        return self._uri_still

    @property
    def proxy1(self) -> str | None:
        return self._proxy1

    @property
    def proxy2(self) -> str | None:
        return self._proxy2

    @property
    def proxy_still(self) -> str | None:
        return self._proxy_still


async def discover_tvcc_cameras(gateway):
    """Scopri tutte le telecamere TVCC disponibili."""
    _LOGGER.debug("Discovering TVCC cameras")
    
    try:
        resp = await gateway.tx_command({
            "cmd_name": "tvcc_cameras_list_req",
            "username": "admin"
        }, resp_command="tvcc_cameras_list_resp")
        
        if not resp:
            _LOGGER.error("No response from gateway")
            return []
        
        cameras = []
        for item in resp.get("array", []):
            camera = DomoTVCamera(gateway, item)
            cameras.append(camera)
        
        _LOGGER.debug("Discovered %d TVCC cameras", len(cameras))
        return cameras
        
    except Exception as err:
        _LOGGER.error("TVCC cameras discovery failed: %s", err)
        return []


def get_all_tvcc_cameras() -> List[DomoTVCamera]:
    """Restituisce tutte le telecamere TVCC."""
    return list(_TVCC_CAMERAS.values())


def get_tvcc_camera(camera_id: int) -> Optional[DomoTVCamera]:
    """Restituisce una telecamera per ID."""
    return _TVCC_CAMERAS.get(camera_id)
