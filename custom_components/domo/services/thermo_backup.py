"""
domo/services/thermo_backup.py

Backup/restore dei profili termici (Lun-Dom, esclude Jolly) e dei set-point
t1/t2/t3 di tutti i termostati.

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

from ..const import SIGNAL_UPDATE_ENTITY
from ..platforms.thermoregulation import get_all_thermostats

_LOGGER = logging.getLogger(__name__)

BACKUP_DIR_NAME = "thermo_profile_bk"
_WEEKDAY_IDS = range(7)  # 0-6 = Lun..Dom. Esclude 7 = Jolly.

# Cache in memoria dei nomi dei file di backup trovati su disco, ordinati per data
# di modifica. Popolata/aggiornata SOLO da async_refresh_backup_files_cache (che
# gira in executor): list_backup_files non deve mai fare I/O diretto, perché la
# property 'options' dei select entity è sincrona e gira nell'event loop.
_backup_files_cache: List[str] = []

# Stato del file selezionato per il restore (letto/scritto dal select entity,
# consumato dal button entity — stesso pattern del dict globale _THERMOSTATS).
RESTORE_PLACEHOLDER = "-- seleziona un file --"

_selected_restore_file: Optional[str] = None


def get_selected_restore_file() -> Optional[str]:
    return _selected_restore_file


def set_selected_restore_file(filename: str) -> None:
    global _selected_restore_file
    _selected_restore_file = None if filename == RESTORE_PLACEHOLDER else filename


# Messaggio temporaneo di esito restore, mostrato sul select al posto del file scelto.
RESTORE_STATUS_RESET_DELAY = 4  # secondi prima di tornare al placeholder
RESTORE_VERIFY_TIMEOUT = 15  # secondi di attesa conferma dal bus per termostato

_restore_status: Optional[str] = None


def get_restore_status() -> Optional[str]:
    return _restore_status


def _set_restore_status(hass: HomeAssistant, message: Optional[str]) -> None:
    global _restore_status
    _restore_status = message
    async_dispatcher_send(hass, SIGNAL_UPDATE_ENTITY, "thermo_restore_status")


def _backup_dir(hass: HomeAssistant) -> Path:
    """Restituisce il path della cartella di backup (nessun I/O: la creazione
    della cartella avviene solo nei punti che già girano in executor)."""
    return Path(hass.config.path(BACKUP_DIR_NAME))


def _current_season_tag() -> str:
    """Stagione dell'impianto (uguale per tutti i termostati)."""
    thermostats = get_all_thermostats()
    season = thermostats[0].season if thermostats else "winter"
    return "summer" if season == "summer" else "winter"


def _build_backup_zones() -> Dict[str, Any]:
    zones: Dict[str, Any] = {}
    for thermostat in get_all_thermostats():
        profiles = {
            str(day_id): raw
            for day_id, raw in thermostat.profile_raw_by_day.items()
            if day_id in _WEEKDAY_IDS and raw
        }
        zones[str(thermostat.act_id)] = {
            "name": thermostat.name,
            "t1": thermostat.t1_raw,
            "t2": thermostat.t2_raw,
            "t3": thermostat.t3_raw,
            "profiles": profiles,
        }
    return zones


async def async_backup_thermal_profiles(hass: HomeAssistant) -> str:
    """Salva un backup di t1/t2/t3 e profili termici (Lun-Dom) di tutti i termostati.
    Restituisce il nome del file creato."""
    zones = _build_backup_zones()
    season_tag = _current_season_tag()
    filename = f"{datetime.now():%Y%m%d}_thermo_{season_tag}_bk.json"

    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "season": season_tag,
        "zones": zones,
    }

    path = _backup_dir(hass) / filename

    def _write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    await hass.async_add_executor_job(_write)
    await async_refresh_backup_files_cache(hass)
    _LOGGER.info("THERMO BACKUP: salvato %s (%d termostati)", filename, len(zones))
    return filename


