"""
domo/services/thermo_backup.py

Backup and restore of thermostat weekly heating profiles (Mon-Sun, excludes
Jolly) and t1/t2/t3 setpoints across all thermostats.

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues

status: passed
"""
from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

from ..const import SIGNAL_UPDATE_ENTITY
from ..platforms.thermoregulation import get_all_thermostats

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== SHARED HELPERS =====
# ============================================================

def _backup_dir(hass: HomeAssistant) -> Path:
    """Return the backup directory path (no I/O)."""
    return Path(hass.config.path(BACKUP_DIR_NAME))


def _current_season_tag() -> str:
    """Season currently set on the system (same for all thermostats)."""
    thermostats = get_all_thermostats()
    season = thermostats[0].season if thermostats else "winter"
    return "summer" if season == "summer" else "winter"


# ============================================================
# ===== BACKUP FILES CACHE =====
# ============================================================

BACKUP_DIR_NAME = "thermo_profile_bk"
_WEEKDAY_IDS = range(7)

_backup_files_cache: list[str] = []


async def async_refresh_backup_files_cache(hass: HomeAssistant) -> None:
    """Reload the on-disk backup file list into the in-memory cache."""
    global _backup_files_cache

    def _scan() -> list[str]:
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


def list_backup_files(hass: HomeAssistant) -> list[str]:
    """List cached backup files for the currently set season, newest first."""
    season_tag = _current_season_tag()
    suffix = f"_thermo_{season_tag}_bk.json"
    return [f for f in _backup_files_cache if f.endswith(suffix)]


# ============================================================
# ===== RESTORE FILE SELECTION =====
# ============================================================

RESTORE_PLACEHOLDER = "__select_file__"

_selected_restore_file: str | None = None


def get_selected_restore_file() -> str | None:
    return _selected_restore_file


def set_selected_restore_file(filename: str) -> None:
    global _selected_restore_file
    _selected_restore_file = None if filename == RESTORE_PLACEHOLDER else filename


# ============================================================
# ===== RESTORE STATUS =====
# ============================================================

RESTORE_STATUS_RESET_DELAY = 4
RESTORE_VERIFY_TIMEOUT = 15

_restore_status: str | None = None


def get_restore_status() -> str | None:
    return _restore_status


def _set_restore_status(hass: HomeAssistant, message: str | None) -> None:
    global _restore_status
    _restore_status = message
    async_dispatcher_send(hass, SIGNAL_UPDATE_ENTITY, "thermo_restore_status")


# ============================================================
# ===== BACKUP =====
# ============================================================

def _build_backup_zones() -> dict[str, Any]:
    zones: dict[str, Any] = {}
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
    """Save a backup of t1/t2/t3 and heating profiles (Mon-Sun) for all
    thermostats. Returns the created file name."""
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
    _LOGGER.info("THERMO BACKUP: saved %s (%d thermostats)", filename, len(zones))
    return filename


# ============================================================
# ===== RESTORE =====
# ============================================================

async def async_restore_thermal_profiles(hass: HomeAssistant, filename: str) -> None:
    """Restore t1/t2/t3 and heating profiles (Mon-Sun), verify the confirmed
    updates from the bus (gateway push) and publish a transient outcome
    message on the select."""
    path = _backup_dir(hass) / filename

    def _read() -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Backup file not found: {filename}")
        return json.loads(path.read_text())

    data = await hass.async_add_executor_job(_read)
    zones = data.get("zones", {})
    thermostats = {str(t.act_id): t for t in get_all_thermostats()}
    _set_restore_status(hass, "in_progress")

    pending: dict[str, dict[str, Any]] = {}
    events: dict[str, asyncio.Event] = {}

    def _matches(thermostat, expected: dict[str, Any]) -> bool:
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
                "THERMO RESTORE VERIFY %s: expected t1=%s t2=%s t3=%s days=%s | current t1=%s t2=%s t3=%s days=%s | match=%s",
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
                _LOGGER.warning("THERMO RESTORE: thermostat act_id=%s not found, skipping", act_id_str)
                continue

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
        _LOGGER.warning("THERMO RESTORE: verification not confirmed by bus for: %s", failed_names)
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
                        "THERMO RESTORE VERIFY FAIL %s: %s expected=%s current=%s",
                        thermostat.name, key, exp_val, act_val,
                    )
            for day_id_str, exp_profile in expected.get("profiles", {}).items():
                act_profile = thermostat.profile_raw_by_day.get(int(day_id_str))
                if act_profile != exp_profile:
                    _LOGGER.warning(
                        "THERMO RESTORE VERIFY FAIL %s: day=%s expected=%r current=%r",
                        thermostat.name, day_id_str, exp_profile, act_profile,
                    )
        _set_restore_status(hass, "verify_failed")
    else:
        _LOGGER.info("THERMO RESTORE: restored and verified %s (%d thermostats)", filename, len(zones))
        _set_restore_status(hass, "done")

    async def _reset_status() -> None:
        await asyncio.sleep(RESTORE_STATUS_RESET_DELAY)
        global _selected_restore_file
        _selected_restore_file = None
        _set_restore_status(hass, None)

    hass.async_create_task(_reset_status())
