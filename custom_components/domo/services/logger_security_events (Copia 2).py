"""
Security events logger Proxinet.

For more details about this platform, please refer to the documentation at
https://github.com/odoricof/xxx
"""

from __future__ import annotations

import logging
import hashlib  # OK: importato una sola volta
from pathlib import Path
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import DOMAIN, SIGNAL_UPDATE_ENTITY
from ..platforms.sicu import get_security_device

from ..alarm_control_panel import AREA_STATUS_MAP, INPUT_STATUS_MAP, CENTRAL_STATUS_MAP


_LOGGER = logging.getLogger(__name__)

EVENT_LOG_PATH = Path("/config/security_events_logs/security_events.log")
EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# FILE LOGGER
# ============================================================

_event_logger = logging.getLogger("security_events")
_event_logger.setLevel(logging.INFO)
_event_logger.propagate = False

if not _event_logger.handlers:
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
    
    # Scrivi l'intestazione all'inizio del file
    header = "DATA,ORA,CENTRALE,RAW CENTRALE,STATO CENTRALE,AREA,RAW AREA,STATO AREA,INGRESSO,RAW INGRESSO,STATO INGRESSO"
    _event_logger.info(header)

# ============================================================
# LOGGER SERVICE
# ============================================================

class SecurityEventsLogger:
    def __init__(self, hass):
        self.hass = hass
        self._last_snapshot = None
        self._last_log_key = None  # Chiave unica per l'ultimo log (timestamp + hash)

        async_dispatcher_connect(
            hass,
            SIGNAL_UPDATE_ENTITY,
            self._handle_update,
        )

    def _handle_update(self):
        central = get_security_device()
        if not central:
            return

        data = getattr(central, "_last_snapshot", None)
        if not data:
            return

        prev = self._last_snapshot or {}
        
        # Verifica se ci sono cambiamenti rispetto allo snapshot precedente
        if prev == data:
            return  # Nessun cambiamento, non loggare

        now = datetime.now()
        date = now.strftime("%d.%m.%Y")
        time = now.strftime("%H:%M:%S")
        
        # Inizia con data e ora
        log_parts = [date, time]
        
        # ---------------- CENTRALE ----------------
        c = data.get("central", {}) or {}
        raw_central = c.get("status")
        if raw_central is not None:
            log_parts.extend([
                "CENTRALE",
                str(raw_central),
                CENTRAL_STATUS_MAP.get(raw_central, f"sconosciuto_{raw_central}")
            ])
        else:
            log_parts.extend(["", "", ""])

        # ---------------- TUTTE LE AREE ----------------
        areas = data.get("areas", [])
        if areas:
            for a in areas:
                raw_area = a.get("status")
                name_area = a.get("name") or a.get("area_name") or f"area_{a.get('area_id')}"
                log_parts.extend([
                    name_area,
                    str(raw_area),
                    AREA_STATUS_MAP.get(raw_area, f"sconosciuto_{raw_area}")
                ])
        else:
            log_parts.extend(["", "", ""])  # Un set di campi vuoti se non ci sono aree

        # ---------------- TUTTI GLI INGRESSI ----------------
        inputs = data.get("inputs", [])
        if inputs:
            for i in inputs:
                raw_input = i.get("status")
                name_input = i.get("name") or i.get("input_name") or f"input_{i.get('input_id')}"
                log_parts.extend([
                    name_input,
                    str(raw_input),
                    INPUT_STATUS_MAP.get(raw_input, f"sconosciuto_{raw_input}")
                ])
        else:
            log_parts.extend(["", "", ""])  # Un set di campi vuoti se non ci sono ingressi

        # Crea la stringa da loggare
        log_line = ",".join(str(part) for part in log_parts)
        
        # Evita duplicati nello stesso timestamp
        data_hash = hashlib.md5(str(data).encode()).hexdigest()[:8]
        current_key = f"{time}_{data_hash}"  # Chiave: timestamp + hash
        
        # Se è lo stesso identico evento nello stesso secondo, salta
        if current_key == self._last_log_key:
            return
            
        _event_logger.info(log_line)
        self._last_log_key = current_key  # Aggiorna l'ultima chiave
        self._last_snapshot = data