async def async_refresh_backup_files_cache(hass: HomeAssistant) -> None:
    """Ricarica dal disco la cache dei file di backup. Fa I/O (scandir/stat), quindi
    va sempre chiamata da codice async — mai dalla property 'options', sincrona."""
    global _backup_files_cache

    def _scan() -> List[str]:
        directory = Path(hass.config.path(BACKUP_DIR_NAME))
        if not directory.exists():
            return []
        files = sorted(
            directory.glob("*_thermo_*_bk.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return [f.name for f in files]

    _backup_files_cache = await hass.async_add_executor_job(_scan)


def list_backup_files(hass: HomeAssistant) -> List[str]:
    """Elenca (dalla cache in memoria, nessun I/O) i file di backup disponibili per
    la stagione attualmente impostata sull'impianto, più recente prima. I file
    dell'altra stagione sono nascosti per evitare ripristini incrociati."""
    season_tag = _current_season_tag()
    suffix = f"_thermo_{season_tag}_bk.json"
    return [f for f in _backup_files_cache if f.endswith(suffix)]


async def async_restore_thermal_profiles(hass: HomeAssistant, filename: str) -> None:
    """Ripristina t1/t2/t3 e profili termici (Lun-Dom), verifica gli aggiornamenti confermati
    dal bus (push del gateway) e pubblica un messaggio di esito temporaneo sul select."""
    path = _backup_dir(hass) / filename

    def _read() -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"File di backup non trovato: {filename}")
        return json.loads(path.read_text())

    data = await hass.async_add_executor_job(_read)
    zones = data.get("zones", {})
    thermostats = {str(t.act_id): t for t in get_all_thermostats()}
    _set_restore_status(hass, "Ripristino in corso...")

    pending: Dict[str, Dict[str, Any]] = {}
    events: Dict[str, asyncio.Event] = {}

    def _matches(thermostat, expected: Dict[str, Any]) -> bool:
        for key, attr in (("t1", "t1_raw"), ("t2", "t2_raw"), ("t3", "t3_raw")):
            if expected.get(key) is not None and getattr(thermostat, attr) != expected[key]:
                return False
        for day_id_str, profile_data in expected.get("profiles", {}).items():
            if thermostat.profile_raw_by_day.get(int(day_id_str)) != profile_data:
                return False
        return True

    @callback
    def _on_update(entity_id: str = None) -> None:
        for act_id_str, event in events.items():
            if event.is_set():
                continue
            thermostat = thermostats.get(act_id_str)
            expected = pending.get(act_id_str)
            if thermostat is None or expected is None:
                continue
            if entity_id is not None and entity_id != thermostat.unique_id:
                continue
            match = _matches(thermostat, expected)
            _LOGGER.debug(
                "THERMO RESTORE VERIFY %s: atteso t1=%s t2=%s t3=%s giorni=%s | attuale t1=%s t2=%s t3=%s giorni=%s | match=%s",
                thermostat.name,
                expected.get("t1"), expected.get("t2"), expected.get("t3"),
                list(expected.get("profiles", {}).keys()),
                thermostat.t1_raw, thermostat.t2_raw, thermostat.t3_raw,
                list(thermostat.profile_raw_by_day.keys()),
                match,
            )
            if match:
                event.set()

    unsub = async_dispatcher_connect(hass, SIGNAL_UPDATE_ENTITY, _on_update)

    try:
        for act_id_str, zone_data in zones.items():
            thermostat = thermostats.get(act_id_str)
            if thermostat is None:
                _LOGGER.warning("THERMO RESTORE: termostato act_id=%s non trovato, salto", act_id_str)
                continue

            # IMPORTANTE: registrare pending/events PRIMA di scrivere. Le conferme
            # thermo_zone_info_ind arrivano dal gateway già durante le scritture
            # stesse (interleaved con gli await sottostanti), non dopo l'intera
            # sequenza: se registrate dopo, il callback le trova già passate.
            pending[act_id_str] = zone_data
            events[act_id_str] = asyncio.Event()

            for key in ("t1", "t2", "t3"):
                raw_value = zone_data.get(key)
                if raw_value is None:
                    continue
                await thermostat.async_set_thermal_profile_value(key, raw_value / 10.0)

            for day_id_str, profile_data in zone_data.get("profiles", {}).items():
                if not profile_data:
                    continue
                await thermostat.async_write_raw_profile(int(day_id_str), profile_data)

            # Il match potrebbe già essersi verificato durante le scritture stesse
            # (tutte le conferme ricevute prima che il loop finisca): controlliamo
            # subito per evitare di aspettare inutilmente fino al timeout.
            if not events[act_id_str].is_set() and _matches(thermostat, zone_data):
                events[act_id_str].set()

        results = await asyncio.gather(
            *(asyncio.wait_for(event.wait(), timeout=RESTORE_VERIFY_TIMEOUT) for event in events.values()),
            return_exceptions=True,
        )
        failed_ids = [
            act_id for act_id, result in zip(events.keys(), results) if isinstance(result, Exception)
        ]
    finally:
        unsub()

    if failed_ids:
        failed_names = [thermostats[a].name for a in failed_ids if a in thermostats]
        _LOGGER.warning("THERMO RESTORE: verifica non confermata dal bus per: %s", failed_names)
        for act_id_str in failed_ids:
            thermostat = thermostats.get(act_id_str)
            expected = pending.get(act_id_str)
            if thermostat is None or expected is None:
                continue
            for key, attr in (("t1", "t1_raw"), ("t2", "t2_raw"), ("t3", "t3_raw")):
                exp_val = expected.get(key)
                act_val = getattr(thermostat, attr)
                if exp_val is not None and act_val != exp_val:
                    _LOGGER.warning(
                        "THERMO RESTORE VERIFY FAIL %s: %s atteso=%s attuale=%s",
                        thermostat.name, key, exp_val, act_val,
                    )
            for day_id_str, exp_profile in expected.get("profiles", {}).items():
                act_profile = thermostat.profile_raw_by_day.get(int(day_id_str))
                if act_profile != exp_profile:
                    _LOGGER.warning(
                        "THERMO RESTORE VERIFY FAIL %s: giorno=%s atteso=%r attuale=%r",
                        thermostat.name, day_id_str, exp_profile, act_profile,
                    )
        _set_restore_status(hass, "Ripristino: verifica fallita")
    else:
        _LOGGER.info("THERMO RESTORE: ripristinato e verificato %s (%d termostati)", filename, len(zones))
        _set_restore_status(hass, "Ripristino eseguito")

    async def _reset_status() -> None:
        await asyncio.sleep(RESTORE_STATUS_RESET_DELAY)
        global _selected_restore_file
        _selected_restore_file = None
        _set_restore_status(hass, None)

    hass.async_create_task(_reset_status())
