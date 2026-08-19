"""
domo/platforms/thermoregulation.py

Entities fed by this file:
- domo/climate.py : Thermostats
- domo/number.py  : Anti-freeze, thermal differential, T1, T2, T3
- domo/select.py  : Thermal profile day, algorithm mode, season
- domo/text.py    : Daily thermal profile

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)


class ThermalProfileError(ValueError):
    """Input utente non applicabile al profilo termico (slot sovrapposti o ambigui)."""

# Mappa delle modalità termostato
THERMO_MODES = {
    0: "off",
    1: "manual",    
    2: "auto",
    3: "jolly",
}

# Mappa giorno (tab app nativa)
PROFILE_DAY_TO_ID = {
    "Lunedì": 0, "Martedì": 1, "Mercoledì": 2, "Giovedì": 3,
    "Venerdì": 4, "Sabato": 5, "Domenica": 6, "Jolly": 7,
}

PROFILE_ID_TO_DAY = {v: k for k, v in PROFILE_DAY_TO_ID.items()}

_WEEKDAY_ORDER = list(PROFILE_DAY_TO_ID)[:7]

PROFILE_CHAR_TO_SETPOINT = {
    "1": "t1",
    "2": "t1",
    "3": "t2",
    "4": "t2",
    "5": "t3",
}

SETPOINT_TO_PROFILE_CHAR = {"t1": "1", "t2": "3", "t3": "5"}

QUARTER_MINUTES = 15

ALGO_MODE_TO_PARAMS = {
    "PROPORZIONALE-INTEGRALE 1": {"type": "P", "pi_set_in_use": 1},
    "PROPORZIONALE-INTEGRALE 2": {"type": "P", "pi_set_in_use": 2},
    "PROPORZIONALE-INTEGRALE 3": {"type": "P", "pi_set_in_use": 3},
    "PROPORZIONALE-INTEGRALE 4": {"type": "P", "pi_set_in_use": 4},
    "DIFFERENZIALE": {"type": "D"},
}

_ALGO_PARAMS_TO_MODE = {
    (params["type"], params.get("pi_set_in_use")): name
    for name, params in ALGO_MODE_TO_PARAMS.items()
}
# Dizionario globale per tenere traccia di tutti i termostati
_THERMOSTATS: dict[int, "DomoThermostat"] = {}

def current_weekday_name() -> str:
    """Nome del giorno corrente, stesso formato di PROFILE_DAY_TO_ID."""
    return PROFILE_ID_TO_DAY[datetime.now().weekday()]

def _slot_to_time_str(slot_index: int) -> str:
    """Converte l'indice di quarto d'ora (0-95) in stringa HH:MM."""
    total_minutes = slot_index * QUARTER_MINUTES
    hour = (total_minutes // 60) % 24
    minute = total_minutes % 60
    return f"{hour:02d}:{minute:02d}"
    
def _time_str_to_slot(time_str: str) -> int:
    """Converte una stringa HH:MM nell'indice di quarto d'ora (0-96)"""
    hour, minute = (int(x) for x in time_str.split(":"))
    total_minutes = hour * 60 + minute
    slot = round(total_minutes / QUARTER_MINUTES)
    return max(0, min(slot, 96))
    

def _decode_profile_to_blocks(profile_data: str) -> List[tuple]:
    """Decodifica una stringa profilo (96 caratteri) in blocchi contigui (start_slot, end_slot, char)."""
    blocks: List[tuple] = []
    if not profile_data:
        return blocks
    current_char, start = profile_data[0], 0
    for i in range(1, len(profile_data)):
        if profile_data[i] != current_char:
            blocks.append((start, i, current_char))
            current_char, start = profile_data[i], i
    blocks.append((start, len(profile_data), current_char))
    return blocks


def _parse_schedule_blocks(schedule_str: str) -> List[tuple]:
    """Effettua il parsing di 'HH:MM-HH:MM=tN,...' in una lista di (start_slot, end_slot, char)."""
    blocks: List[tuple] = []
    for raw_block in schedule_str.split(","):
        raw_block = raw_block.strip()
        if not raw_block:
            continue
        rng, name = raw_block.split("=")
        start, end = rng.split("-")
        char = SETPOINT_TO_PROFILE_CHAR.get(name.strip())
        if char is None:
            raise ThermalProfileError(f"Set-point sconosciuto: {name.strip()}")
        start_slot, end_slot = _time_str_to_slot(start.strip()), _time_str_to_slot(end.strip())
        if end_slot <= start_slot:
            raise ThermalProfileError(f"Slot non valido: {raw_block}")
        blocks.append((start_slot, end_slot, char))
    if not blocks:
        raise ThermalProfileError("Profilo vuoto: nessun blocco specificato")
    return blocks


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    """Numero di quarti d'ora in comune fra due intervalli [a_start,a_end) e [b_start,b_end)."""
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def _find_target_block_index(u_start: int, u_end: int, u_char: str, base_blocks: List[tuple]) -> int:
    """Individua l'indice dello slot di base con la massima sovrapposizione con lo slot richiesto."""   
    def _best(indexed_blocks):
        overlaps = [(_overlap(u_start, u_end, b[0], b[1]), idx) for idx, b in indexed_blocks]
        max_ov = max(ov for ov, _ in overlaps)
        winners = [idx for ov, idx in overlaps if ov == max_ov]
        return max_ov, winners

    indexed = list(enumerate(base_blocks))
    same_char = [(i, b) for i, b in indexed if b[2] == u_char]

    if same_char:
        max_ov, winners = _best(same_char)
        if max_ov > 0:
            if len(winners) > 1:
                raise ThermalProfileError(
                    "Impossibile identificare univocamente lo slot da modificare. Input annullato."
                )
            return winners[0]

    max_ov, winners = _best(indexed)
    if len(winners) > 1:
        raise ThermalProfileError(
            "Impossibile identificare univocamente lo slot da modificare. Input annullato."
        )
    return winners[0]


