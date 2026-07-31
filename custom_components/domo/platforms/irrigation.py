"""
domo/platforms/irrigation.py

Entities fed by this file:
- domo/number.py  : Seasonal percentage, Work cycle, Max irrigation time
- domo/switch.py  : Sector enable, Weekdays, Manual mode, Sprinklers enable
- domo/time.py    : Start time, End time

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_DISCOVERY_NEW, SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

_IRRIGATION_ZONES: Dict[int, "DomoIrrigationZone"] = {}


def _decode_days(days: int) -> List[str]:
    """Decodifica la bitmask 'days' nei giorni della settimana attivi."""
    return [WEEKDAYS[i] for i in range(7) if days & (1 << i)]


def _encode_day_change(current_days: int, day_index: int, value: int) -> int:
    """Calcola la nuova bitmask 'days' abilitando/disabilitando un singolo giorno,
    preservando lo stato degli altri giorni."""
    if value:
        return current_days | (1 << day_index)
    return current_days & ~(1 << day_index)


def _decode_time(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, int]]:
    """Normalizza un oggetto {hour,min,sec} del gateway.
    Il gateway usa -1 per 'non impostato': in tal caso restituisce None."""
    if not data:
        return None
    hour = data.get("hour", -1)
    if hour is None or hour < 0:
        return None
    return {
        "hour": hour,
        "min": max(data.get("min", 0), 0),
        "sec": max(data.get("sec", 0), 0),
    }


class DomoSprinkler:
    """Singolo irrigatore appartenente a un settore di irrigazione (campo 'sprinklers[]')."""

    def __init__(self, zone: "DomoIrrigationZone", data: Dict[str, Any]):
        self._zone = zone
        self._act_id = data.get("act_id")
        self._name = data.get("name", f"Irrigatore {self._act_id}")
        self._enabled = bool(data.get("enabled", 0))
        self._status = data.get("status", 0)
        self._active = data.get("active")
        self._duty = data.get("duty")

    @property
    def zone(self) -> "DomoIrrigationZone":
        return self._zone

    @property
    def zone_id(self) -> int:
        return self._zone.zone_id

    @property
    def gateway(self):
        return self._zone.gateway

    @property
    def unique_id(self) -> str:
        return f"domo_irrigation_{self.zone_id}_sprinkler_{self._act_id}"

    @property
    def act_id(self) -> int:
        return self._act_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def is_active(self) -> bool:
        """True se questo irrigatore sta erogando acqua in questo momento."""
        return self._status == 1

    @property
    def active(self) -> Optional[int]:
        return self._active

    @property
    def duty(self) -> Optional[int]:
        return self._duty

    def update(self, data: Dict[str, Any]) -> None:
        if "name" in data:
            self._name = data["name"]
        if "enabled" in data:
            self._enabled = bool(data["enabled"])
        if "status" in data:
            self._status = data["status"]
        if "active" in data:
            self._active = data["active"]
        if "duty" in data:
            self._duty = data["duty"]


class DomoIrrigationZone:
    """Settore di irrigazione ETI Domo / CAME Domotic (feature 'irrig')."""

    def __init__(self, gateway, data: Dict[str, Any]):
        self._gateway = gateway
        self._id = data["id"]
        self._name = data.get("name", f"Settore irrigazione {self._id}")
        self._enabled = bool(data.get("enabled", 0))
        self._status = data.get("status", 0)
        self._forced = bool(data.get("forced", 0))
        self._days = data.get("days", 0)
        self._perc = data.get("perc", 100)
        self._start = _decode_time(data.get("start"))
        self._end = _decode_time(data.get("end"))

        self._sprinklers: Dict[int, DomoSprinkler] = {}
        for spr in data.get("sprinklers", []) or []:
            act_id = spr.get("act_id")
            if act_id is not None:
                self._sprinklers[act_id] = DomoSprinkler(self, spr)

        _IRRIGATION_ZONES[self._id] = self

        _LOGGER.debug(
            "IRRIGATION zone created | id=%s name=%s enabled=%s days=%s perc=%s sprinklers=%s",
            self._id, self._name, self._enabled, self._days, self._perc,
            list(self._sprinklers.keys()),
        )

    # --------------------------------------------------
    # PROPRIETA'
    # --------------------------------------------------
    @property
    def zone_id(self) -> int:
        return self._id

    @property
    def gateway(self):
        return self._gateway

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"domo_irrigation_{self._id}"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def is_watering(self) -> bool:
        """True se il settore sta irrigando in questo momento."""
        return self._status == 1

    @property
    def forced(self) -> bool:
        """True se e' in corso un'irrigazione forzata manualmente."""
        return self._forced

    @property
    def days(self) -> int:
        return self._days

    @property
    def active_weekdays(self) -> List[str]:
        return _decode_days(self._days)

    @property
    def perc(self) -> int:
        """Percentuale di durata rispetto al tempo nominale (es. 100 = nominale)."""
        return self._perc

    @property
    def start(self) -> Optional[Dict[str, int]]:
        """Orario di partenza programmato, o None se non impostato."""
        return self._start

    @property
    def end(self) -> Optional[Dict[str, int]]:
        """Orario di fine (calcolato dal gateway in base a durata/perc), sola lettura."""
        return self._end

    @property
    def sprinklers(self) -> List[DomoSprinkler]:
        return list(self._sprinklers.values())

    def get_sprinkler(self, act_id: int) -> Optional[DomoSprinkler]:
        return self._sprinklers.get(act_id)

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------
    def update(self, data: Dict[str, Any]) -> bool:
        """Aggiorna il settore con i nuovi dati ricevuti dal bus (irrigation_detail_ind)."""
        if data.get("id") != self._id:
            return False

        changed = False
        field_map = {
            "name": "_name",
            "enabled": "_enabled",
            "status": "_status",
            "forced": "_forced",
            "days": "_days",
            "perc": "_perc",
        }
        for key, attr in field_map.items():
            if key not in data:
                continue
            value = data[key]
            if key in ("enabled", "forced"):
                value = bool(value)
            if getattr(self, attr) != value:
                setattr(self, attr, value)
                changed = True

        if "start" in data:
            new_start = _decode_time(data["start"])
            if new_start != self._start:
                self._start = new_start
                changed = True

        if "end" in data:
            new_end = _decode_time(data["end"]) if self._start is not None else None
            if new_end != self._end:
                self._end = new_end
                changed = True

        if "sprinklers" in data:
            for spr in data["sprinklers"] or []:
                act_id = spr.get("act_id")
                if act_id is None:
                    continue
                existing = self._sprinklers.get(act_id)
                if existing:
                    existing.update(spr)
                    if self._gateway and self._gateway.hass:
                        async_dispatcher_send(
                            self._gateway.hass, SIGNAL_UPDATE_ENTITY, existing.unique_id
                        )
                else:
                    new_sprinkler = DomoSprinkler(self, spr)
                    self._sprinklers[act_id] = new_sprinkler
                    if self._gateway and self._gateway.hass:
                        async_dispatcher_send(
                            self._gateway.hass, SIGNAL_DISCOVERY_NEW.format("number"), new_sprinkler
                        )
                        async_dispatcher_send(
                            self._gateway.hass, SIGNAL_DISCOVERY_NEW.format("binary_sensor"), new_sprinkler
                        )
            changed = True

        if changed:
            _LOGGER.debug(
                "IRRIGATION zone updated | id=%s enabled=%s status=%s forced=%s perc=%s",
                self._id, self._enabled, self._status, self._forced, self._perc,
            )
        return True


# ============================================================
# DISCOVERY
# ============================================================
async def discover_irrigation_zones(gateway):
    """Scopre i settori di irrigazione disponibili (feature 'irrig')."""
    _LOGGER.info("IRRIGATION starting discovery")

    try:
        resp = await gateway.tx_command(
            {"cmd_name": "irrigation_list_req", "detailed": 1},
            resp_command="irrigation_list_resp",
        )
    except Exception as err:
        _LOGGER.error("IRRIGATION discovery failed: %s", err)
        return []

    if not resp or "array" not in resp:
        _LOGGER.debug("IRRIGATION: nessun settore trovato")
        return []

    zones = []
    for item in resp.get("array", []):
        if "id" not in item:
            continue
        zone = _IRRIGATION_ZONES.get(item["id"])
        if zone:
            zone.update(item)
        else:
            zone = DomoIrrigationZone(gateway, item)
        zones.append(zone)

    _LOGGER.info("IRRIGATION discovered %d zone(s)", len(zones))
    return zones


def get_all_irrigation_zones() -> List["DomoIrrigationZone"]:
    return list(_IRRIGATION_ZONES.values())


def get_all_sprinklers() -> List["DomoSprinkler"]:
    """Ritorna tutti gli irrigatori di tutti i settori, per il setup iniziale delle entita'."""
    result: List[DomoSprinkler] = []
    for zone in _IRRIGATION_ZONES.values():
        result.extend(zone.sprinklers)
    return result


