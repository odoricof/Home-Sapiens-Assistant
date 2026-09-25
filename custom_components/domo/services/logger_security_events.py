"""
domo/services/logger_security_events.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues

status: passed
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import SIGNAL_UPDATE_ENTITY
from ..platforms.sicu import AREA_STATUS_MAP, CENTRAL_STATUS_MAP, INPUT_STATUS_MAP, get_security_device

_LOGGER = logging.getLogger(__name__)


EVENT_LOG_PATH: Path | None = None


# ============================================================
# ===== FILE LOGGER =====
# ============================================================

_event_logger = logging.getLogger("security_events")
_event_logger.setLevel(logging.INFO)
_event_logger.propagate = False


def _setup_file_logger(hass: HomeAssistant) -> None:
    """Create the log directory and file handler. Runs in executor."""
    global EVENT_LOG_PATH
    if _event_logger.handlers:
        return

    EVENT_LOG_PATH = Path(hass.config.path("security_events_logs", "security_events.log"))
    EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    handler = TimedRotatingFileHandler(
        EVENT_LOG_PATH,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
        utc=False,
        delay=True,
    )
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    _event_logger.addHandler(handler)

    header = "DATE,TIME,CENTRAL,RAW CENTRAL,CENTRAL STATUS,AREA,RAW AREA,AREA STATUS,INPUT,RAW INPUT,INPUT STATUS"
    _event_logger.info(header)

    _LOGGER.info("SECURITY EVENTS LOGGER: file log initialized at %s", EVENT_LOG_PATH)


# ============================================================
# ===== LOGGER SERVICE =====
# ============================================================

class SecurityEventsLogger:
    """Writes a CSV audit trail of security system state changes to disk."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._last_snapshot = None
        self._last_log_key = None

        hass.add_job(_setup_file_logger, hass)

        self._unsub_dispatcher = async_dispatcher_connect(
            hass,
            SIGNAL_UPDATE_ENTITY,
            self._handle_update,
        )

    def unload(self) -> None:
        """Disconnect the dispatcher listener. Call on integration unload/reload."""
        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    @callback
    def _handle_update(self, entity_id: str = None) -> None:
        if entity_id is not None and entity_id != "security_central":
            return
        central = get_security_device()
        if not central:
            return

        data = getattr(central, "_last_snapshot", None)
        if not data:
            return

        prev = self._last_snapshot or {}
        if prev == data:
            return

        c = data.get("central", {}) or {}
        raw_central = c.get("status")

        if raw_central == 256:
            self._last_snapshot = data
            return

        now = datetime.now()
        date = now.strftime("%d.%m.%Y")
        time = now.strftime("%H:%M:%S")

        log_parts = [date, time]

        if raw_central is not None:
            central_name = c.get("name", "CENTRAL")

            log_parts.extend([
                central_name,
                str(raw_central),
                CENTRAL_STATUS_MAP.get(raw_central, f"unknown_{raw_central}")
            ])
        else:
            log_parts.extend(["", "", ""])

        areas = data.get("areas", [])
        if areas:
            for a in areas:
                raw_area = a.get("status")
                name_area = a.get("name") or a.get("area_name") or f"area_{a.get('area_id')}"
                log_parts.extend([
                    name_area,
                    str(raw_area),
                    AREA_STATUS_MAP.get(raw_area, f"unknown_{raw_area}")
                ])
        else:
            log_parts.extend(["", "", ""])

        inputs = data.get("inputs", [])
        if inputs:
            filtered_inputs = [i for i in inputs if i.get("status") != 1]

            if filtered_inputs:
                for i in filtered_inputs:
                    raw_input = i.get("status")
                    name_input = i.get("name") or i.get("input_name") or f"input_{i.get('input_id')}"
                    log_parts.extend([
                        name_input,
                        str(raw_input),
                        INPUT_STATUS_MAP.get(raw_input, f"unknown_{raw_input}")
                    ])
        else:
            log_parts.extend(["", "", ""])

        log_line = ",".join(str(part) for part in log_parts)

        data_hash = hashlib.md5(str(data).encode()).hexdigest()[:8]
        current_key = f"{time}_{data_hash}"

        if current_key == self._last_log_key:
            return

        self.hass.add_job(_event_logger.info, log_line)
        self._last_log_key = current_key
        self._last_snapshot = data