def _encode_without_base(blocks: List[tuple]) -> str:
    """Comportamento legacy (nessun profilo di base disponibile): riempie i buchi con l'ultimo/primo carattere noto."""
    slots = [None] * 96
    for start, end, char in blocks:
        for i in range(start, end):
            slots[i] = char

    last_char = None
    for i in range(96):
        if slots[i] is not None:
            last_char = slots[i]
        elif last_char is not None:
            slots[i] = last_char

    first_char = next((c for c in slots if c is not None), None)
    if first_char:
        for i in range(96):
            if slots[i] is None:
                slots[i] = first_char
    return "".join(slots)


def encode_thermal_profile(schedule_str: str, base_profile_data: Optional[str] = None) -> str:
    """Converte 'HH:MM-HH:MM=tN,...' nella stringa di 96 caratteri per thermo_zone_config_req.""" 
    user_blocks = _parse_schedule_blocks(schedule_str)

    # Se non c'è base (prima scrittura), comportamento legacy: riempimento buchi.
    if not base_profile_data or len(base_profile_data) != 96:
        return _encode_without_base(user_blocks)

    base_blocks = _decode_profile_to_blocks(base_profile_data)

    # Scarto gli slot dell'utente identici a quelli già presenti nella base: non sono modifiche
    # reali (permette di inviare sia il profilo intero sia solo le righe cambiate).
    real_blocks = [b for b in user_blocks if b not in base_blocks]
    if not real_blocks:
        return base_profile_data

    # Le modifiche realmente richieste non devono sovrapporsi fra loro.
    real_blocks_sorted = sorted(real_blocks, key=lambda b: b[0])
    for prev_block, curr_block in zip(real_blocks_sorted, real_blocks_sorted[1:]):
        if _overlap(prev_block[0], prev_block[1], curr_block[0], curr_block[1]) > 0:
            raise ThermalProfileError("Slot temporali sovrapposti. Input annullato.")

    slots = list(base_profile_data)
    for u_start, u_end, u_char in real_blocks_sorted:
        target_idx = _find_target_block_index(u_start, u_end, u_char, base_blocks)
        t_start, t_end, _t_char = base_blocks[target_idx]

        # Applico l'intervallo/temperatura richiesti dall'utente (priorità assoluta).
        for i in range(u_start, u_end):
            slots[i] = u_char

        # Lo slot precedente termina all'inizio del nuovo slot (recupera l'eventuale buco lasciato
        # dal restringimento dello slot modificato).
        if u_start > t_start:
            prev_char = base_blocks[target_idx - 1][2] if target_idx > 0 else base_blocks[target_idx][2]
            for i in range(t_start, u_start):
                slots[i] = prev_char

        # Lo slot successivo inizia alla fine del nuovo slot.
        if u_end < t_end:
            next_char = base_blocks[target_idx + 1][2] if target_idx < len(base_blocks) - 1 else base_blocks[target_idx][2]
            for i in range(u_end, t_end):
                slots[i] = next_char

    return "".join(slots)