def get_irrigation_zone(zone_id: int) -> Optional["DomoIrrigationZone"]:
    return _IRRIGATION_ZONES.get(zone_id)


# ============================================================
# HANDLER BUS
# ============================================================
def handle_irrigation_status_update(gateway, device_info: Dict[str, Any]) -> bool:
    """Punto unico di ingresso per i pacchetti 'irrigation_detail_ind' dal gateway."""
    cmd = device_info.get("cmd_name")
    if cmd != "irrigation_detail_ind":
        return False

    zone_id = device_info.get("id")
    if zone_id is None:
        return False

    zone = _IRRIGATION_ZONES.get(zone_id)
    is_new = zone is None

    if is_new:
        zone = DomoIrrigationZone(gateway, device_info)
    else:
        zone.update(device_info)

    if gateway and gateway.hass:
        if is_new:
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("irrigation_switch"), zone)
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("time"), zone)
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("irrigation_number"), zone)
            for sprinkler in zone.sprinklers:
                async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("number"), sprinkler)
                async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("binary_sensor"), sprinkler)
        async_dispatcher_send(gateway.hass, SIGNAL_UPDATE_ENTITY, zone.unique_id)

    _LOGGER.debug(
        "IRRIGATION irrigation_detail_ind | id=%s enabled=%s status=%s forced=%s new=%s",
        zone_id, zone.enabled, zone.is_watering, zone.forced, is_new,
    )
    return True


