"""
domo/platforms/loadsctrl.py

Entities fed by this file:
- domo/sensor.py : Potenza istantanea fonte alimentazione (Generale)
- domo/number.py : Fondo scala (max_power), Isteresi
- domo/text.py   : Profilo energetico giornaliero (7 giorni x 24 livelli)
- domo/select.py : Giorno da modificare (la funzione "copia profilo su..." e' gestita
                    interamente lato UI in domo/select.py, come per i termostati -
                    non richiede comandi bus dedicati)
- domo/switch.py : Abilitazione/disabilitazione controllo carico (relay), icona dinamica
                    in base allo stato di collegamento gestita da domo/switch.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_DISCOVERY_NEW, SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)


class LoadCtrlProfileError(ValueError):
    """Input utente non applicabile al profilo energetico (slot sovrapposti o ambigui)."""


# Ordine giorni confermato: lun=indice 0 ... dom=indice 6 (coerente con platforms/irrigation.py).
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Mappa giorno (Italiano) -> indice, usata dal selector "Giorno del profilo energetico"
# (nessun 'Jolly', a differenza della termoregolazione: solo i 7 giorni reali).
LOADCTRL_DAY_TO_INDEX = {
    "Lunedì": 0, "Martedì": 1, "Mercoledì": 2, "Giovedì": 3,
    "Venerdì": 4, "Sabato": 5, "Domenica": 6,
}
LOADCTRL_INDEX_TO_DAY = {v: k for k, v in LOADCTRL_DAY_TO_INDEX.items()}
_WEEKDAY_ORDER = list(LOADCTRL_DAY_TO_INDEX)

# Ordine giorni confermato: lun=indice 0 ... dom=indice 6 (coerente con platforms/irrigation.py).
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Il profilo giornaliero e' una stringa di 24 caratteri (uno per ora), cifre '0'-'5'.
# Formula confermata sul campo: Watt = digit * (fondo_scala / 5).
# digit 0 = 0W (esiste nel protocollo ma NON e' selezionabile dalla UI ufficiale);
# digit 1-5 = i 5 livelli mostrati nella UI ufficiale (es. fondo scala 4kW ->
# 800W, 1600W, 2400W, 3200W, 4000W).
LOADCTRL_PROFILE_HOURS = 24
LOADCTRL_LEVELS = 5  # numero di livelli UI selezionabili (digit 1-5)
LOADCTRL_DEFAULT_LEVEL = 5  # livello massimo (nessuna limitazione), fallback per dati mancanti

_LOADCTRL_METERS: Dict[int, "DomoLoadCtrlMeter"] = {}
_LOADCTRL_RELAYS: Dict[int, "DomoLoadCtrlRelay"] = {}


def loadsctrl_level_to_watts(level: int, max_power: int) -> int:
    """Converte un digit raw (0-5) in Watt, proporzionale al fondo scala (max_power).
    digit 0 = 0W (non selezionabile dalla UI ufficiale); digit 1-5 = i 5 livelli UI."""
    level = max(0, min(LOADCTRL_LEVELS, level))
    return round(max_power * level / LOADCTRL_LEVELS)


def loadsctrl_validate_profile_string(value: str) -> bool:
    """Verifica che una stringa profilo sia valida: 24 caratteri, cifre 0-5."""
    if not isinstance(value, str) or len(value) != LOADCTRL_PROFILE_HOURS:
        return False
    return all(ch in "012345" for ch in value)


# ============================================================
# ENCODER / DECODER PROFILO (formato leggibile 'N-M=Watt,...')
# ============================================================
# Formato: slot orari 1-24 (senza minuti: lo slot N rappresenta l'ora N-1:00 - N:00),
# valore in Watt calcolato dinamicamente in proporzione al fondo scala (max_power).
# Esempio con fondo scala 4000W: "1-6=800,7=1600,8-9=2400,10-12=3200,13-24=4000".
# La scrittura di un singolo slot sovrascrive solo quello slot, lasciando invariato il resto.

def _watts_to_level(watts: int, max_power: int) -> str:
    """Converte un valore in Watt nel livello raw '1'-'5' piu' vicino (i 5 livelli
    selezionabili dalla UI ufficiale), in base al fondo scala corrente. Arrotonda al livello
    piu' vicino; valori sotto il minimo vengono portati al minimo (livello 1), valori sopra
    il fondo scala vengono portati al massimo (livello 5, fondo scala)."""
    if max_power <= 0:
        raise LoadCtrlProfileError(f"Fondo scala non valido: {max_power}W")

    step = max_power / LOADCTRL_LEVELS
    level = round(watts / step)
    level = max(1, min(LOADCTRL_LEVELS, level))
    return str(level)


def _parse_hour_range(rng: str) -> Tuple[int, int]:
    """Converte 'N' o 'N-M' (ore 1-24, inclusive) nello slot 0-indexed (start, end) semi-aperto."""
    rng = rng.strip()
    if "-" in rng:
        start_str, end_str = rng.split("-")
        start_hour, end_hour = int(start_str.strip()), int(end_str.strip())
    else:
        start_hour = end_hour = int(rng)

    if not (1 <= start_hour <= end_hour <= LOADCTRL_PROFILE_HOURS):
        raise LoadCtrlProfileError(f"Slot orario non valido (atteso 1-{LOADCTRL_PROFILE_HOURS}): {rng}")

    return start_hour - 1, end_hour


def _parse_schedule_blocks(schedule_str: str, max_power: int) -> List[Tuple[int, int, str]]:
    """Effettua il parsing di 'N-M=Watt,...' in una lista di (start_slot, end_slot, char raw 0-4)."""
    blocks: List[Tuple[int, int, str]] = []
    for raw_block in schedule_str.split(","):
        raw_block = raw_block.strip()
        if not raw_block:
            continue
        rng, watts_str = raw_block.split("=")
        try:
            watts = int(watts_str.strip())
        except ValueError:
            raise LoadCtrlProfileError(f"Valore non numerico: {watts_str.strip()}")
        char = _watts_to_level(watts, max_power)
        start_slot, end_slot = _parse_hour_range(rng)
        blocks.append((start_slot, end_slot, char))
    if not blocks:
        raise LoadCtrlProfileError("Profilo vuoto: nessun blocco specificato")
    return blocks


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    """Numero di ore in comune fra due intervalli [a_start,a_end) e [b_start,b_end)."""
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def _decode_profile_to_blocks(profile_data: str) -> List[Tuple[int, int, str]]:
    """Decodifica una stringa profilo (24 caratteri) in blocchi contigui (start_slot, end_slot, char)."""
    blocks: List[Tuple[int, int, str]] = []
    if not profile_data:
        return blocks
    current_char, start = profile_data[0], 0
    for i in range(1, len(profile_data)):
        if profile_data[i] != current_char:
            blocks.append((start, i, current_char))
            current_char, start = profile_data[i], i
    blocks.append((start, len(profile_data), current_char))
    return blocks


def encode_loadsctrl_profile(schedule_str: str, max_power: int, base_profile_data: Optional[str] = None) -> str:
    """Converte 'N-M=Watt,...' nella stringa di 24 caratteri per loadsctrl_meter_set_req.
    Ogni blocco specificato dall'utente sovrascrive direttamente il proprio intervallo di ore;
    le ore non menzionate mantengono il valore della base. I blocchi identici a quelli gia'
    presenti nella base (testo lasciato invariato dall'utente) vengono scartati prima del
    controllo sovrapposizioni, cosi' da poter riscrivere solo la parte che cambia senza dover
    ricalcolare a mano i confini delle porzioni contigue - stesso comportamento dei profili
    termici."""
    user_blocks = _parse_schedule_blocks(schedule_str, max_power)

    if base_profile_data and len(base_profile_data) == LOADCTRL_PROFILE_HOURS:
        base_blocks = _decode_profile_to_blocks(base_profile_data)
        slots = list(base_profile_data)
    else:
        base_blocks = []
        slots = [str(LOADCTRL_DEFAULT_LEVEL)] * LOADCTRL_PROFILE_HOURS

    # Scarto i blocchi dell'utente identici a quelli gia' presenti nella base: non sono
    # modifiche reali, permettono di lasciare nel testo le righe non toccate.
    real_blocks = [b for b in user_blocks if b not in base_blocks]
    if not real_blocks:
        return base_profile_data if base_profile_data else "".join(slots)

    # Solo le modifiche realmente richieste non devono sovrapporsi fra loro.
    sorted_blocks = sorted(real_blocks, key=lambda b: b[0])
    for prev_block, curr_block in zip(sorted_blocks, sorted_blocks[1:]):
        if _overlap(prev_block[0], prev_block[1], curr_block[0], curr_block[1]) > 0:
            raise LoadCtrlProfileError("Slot orari sovrapposti. Input annullato.")

    for start, end, char in sorted_blocks:
        for i in range(start, end):
            slots[i] = char

    return "".join(slots)


def decode_loadsctrl_profile_to_schedule_str(profile_data: str, max_power: int) -> str:
    """Decodifica la stringa profilo (24 caratteri, digit raw 0-4) nel formato
    'N-M=Watt,...' (N,M = ore 1-24, Watt calcolato dinamicamente sul fondo scala corrente)."""
    if not profile_data:
        return ""
    blocks = []
    current_char, start = None, 0
    for i, ch in enumerate(profile_data):
        if current_char is None:
            current_char, start = ch, i
            continue
        if ch != current_char:
            blocks.append(_format_block(start, i, current_char, max_power))
            current_char, start = ch, i
    if current_char is not None:
        blocks.append(_format_block(start, len(profile_data), current_char, max_power))
    return ",".join(blocks)


def _format_block(start_slot: int, end_slot: int, char: str, max_power: int) -> str:
    """Formatta un blocco (start_slot, end_slot, char raw) come 'N=Watt' o 'N-M=Watt'."""
    start_hour, end_hour = start_slot + 1, end_slot
    watts = loadsctrl_level_to_watts(int(char), max_power)
    if start_hour == end_hour:
        return f"{start_hour}={watts}"
    return f"{start_hour}-{end_hour}={watts}"


class DomoLoadCtrlRelay:
    """Singolo carico gestito dal controllo carichi (campo 'array[]' di loadsctrl_relay_list_resp)."""

    def __init__(self, meter: "DomoLoadCtrlMeter", data: Dict[str, Any]):
        self._meter = meter
        self._id = data["id"]
        self._name = data.get("name", f"Carico {self._id}")
        self._priority = data.get("priority", 0)
        self._enabled = bool(data.get("enabled", 0))
        self._act_id = data.get("act_id")
        self._detached = bool(data.get("detached", 0))
        self._status = data.get("status", 0)
        self._loadtype = data.get("loadtype")

    @property
    def meter(self) -> "DomoLoadCtrlMeter":
        return self._meter

    @property
    def meter_id(self) -> int:
        return self._meter.meter_id

    @property
    def gateway(self):
        return self._meter.gateway

    @property
    def relay_id(self) -> int:
        return self._id

    @property
    def unique_id(self) -> str:
        return f"domo_loadsctrl_relay_{self._id}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def enabled(self) -> bool:
        """True se il carico e' attualmente abilitato (switch ON)."""
        return self._enabled

    @property
    def act_id(self) -> Optional[int]:
        return self._act_id

    @property
    def is_detached(self) -> bool:
        """True se il gestore carichi ha temporaneamente escluso il carico (evento di sovraccarico)."""
        return self._detached

    @property
    def status(self) -> int:
        return self._status

    @property
    def loadtype(self) -> Optional[int]:
        return self._loadtype

    def update(self, data: Dict[str, Any]) -> None:
        if "name" in data:
            self._name = data["name"]
        if "priority" in data:
            self._priority = data["priority"]
        if "enabled" in data:
            self._enabled = bool(data["enabled"])
        if "act_id" in data:
            self._act_id = data["act_id"]
        if "detached" in data:
            self._detached = bool(data["detached"])
        if "status" in data:
            self._status = data["status"]
        if "loadtype" in data:
            self._loadtype = data["loadtype"]


class DomoLoadCtrlMeter:
    """Gestore del controllo carichi ETI Domo / CAME Domotic (feature 'loadsctrl'), es. 'Generale'."""

    def __init__(self, gateway, data: Dict[str, Any]):
        self._gateway = gateway
        self._id = data["id"]
        self._name = data.get("name", f"Controllo carichi {self._id}")
        self._hysteresis = data.get("hysteresis", 0)
        self._max_power = data.get("max_power", 0)
        self._profile_data = list(data.get("profile_data") or [])
        self._meter_id = data.get("meter_id")
        self._power = data.get("power", 0)

        self._relays: Dict[int, DomoLoadCtrlRelay] = {}

        self._selected_profile_day: str = _WEEKDAY_ORDER[datetime.now().weekday()]
        self._profile_draft_by_day: Dict[str, str] = {}
        self._apply_profile_data_array(self._profile_data)

        _LOADCTRL_METERS[self._id] = self

        _LOGGER.debug(
            "LOADSCTRL meter created | id=%s name=%s max_power=%s hysteresis=%s meter_id=%s power=%s",
            self._id, self._name, self._max_power, self._hysteresis, self._meter_id, self._power,
        )

    # --------------------------------------------------
    # PROPRIETA'
    # --------------------------------------------------
    @property
    def meter_id(self) -> int:
        return self._id

    @property
    def gateway(self):
        return self._gateway

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"domo_loadsctrl_{self._id}"

    @property
    def hysteresis(self) -> int:
        """Isteresi in Watt."""
        return self._hysteresis

    @property
    def max_power(self) -> int:
        """Fondo scala in Watt."""
        return self._max_power

    @property
    def profile_data(self) -> List[str]:
        return list(self._profile_data)

    @property
    def energy_meter_id(self) -> Optional[int]:
        """Id del contatore energia collegato (feature 'energy'), sola lettura."""
        return self._meter_id

    @property
    def power(self) -> int:
        """Potenza istantanea in Watt della fonte di alimentazione."""
        return self._power

    @property
    def relays(self) -> List[DomoLoadCtrlRelay]:
        """Carichi collegati, ordinati per priorita'."""
        return sorted(self._relays.values(), key=lambda relay: relay.priority)

    def get_relay(self, relay_id: int) -> Optional[DomoLoadCtrlRelay]:
        return self._relays.get(relay_id)

    def get_profile_day(self, day_index: int) -> str:
        """Ritorna la stringa profilo (24 livelli) del giorno indicato (0=mon ... 6=sun)."""
        if 0 <= day_index < len(self._profile_data):
            return self._profile_data[day_index]
        return str(LOADCTRL_DEFAULT_LEVEL) * LOADCTRL_PROFILE_HOURS

    def get_day_level(self, day_index: int, hour: int) -> int:
        """Ritorna il livello (1-5) impostato per una specifica ora di un giorno."""
        day = self.get_profile_day(day_index)
        if 0 <= hour < len(day):
            return int(day[hour])
        return LOADCTRL_DEFAULT_LEVEL

    @property
    def selected_profile_day(self) -> str:
        """Giorno (Italiano) attualmente in editing per il profilo energetico."""
        return self._selected_profile_day

    def set_selected_profile_day(self, day: str) -> None:
        if day not in LOADCTRL_DAY_TO_INDEX:
            raise ValueError(f"Giorno non valido: {day}")
        self._selected_profile_day = day

    @property
    def profile_draft(self) -> str:
        """Bozza leggibile ('HH:MM-HH:MM=N,...') del giorno correntemente selezionato."""
        return self._profile_draft_by_day.get(self._selected_profile_day, "")

    def _apply_profile_data_array(self, profile_data_array: List[str]) -> None:
        """Ricostruisce la cache delle bozze leggibili per tutti i giorni (0-6: Lun...Dom),
        con valori in Watt calcolati sul fondo scala corrente."""
        for day_index, raw in enumerate(profile_data_array):
            day_name = LOADCTRL_INDEX_TO_DAY.get(day_index)
            if day_name is None:
                continue
            self._profile_draft_by_day[day_name] = decode_loadsctrl_profile_to_schedule_str(raw, self._max_power)

    async def async_set_profile(self, schedule_str: str) -> None:
        """Scrive il profilo energetico (formato leggibile) del giorno correntemente selezionato."""
        day_index = LOADCTRL_DAY_TO_INDEX[self._selected_profile_day]
        base_profile_data = self.get_profile_day(day_index)
        profile_data = encode_loadsctrl_profile(schedule_str, self._max_power, base_profile_data=base_profile_data)

        _LOGGER.debug(
            "📈LOADSCTRL meter id=%s: profilo giorno=%s base=%r input=%r -> profile_data=%r",
            self._id, self._selected_profile_day, base_profile_data, schedule_str, profile_data,
        )

        await async_set_loadsctrl_profile_day(self._id, day_index, profile_data, self._gateway)

    def update_profile_day_local(self, day_index: int, profile_string: str) -> None:
        """Aggiorna otticamente la cache locale"""
        while len(self._profile_data) < 7:
            self._profile_data.append(str(LOADCTRL_DEFAULT_LEVEL) * LOADCTRL_PROFILE_HOURS)
        self._profile_data[day_index] = profile_string
        day_name = LOADCTRL_INDEX_TO_DAY.get(day_index)
        if day_name:
            self._profile_draft_by_day[day_name] = decode_loadsctrl_profile_to_schedule_str(profile_string, self._max_power)
    

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------
    def update(self, data: Dict[str, Any]) -> bool:
        """Aggiorna il gestore carichi con i nuovi dati ricevuti dal bus (loadsctrl_meter_ind)."""
        if data.get("id") != self._id:
            return False

        changed = False
        field_map = {
            "name": "_name",
            "hysteresis": "_hysteresis",
            "max_power": "_max_power",
            "meter_id": "_meter_id",
            "power": "_power",
        }
        max_power_changed = False
        profile_changed = False
        for key, attr in field_map.items():
            if key not in data:
                continue
            if getattr(self, attr) != data[key]:
                setattr(self, attr, data[key])
                changed = True
                if key == "max_power":
                    max_power_changed = True

        if "profile_data" in data:
            new_profile = list(data["profile_data"] or [])
            if new_profile != self._profile_data:
                self._profile_data = new_profile
                changed = True
                profile_changed = True
                
        if profile_changed or max_power_changed:
            self._apply_profile_data_array(self._profile_data)               

        if changed:
            _LOGGER.debug(
                "LOADSCTRL meter updated | id=%s max_power=%s hysteresis=%s power=%s",
                self._id, self._max_power, self._hysteresis, self._power,
            )
        return True

    def add_or_update_relay(self, data: Dict[str, Any]) -> "tuple[DomoLoadCtrlRelay, bool]":
        """Crea o aggiorna un carico collegato a questo gestore. Ritorna (relay, is_new)."""
        relay_id = data["id"]
        relay = self._relays.get(relay_id)
        is_new = relay is None
        if is_new:
            relay = DomoLoadCtrlRelay(self, data)
            self._relays[relay_id] = relay
            _LOADCTRL_RELAYS[relay_id] = relay
        else:
            relay.update(data)
        return relay, is_new


# ============================================================
# DISCOVERY
# ============================================================
async def discover_loadsctrl(gateway):
    """Scopre i gestori di controllo carichi e i relativi carichi (feature 'loadsctrl')."""
    _LOGGER.info("LOADSCTRL starting discovery")

    try:
        resp = await gateway.tx_command(
            {"cmd_name": "loadsctrl_meter_list_req"},
            resp_command="loadsctrl_meter_list_resp",
        )
    except Exception as err:
        _LOGGER.error("LOADSCTRL meter discovery failed: %s", err)
        return []

    if not resp or "array" not in resp:
        _LOGGER.debug("LOADSCTRL: nessun gestore carichi trovato")
        return []

    meters = []
    for item in resp.get("array", []):
        if "id" not in item:
            continue
        meter = _LOADCTRL_METERS.get(item["id"])
        if meter:
            meter.update(item)
        else:
            meter = DomoLoadCtrlMeter(gateway, item)
        meters.append(meter)
        await _discover_loadsctrl_relays(gateway, meter)

    _LOGGER.info("LOADSCTRL discovered %d gestore(i) carichi", len(meters))
    return meters


async def _discover_loadsctrl_relays(gateway, meter: DomoLoadCtrlMeter) -> None:
    """Scopre i carichi (relay) collegati a un gestore di controllo carichi."""
    try:
        resp = await gateway.tx_command(
            {"cmd_name": "loadsctrl_relay_list_req", "id": meter.meter_id},
            resp_command="loadsctrl_relay_list_resp",
        )
    except Exception as err:
        _LOGGER.error("LOADSCTRL relay discovery failed for meter id=%s: %s", meter.meter_id, err)
        return

    if not resp or "array" not in resp:
        _LOGGER.debug("LOADSCTRL: nessun carico trovato per meter id=%s", meter.meter_id)
        return

    for item in resp.get("array", []):
        if "id" not in item:
            continue
        meter.add_or_update_relay(item)

    _LOGGER.debug("LOADSCTRL meter id=%s: %d carico(i)", meter.meter_id, len(meter.relays))


def get_all_loadsctrl_meters() -> List["DomoLoadCtrlMeter"]:
    return list(_LOADCTRL_METERS.values())


def get_all_loadsctrl_relays() -> List["DomoLoadCtrlRelay"]:
    """Ritorna tutti i carichi di tutti i gestori, per il setup iniziale delle entita'."""
    result: List[DomoLoadCtrlRelay] = []
    for meter in _LOADCTRL_METERS.values():
        result.extend(meter.relays)
    return result


def get_loadsctrl_meter(meter_id: int) -> Optional["DomoLoadCtrlMeter"]:
    return _LOADCTRL_METERS.get(meter_id)


def get_loadsctrl_relay(relay_id: int) -> Optional["DomoLoadCtrlRelay"]:
    return _LOADCTRL_RELAYS.get(relay_id)


# ============================================================
# HANDLER BUS
# ============================================================
def handle_loadsctrl_status_update(gateway, device_info: Dict[str, Any]) -> bool:
    """Punto unico di ingresso per i pacchetti 'loadsctrl_meter_ind' / 'loadsctrl_relay_ind' dal gateway."""
    cmd = device_info.get("cmd_name")
    if cmd not in ("loadsctrl_meter_ind", "loadsctrl_relay_ind"):
        return False

    if cmd == "loadsctrl_meter_ind":
        return _handle_meter_ind(gateway, device_info)
    return _handle_relay_ind(gateway, device_info)


def _handle_meter_ind(gateway, device_info: Dict[str, Any]) -> bool:
    meter_id = device_info.get("id")
    if meter_id is None:
        return False

    meter = _LOADCTRL_METERS.get(meter_id)
    is_new = meter is None

    if is_new:
        meter = DomoLoadCtrlMeter(gateway, device_info)
    else:
        meter.update(device_info)

    if gateway and gateway.hass:
        if is_new:
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_sensor"), meter)
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_number"), meter)
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_text"), meter)
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_select"), meter)
        async_dispatcher_send(gateway.hass, SIGNAL_UPDATE_ENTITY, meter.unique_id)

    _LOGGER.debug(
        "LOADSCTRL loadsctrl_meter_ind | id=%s max_power=%s hysteresis=%s power=%s new=%s",
        meter_id, meter.max_power, meter.hysteresis, meter.power, is_new,
    )
    return True


def _handle_relay_ind(gateway, device_info: Dict[str, Any]) -> bool:
    relay_id = device_info.get("id")
    if relay_id is None:
        return False

    relay = _LOADCTRL_RELAYS.get(relay_id)

    if relay is not None:
        relay.update(device_info)
        is_new = False
        meter = relay.meter
    else:
        # Carico non ancora noto: lo agganciamo all'unico gestore carichi conosciuto.
        # Con piu' gestori attivi in futuro andra' rivisto (il pacchetto non indica il gestore
        # di appartenenza), per ora coerente con l'unico caso osservato ('Generale').
        if len(_LOADCTRL_METERS) != 1:
            _LOGGER.warning(
                "LOADSCTRL: carico sconosciuto id=%s con %d gestori attivi, impossibile associare",
                relay_id, len(_LOADCTRL_METERS),
            )
            return False
        meter = next(iter(_LOADCTRL_METERS.values()))
        relay, is_new = meter.add_or_update_relay(device_info)

    if gateway and gateway.hass:
        if is_new:
            async_dispatcher_send(gateway.hass, SIGNAL_DISCOVERY_NEW.format("loadsctrl_switch"), relay)
        async_dispatcher_send(gateway.hass, SIGNAL_UPDATE_ENTITY, relay.unique_id)

    _LOGGER.debug(
        "LOADSCTRL loadsctrl_relay_ind | id=%s enabled=%s status=%s detached=%s new=%s",
        relay_id, relay.enabled, relay.status, relay.is_detached, is_new,
    )
    return True


# ============================================================
# FUNZIONI DI COMANDO
# ============================================================
async def _async_send_meter_set(meter: DomoLoadCtrlMeter, gateway, **overrides: Any) -> None:
    """Invia loadsctrl_meter_set_req con il payload completo (hysteresis, max_power,
    profile_data), come richiesto dal gateway, applicando le sole modifiche indicate."""
    payload = {
        "cmd_name": "loadsctrl_meter_set_req",
        "id": meter.meter_id,
        "hysteresis": meter.hysteresis,
        "max_power": meter.max_power,
        "profile_data": meter.profile_data,
    }
    payload.update(overrides)

    await gateway.tx_command(payload, resp_command=None)


async def async_set_loadsctrl_max_power(meter_id: int, max_power: int, gateway) -> None:
    """Imposta il fondo scala (max_power, in Watt) del gestore carichi."""
    meter = get_loadsctrl_meter(meter_id)
    if meter is None:
        _LOGGER.warning("LOADSCTRL: set_max_power su gestore sconosciuto id=%s", meter_id)
        return
    await _async_send_meter_set(meter, gateway, max_power=max_power)


async def async_set_loadsctrl_hysteresis(meter_id: int, hysteresis: int, gateway) -> None:
    """Imposta l'isteresi (in Watt) del gestore carichi."""
    meter = get_loadsctrl_meter(meter_id)
    if meter is None:
        _LOGGER.warning("LOADSCTRL: set_hysteresis su gestore sconosciuto id=%s", meter_id)
        return
    await _async_send_meter_set(meter, gateway, hysteresis=hysteresis)


async def async_set_loadsctrl_profile_day(
    meter_id: int, day_index: int, profile_string: str, gateway
) -> None:
    """Sostituisce il profilo (24 livelli) di un singolo giorno della settimana."""
    meter = get_loadsctrl_meter(meter_id)
    if meter is None:
        _LOGGER.warning("LOADSCTRL: set_profile_day su gestore sconosciuto id=%s", meter_id)
        return
    if not (0 <= day_index < 7):
        _LOGGER.warning("LOADSCTRL: day_index fuori range: %s", day_index)
        return
    if not loadsctrl_validate_profile_string(profile_string):
        _LOGGER.warning("LOADSCTRL: profilo non valido (attesi 24 caratteri 1-5): %s", profile_string)
        return

    new_profile = meter.profile_data
    while len(new_profile) < 7:
        new_profile.append(str(LOADCTRL_DEFAULT_LEVEL) * LOADCTRL_PROFILE_HOURS)
    new_profile[day_index] = profile_string

    await _async_send_meter_set(meter, gateway, profile_data=new_profile)

    meter.update_profile_day_local(day_index, profile_string)


async def async_set_loadsctrl_relay_enabled(relay_id: int, value: int, gateway) -> None:
    """Abilita/disabilita il controllo del carico (switch ON/OFF)."""
    relay = get_loadsctrl_relay(relay_id)
    if relay is None:
        _LOGGER.warning("LOADSCTRL: set_relay_enabled su carico sconosciuto id=%s", relay_id)
        return
    await gateway.tx_command(
        {
            "cmd_name": "loadsctrl_relay_set_req",
            "id": relay_id,
            "enabled": value,
            "priority": relay.priority,
        },
        resp_command=None,
    )