def decode_thermal_profile(profile_data: str, t1: Optional[int], t2: Optional[int], t3: Optional[int]) -> Dict[str, str]:
    """Decodifica la stringa profilo (96 caratteri) in blocchi orari compressi (una riga per fascia)."""    
    if not profile_data:
        return {}
    setpoint_values = {"t1": t1, "t2": t2, "t3": t3}
    def _char_to_temp(ch: str):
        name = PROFILE_CHAR_TO_SETPOINT.get(ch)
        if name is None:
            return None, None
        temp_dec = setpoint_values.get(name)
        return name, (temp_dec / 10.0 if temp_dec is not None else None)
    blocks = {}
    current_name, current_temp, start = None, None, 0
    for i, ch in enumerate(profile_data):
        name, temp = _char_to_temp(ch)
        if current_name is None:
            current_name, current_temp, start = name, temp, i
            continue
        if name != current_name:
            key = f"{_slot_to_time_str(start)}-{_slot_to_time_str(i)}"
            blocks[key] = f"{current_name} | {current_temp}°C"
            current_name, current_temp, start = name, temp, i
    if current_name is not None:
        key = f"{_slot_to_time_str(start)}-24:00"
        blocks[key] = f"{current_name} | {current_temp}°C"
    return blocks

def decode_thermal_profile_to_schedule_str(profile_data: str) -> str:
    """Decodifica la stringa profilo (96 caratteri) nel formato 'HH:MM-HH:MM=tN,...'."""    
    if not profile_data:
        return ""
    blocks = []
    current_name, start = None, 0
    for i, ch in enumerate(profile_data):
        name = PROFILE_CHAR_TO_SETPOINT.get(ch)
        if current_name is None:
            current_name, start = name, i
            continue
        if name != current_name:
            blocks.append(f"{_slot_to_time_str(start)}-{_slot_to_time_str(i)}={current_name}")
            current_name, start = name, i
    if current_name is not None:
        blocks.append(f"{_slot_to_time_str(start)}-24:00={current_name}")
    return ",".join(blocks)

async def discover_thermostats(gateway):
    """Scopri tutti i termostati disponibili."""
    _LOGGER.info("THERMOSTATS starting discovery")
    
    try:
        # Richiedi lista termostati
        resp = await gateway.tx_command({
            "cmd_name": "nested_thermo_list_req",
            "topologic_scope": "plant",
            "extended_infos": 2,
            "value": 0
        }, resp_command="thermo_list_resp")
        
        if not resp:
            _LOGGER.error("THERMOSTATS discovery: no response")
            return None
        
        # Parsing della struttura annidata
        thermostats_found = []
        for zone in resp.get("array", []):
            zone_name = zone.get("name")
            
            for thermo in zone.get("array", []):
                if thermo.get("leaf"):
                    # Crea oggetto DomoThermostat
                    thermo_obj = DomoThermostat(
                        gateway,
                        thermo,
                        zone_name,
                        thermo.get("name")
                    )
                    _THERMOSTATS[thermo.get("act_id")] = thermo_obj
                    thermostats_found.append(thermo_obj)
        
        _LOGGER.info("THERMOSTATS discovered %d devices", len(thermostats_found))
        return thermostats_found
        
    except Exception as err:
        _LOGGER.error("THERMOSTATS discovery failed: %s", err)
        return None