# ============================================================
# FUNZIONI DI COMANDO
# ============================================================
async def async_set_irrigation_enabled(zone_id: int, value: int, gateway) -> None:
    """Abilita/disabilita un settore di irrigazione."""
    await gateway.tx_command(
        {"cmd_name": "irrigation_set_req", "id": zone_id, "enabled": value},
        resp_command=None,
    )


async def async_set_irrigation_perc(zone_id: int, perc: int, gateway) -> None:
    """Imposta la percentuale di durata dell'irrigazione (100 = durata nominale)."""
    await gateway.tx_command(
        {"cmd_name": "irrigation_set_req", "id": zone_id, "perc": perc},
        resp_command=None,
    )


async def async_set_irrigation_days(zone_id: int, days: int, gateway) -> None:
    """Imposta la bitmask completa dei giorni attivi (mon=bit0 ... sun=bit6)."""
    await gateway.tx_command(
        {"cmd_name": "irrigation_set_req", "id": zone_id, "days": days},
        resp_command=None,
    )


async def async_set_irrigation_day(zone_id: int, day_index: int, value: int, gateway) -> None:
    """Abilita/disabilita un singolo giorno della settimana per un settore."""
    
    zone = get_irrigation_zone(zone_id)
    if zone is None:
        _LOGGER.warning("IRRIGATION: set_day su zona sconosciuta id=%s", zone_id)
        return
    new_days = _encode_day_change(zone.days, day_index, value)
    await async_set_irrigation_days(zone_id, new_days, gateway)


async def async_set_irrigation_start(
    zone_id: int, hour: int, minute: int, second: int, gateway
) -> None:
    """Imposta l'orario di partenza programmato del settore."""
    await gateway.tx_command(
        {
            "cmd_name": "irrigation_set_req",
            "id": zone_id,
            "start": {"hour": hour, "min": minute, "sec": second},
        },
        resp_command=None,
    )


async def async_set_sprinkler_enabled(zone_id: int, act_id: int, value: int, gateway) -> None:
    """Abilita/disabilita il singolo irrigatore di un settore."""
    await gateway.tx_command(
        {
            "cmd_name": "irrigation_set_req",
            "id": zone_id,
            "sprinklers": [{"act_id": act_id, "enabled": value}],
        },
        resp_command=None,
    )


async def async_set_sprinkler_active(zone_id: int, act_id: int, seconds: int, gateway) -> None:
    """Imposta il tempo massimo di irrigazione (in secondi) del singolo irrigatore."""
    await gateway.tx_command(
        {
            "cmd_name": "irrigation_set_req",
            "id": zone_id,
            "sprinklers": [{"act_id": act_id, "active": seconds}],
        },
        resp_command=None,
    )


async def async_set_sprinkler_duty(zone_id: int, act_id: int, duty: int, gateway) -> None:
    """Imposta il ciclo di lavoro (duty cycle, %) del singolo irrigatore."""
    await gateway.tx_command(
        {
            "cmd_name": "irrigation_set_req",
            "id": zone_id,
            "sprinklers": [{"act_id": act_id, "duty": duty}],
        },
        resp_command=None,
    )


async def async_force_irrigation(zone_id: int, gateway) -> None:
    """Forza l'avvio/arresto manuale dell'irrigazione."""
    await gateway.tx_command(
        {"cmd_name": "irrigation_force_req", "id": zone_id},
        resp_command=None,
    )