def get_thermostat(act_id: int) -> Optional["DomoThermostat"]:
    """Restituisce un oggetto termostato dal suo act_id."""
    return _THERMOSTATS.get(act_id)


def get_all_thermostats() -> List["DomoThermostat"]:
    """Restituisce tutti i termostati."""
    return list(_THERMOSTATS.values())



class DomoThermostat:

    def __init__(self, gateway, thermo_data: Dict[str, Any], zone: str, room: str):
        """Inizializza il termostato."""
        self._gateway = gateway
        
        # Salva i dati direttamente
        self._act_id = thermo_data.get("act_id")
        self._name = thermo_data.get("name")
        self._mode = thermo_data.get("mode", 0)
        self._status = thermo_data.get("status", 0)
        self._season = thermo_data.get("season", "winter")
        self._temperature = thermo_data.get("temp_dec")
        self._set_point = thermo_data.get("set_point")
        self._fan_speed = thermo_data.get("fan_speed")
        
        self._zone = zone
        self._room = room
        
        # Dati aggiuntivi
        self._hygro = thermo_data.get("hygro")
        self._f3a_window_open = thermo_data.get("f3a", {}).get("window_open", 0) == 1
        self._f3a_presence = thermo_data.get("f3a", {}).get("presence", 0) == 1
        self._t1 = thermo_data.get("t1")
        self._t2 = thermo_data.get("t2")
        self._t3 = thermo_data.get("t3")
        self._antifreeze = thermo_data.get("antifreeze")
        self._thermo_algo = thermo_data.get("thermo_algo") or {}
        self._selected_profile_day = _WEEKDAY_ORDER[datetime.now().weekday()]
        self._profile_draft_by_day: Dict[str, str] = {}
        self._profile_raw_by_day: Dict[int, str] = {}
        self._apply_profile_data_array(thermo_data.get("profile_data") or [])
        self._apply_profile_info(thermo_data.get("profile_info", {}) or {}) 
        
        _LOGGER.debug("THERMOSTAT created: %s (ID: %d)", 
                     self._name, self._act_id)

    @property
    def act_id(self) -> int:
        """Restituisce l'ID attuatore."""
        return self._act_id

    @property
    def name(self) -> str:
        """Restituisce il nome del termostato."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Restituisce l'ID univoco per HA."""
        return f"climate.domo_{self.act_id}_{self.name.lower().replace(' ', '_')}"

    @property
    def gateway(self):
        """Restituisce il gateway associato al termostato."""
        return self._gateway

    @property
    def zone(self) -> str:
        """Restituisce la zona."""
        return self._zone
        
    @property
    def room(self) -> str:  # <-- NUOVA PROPERTY
        """Restituisce la stanza."""
        return self._room        

    @property
    def current_temperature(self) -> float:
        """Restituisce la temperatura corrente in °C, o None se non ancora nota."""
        return self._temperature / 10.0 if self._temperature is not None else None

    @property
    def target_temperature(self) -> float:
        """Restituisce la temperatura target in °C, o None se non ancora nota."""
        return self._set_point / 10.0 if self._set_point is not None else None

    @property
    def current_humidity(self) -> Optional[float]:
        """Restituisce l'umidità corrente se disponibile."""
        if self._hygro is not None:
            try:
                return float(self._hygro)
            except (ValueError, TypeError):
                _LOGGER.debug("Invalid hygro value for %s: %s", self.name, self._hygro)
                return None
        return None

    @property
    def hvac_mode(self) -> str:
        """Restituisce la modalità HVAC corrente."""
        return THERMO_MODES.get(self._mode, "off")

    @property
    def hvac_action(self) -> str:
        """Restituisce l'azione corrente (heating/idle/off)."""
        if self._mode == 0:  # Off
            return "off"
        
        if self._status == 1:  # Richiesta attiva
            if self._season == "winter":
                return "heating"
            elif self._season == "summer":
                return "cooling"
        return "idle"

    @property
    def status(self) -> str:
        """Restituisce lo stato testuale (off/idle/active)."""
        if self._mode == 0:
            return "off"
        return "active" if self._status == 1 else "idle"

    @property
    def fan_mode(self) -> Optional[str]:
        """Restituisce la modalità ventola."""
        if self._fan_speed is None:
            return None
        fan_map = {1: "low", 2: "medium", 3: "high", 4: "auto"}
        return fan_map.get(self._fan_speed, "auto")

    @property
    def is_window_open(self) -> bool:
        """Restituisce True se finestra aperta rilevata."""
        return self._f3a_window_open

    @property
    def is_occupied(self) -> bool:
        """Restituisce True se presenza rilevata."""
        return self._f3a_presence
        
    @property
    def profile_data(self) -> Optional[str]:
        """Restituisce la stringa grezza del profilo termico (96 caratteri) attualmente in vigore."""
        if self._mode == 3:  # Jolly
            jolly_id = PROFILE_DAY_TO_ID["Jolly"]
            if jolly_id in self._profile_raw_by_day:
                return self._profile_raw_by_day[jolly_id]        
        today_id = PROFILE_DAY_TO_ID[_WEEKDAY_ORDER[datetime.now().weekday()]]
        if today_id in self._profile_raw_by_day:
            return self._profile_raw_by_day[today_id]
        return self._profile_info.get("profile_data")
        
    @property
    def thermal_profile_schedule(self) -> List[Dict[str, Any]]:
        """Blocchi orari compressi decodificati dal profilo termico."""
        return decode_thermal_profile(self.profile_data, self._t1, self._t2, self._t3)        
        
    @property
    def t1(self) -> Optional[float]:
        return self._t1 / 10.0 if self._t1 is not None else None

    @property
    def t2(self) -> Optional[float]:
        return self._t2 / 10.0 if self._t2 is not None else None

    @property
    def t3(self) -> Optional[float]:
        return self._t3 / 10.0 if self._t3 is not None else None
        
    @property
    def antifreeze(self) -> Optional[float]:
        return self._antifreeze / 10.0 if self._antifreeze is not None else None
        
    @property
    def season(self) -> str:
        """Restituisce la stagione impostata (winter/summer/plant_off)."""
        return self._season

    @property
    def t1_raw(self) -> Optional[int]:
        """Valore t1 grezzo (decimi di grado), per backup/restore senza perdita di precisione."""
        return self._t1

    @property
    def t2_raw(self) -> Optional[int]:
        return self._t2

    @property
    def t3_raw(self) -> Optional[int]:
        return self._t3

    @property
    def profile_raw_by_day(self) -> Dict[int, str]:
        """Restituisce {profile_id: profile_data} dei profili grezzi noti (0-6=Lun..Dom, 7=Jolly)."""
        return dict(self._profile_raw_by_day)        
            
    @property
    def algo_mode(self) -> Optional[str]:
        """Restituisce la modalità algoritmo corrente"""
        algo_type = self._thermo_algo.get("type")
        pi_set = self._thermo_algo.get("pi_set_in_use") if algo_type == "P" else None
        return _ALGO_PARAMS_TO_MODE.get((algo_type, pi_set))

    @property
    def diff_t_dec(self) -> Optional[float]:
        """Restituisce il differenziale termico (°C) usato in modalità DIFF."""
        value = self._thermo_algo.get("diff_t_dec")
        return value / 10.0 if value is not None else None        
        
    @property
    def scheduled_setpoint(self) -> Optional[float]:
        """Restituisce il set-point (°C) attualmente in vigore secondo il profilo termico."""
        profile_data = self.profile_data
        if not profile_data:
            return None

        now = datetime.now()
        quarter_index = now.hour * 4 + now.minute // 15
        if quarter_index >= len(profile_data):
            return None

        char = profile_data[quarter_index]
        setpoint_name = PROFILE_CHAR_TO_SETPOINT.get(char)
        if setpoint_name is None:
            return None

        setpoint_dec = getattr(self, f"_{setpoint_name}")
        return setpoint_dec / 10.0 if setpoint_dec is not None else None        
        
    @property
    def support_fan(self) -> bool:
        """Restituisce True se supporta ventola."""
        return self._fan_speed is not None

    async def async_set_hvac_mode(self, hvac_mode: str):
        """Imposta la modalità HVAC."""
        if self._set_point is None:
            _LOGGER.debug("THERMOSTAT %s: set_point non ancora noto, comando ignorato", self.name)
            return False        
        mode_map = {v: k for k, v in THERMO_MODES.items()}
        mode_code = mode_map.get(hvac_mode, 0)
        
        payload = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self._act_id,
            "mode": mode_code,
            "set_point": self._set_point,
            "extended_infos": 0
        }
        
        await self._gateway.tx_command(payload, resp_command=None)
        return True

    async def async_set_temperature(self, temperature: float):
        """Imposta la temperatura target."""
        set_point = int(temperature * 10)
        
        payload = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self._act_id,
            "mode": self._mode,
            "set_point": set_point,
            "extended_infos": 0
        }
        
        await self._gateway.tx_command(payload, resp_command=None)
        return True

    async def async_set_manual_temperature(self, temperature: float):
        """Passa in manuale impostando contestualmente il set-point desiderato."""
        set_point = int(temperature * 10)

        payload = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self._act_id,
            "mode": 1,
            "set_point": set_point,
            "extended_infos": 0
        }

        await self._gateway.tx_command(payload, resp_command=None)
        return True 

    async def async_set_fan_mode(self, fan_mode: str):
        """Imposta la modalità ventola."""
        fan_map = {"low": 1, "medium": 2, "high": 3, "auto": 4}
        fan_speed = fan_map.get(fan_mode, 4)
        
        payload = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self._act_id,
            "mode": self._mode,
            "set_point": self._set_point,
            "extended_infos": 1,
            "fan_speed": fan_speed
        }
        
        await self._gateway.tx_command(payload, resp_command=None)
        return True

    @property
    def selected_profile_day(self) -> str:
        return self._selected_profile_day

    def set_selected_profile_day(self, day: str) -> None:
        if day not in PROFILE_DAY_TO_ID:
            raise ValueError(f"Giorno non valido: {day}")
        self._selected_profile_day = day

    @property
    def profile_draft(self) -> str:
        """Bozza locale (non letta dal gateway) per il giorno correntemente selezionato."""
        return self._profile_draft_by_day.get(self._selected_profile_day, "")

    async def async_set_thermal_profile(self, schedule_str: str) -> bool:
        """Scrive il profilo termico del giorno correntemente selezionato."""
        if self._set_point is None:
            _LOGGER.debug("THERMOSTAT %s: set_point non ancora noto, comando ignorato", self.name)
            return False
        profile_id = PROFILE_DAY_TO_ID[self._selected_profile_day]
        base_profile_data = self._profile_raw_by_day.get(profile_id)
        try:
            profile_data = encode_thermal_profile(schedule_str, base_profile_data=base_profile_data)
        except ThermalProfileError as err:
            _LOGGER.warning(
                "THERMOSTAT %s: input profilo non valido (giorno=%s, input=%r): %s",
                self.act_id, self._selected_profile_day, schedule_str, err,
            )
            raise
        _LOGGER.debug(
            "📈THERMOSTAT %s: profilo giorno=%s base=%r input=%r -> profile_data=%r",
            self.act_id, self._selected_profile_day, base_profile_data, schedule_str, profile_data,
        )
        payload = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self._act_id,
            "mode": self._mode,
            "set_point": self._set_point,
            "extended_infos": 1,
            "profile_id": profile_id,
            "profile_data": profile_data,
        }
        await self._gateway.tx_command(payload, resp_command=None)
        self._profile_draft_by_day[self._selected_profile_day] = decode_thermal_profile_to_schedule_str(profile_data)
        self._profile_raw_by_day[profile_id] = profile_data
        return True
       
    async def async_set_thermal_profile_value(self, attr_key: str, value: float) -> bool:
        """Imposta uno dei valori di profilo termico (t1/t2/t3/antifreeze)"""
        if attr_key not in ("t1", "t2", "t3", "antifreeze"):
            raise ValueError(f"attr_key non valido: {attr_key}")
        if self._set_point is None:
            _LOGGER.debug("THERMOSTAT %s: set_point non ancora noto, comando ignorato", self.name)
            return False

        values = {
            "t1": self._t1,
            "t2": self._t2,
            "t3": self._t3,
            "antifreeze": self._antifreeze,
        }
        values[attr_key] = int(round(value * 10))

        if any(v is None for v in values.values()) or not self._thermo_algo:
            _LOGGER.debug(
                "THERMOSTAT %s: profilo termico non ancora completo (%s, thermo_algo=%s), comando ignorato",
                self.name, values, self._thermo_algo,
            )
            return False

        payload = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self._act_id,
            "mode": self._mode,
            "set_point": self._set_point,
            "extended_infos": 1,
            "t1": values["t1"],
            "t2": values["t2"],
            "t3": values["t3"],
            "antifreeze": values["antifreeze"],
            "thermo_algo": self._thermo_algo,
        }

        await self._gateway.tx_command(payload, resp_command=None)
        return True        

    async def async_write_raw_profile(self, profile_id: int, profile_data: str) -> bool:
        """Scrive una stringa profilo (96 caratteri) già codificata, senza merge con la base."""
        if self._set_point is None:
            _LOGGER.debug("THERMOSTAT %s: set_point non ancora noto, comando ignorato", self.name)
            return False
        payload = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self._act_id,
            "mode": self._mode,
            "set_point": self._set_point,
            "extended_infos": 1,
            "profile_id": profile_id,
            "profile_data": profile_data,
        }
        await self._gateway.tx_command(payload, resp_command=None)
        day_name = PROFILE_ID_TO_DAY.get(profile_id)
        if day_name:
            self._profile_draft_by_day[day_name] = decode_thermal_profile_to_schedule_str(profile_data)
        self._profile_raw_by_day[profile_id] = profile_data
        return True

    async def async_set_algo_mode(self, mode: str) -> bool:
        """Imposta la modalità dell'algoritmo di regolazione (PI1/PI2/PI3/PI4/DIFF)"""
        if mode not in ALGO_MODE_TO_PARAMS:
            raise ValueError(f"algo_mode non valido: {mode}")
        if self._set_point is None:
            _LOGGER.debug("THERMOSTAT %s: set_point non ancora noto, comando ignorato", self.name)
            return False

        values = {"t1": self._t1, "t2": self._t2, "t3": self._t3, "antifreeze": self._antifreeze}
        if any(v is None for v in values.values()) or not self._thermo_algo:
            _LOGGER.debug(
                "THERMOSTAT %s: profilo termico non ancora completo (%s, thermo_algo=%s), comando ignorato",
                self.name, values, self._thermo_algo,
            )
            return False

        new_algo = dict(self._thermo_algo)
        new_algo.pop("pi_set_in_use", None)
        new_algo.update(ALGO_MODE_TO_PARAMS[mode])

        payload = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self._act_id,
            "mode": self._mode,
            "set_point": self._set_point,
            "extended_infos": 1,
            "t1": values["t1"],
            "t2": values["t2"],
            "t3": values["t3"],
            "antifreeze": values["antifreeze"],
            "thermo_algo": new_algo,
        }

        await self._gateway.tx_command(payload, resp_command=None)
        return True

    async def async_set_diff_t_dec(self, value: float) -> bool:
        """Imposta il differenziale termico (°C, 0.1-2.0) usato in modalità DIFF"""
        if self._set_point is None:
            _LOGGER.debug("THERMOSTAT %s: set_point non ancora noto, comando ignorato", self.name)
            return False

        values = {"t1": self._t1, "t2": self._t2, "t3": self._t3, "antifreeze": self._antifreeze}
        if any(v is None for v in values.values()) or not self._thermo_algo:
            _LOGGER.debug(
                "THERMOSTAT %s: profilo termico non ancora completo (%s, thermo_algo=%s), comando ignorato",
                self.name, values, self._thermo_algo,
            )
            return False

        new_algo = dict(self._thermo_algo)
        new_algo["diff_t_dec"] = int(round(value * 10))

        payload = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self._act_id,
            "mode": self._mode,
            "set_point": self._set_point,
            "extended_infos": 1,
            "t1": values["t1"],
            "t2": values["t2"],
            "t3": values["t3"],
            "antifreeze": values["antifreeze"],
            "thermo_algo": new_algo,
        }

        await self._gateway.tx_command(payload, resp_command=None)
        return True        

    def _apply_profile_info(self, profile_info: Dict[str, Any]) -> None:
            """Aggiorna profile_info, giorno selezionato e bozza."""
            self._profile_info = profile_info
            active_day = PROFILE_ID_TO_DAY.get(profile_info.get("profile_id"))
            if active_day is None:
                return
            self._selected_profile_day = active_day
            profile_data = profile_info.get("profile_data")
            if profile_data:
                self._profile_draft_by_day[active_day] = decode_thermal_profile_to_schedule_str(profile_data)
                profile_id = profile_info.get("profile_id")
                if profile_id is not None:
                    self._profile_raw_by_day[profile_id] = profile_data
                    
    def _apply_profile_data_array(self, profile_data_array: List[str]) -> None:
        """Popola tutti i giorni (0-7: Lun...Dom, Jolly)"""
        for day_id, raw in enumerate(profile_data_array):
            day_name = PROFILE_ID_TO_DAY.get(day_id)
            if day_name is None:
                continue
            self._profile_raw_by_day[day_id] = raw
            self._profile_draft_by_day[day_name] = decode_thermal_profile_to_schedule_str(raw)


    def update_state(self, data: Dict[str, Any]):
        """Aggiorna lo stato in base ai dati ricevuti."""
        if data.get("act_id") != self.act_id:
            return False
        
        if "mode" in data:
            self._mode = data.get("mode")
        if "status" in data:
            self._status = data.get("status")
        if "temp_dec" in data:
            temp_dec = data.get("temp_dec")
            if temp_dec is not None and 30 <= temp_dec <= 350:
                self._temperature = temp_dec
        if "set_point" in data:
            self._set_point = data.get("set_point")
        if "fan_speed" in data:
            self._fan_speed = data.get("fan_speed")
        if "season" in data:
            self._season = data.get("season")
        if "hygro" in data:
            hygro = data.get("hygro")
            if hygro is not None and 0 <= hygro <= 100:
                self._hygro = hygro       
        if "f3a" in data:
            f3a = data["f3a"]
            self._f3a_window_open = f3a.get("window_open", 0) == 1
            self._f3a_presence = f3a.get("presence", 0) == 1
        if "profile_info" in data:
            self._apply_profile_info(data.get("profile_info") or {})
        if "t1" in data:
            self._t1 = data.get("t1")
        if "t2" in data:
            self._t2 = data.get("t2")
        if "t3" in data:
            self._t3 = data.get("t3")  
        if "antifreeze" in data:
            self._antifreeze = data.get("antifreeze")
        if "thermo_algo" in data:
            self._thermo_algo = data.get("thermo_algo") or self._thermo_algo            
                
        _LOGGER.debug("🌡️Thermostat %s state updated", self.name)
        return True


def handle_thermostat_status_update(gateway, device_info: Dict[str, Any]) -> bool:
    """Gestisce gli aggiornamenti di stato dei termostati."""

    act_id = device_info.get("act_id")
    if not act_id:
        return False

    thermostat = get_thermostat(act_id)
    if not thermostat:
        return False

    updated = thermostat.update_state(device_info)

    if updated and gateway.hass:
        async_dispatcher_send(
            gateway.hass,
            SIGNAL_UPDATE_ENTITY,
            thermostat.unique_id
        )

    return updated
