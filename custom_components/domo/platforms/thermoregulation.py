"""
domo/platforms/thermoregulation.py

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

# Mappa delle modalità termostato
THERMO_MODES = {
    0: "off",
    1: "manual",    
    2: "auto",
    3: "jolly",
}

# Mappa fissa: carattere del profilo -> quale set-point (t1/t2/t3) usare
PROFILE_CHAR_TO_SETPOINT = {
    "1": "t1",
    "2": "t1",
    "3": "t2",
    "4": "t2",
    "5": "t3",
}

QUARTER_MINUTES = 15

# Dizionario globale per tenere traccia di tutti i termostati
_THERMOSTATS: dict[int, "DomoThermostat"] = {}

def _slot_to_time_str(slot_index: int) -> str:
    """Converte l'indice di quarto d'ora (0-95) in stringa HH:MM."""
    total_minutes = slot_index * QUARTER_MINUTES
    hour = (total_minutes // 60) % 24
    minute = total_minutes % 60
    return f"{hour:02d}:{minute:02d}"


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


async def discover_thermostats(gateway):
    """Scopri tutti i termostati disponibili."""
    _LOGGER.info("THERMOSTATS starting discovery")
    
    try:
        # Richiedi lista termostati
        resp = await gateway.tx_command({
            "cmd_name": "nested_thermo_list_req",
            "topologic_scope": "plant"
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
                    await refresh_auto_profile(gateway, thermo_obj)
        
        _LOGGER.info("THERMOSTATS discovered %d devices", len(thermostats_found))
        return thermostats_found
        
    except Exception as err:
        _LOGGER.error("THERMOSTATS discovery failed: %s", err)
        return None

async def refresh_auto_profile(gateway, thermostat: "DomoThermostat"):
    """Se il termostato è già in AUTO, ri-manda mode=auto per forzare l'invio del profilo termico completo."""
    if thermostat._mode != 2:  # non è in auto, niente da fare
        return None
    if thermostat._set_point is None:
        _LOGGER.debug(
            "THERMOSTAT %s: set_point non ancora noto, refresh profilo saltato",
            thermostat.act_id,
        )
        return None
    try:
        resp = await gateway.tx_command({
            "cmd_name": "thermo_zone_config_req",
            "act_id": thermostat.act_id,
            "mode": 2,  # auto
            "set_point": thermostat._set_point,
            "extended_infos": 0,
        }, resp_command=None)
        _LOGGER.debug("THERMOSTAT %s refresh profilo response: %s", thermostat.act_id, resp)
        return resp
    except Exception as err:
        _LOGGER.error("THERMOSTAT %s refresh profilo failed: %s", thermostat.act_id, err)
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
        self._profile_info = thermo_data.get("profile_info", {}) or {}
        self._t1 = thermo_data.get("t1")
        self._t2 = thermo_data.get("t2")
        self._t3 = thermo_data.get("t3")
        self._antifreeze = thermo_data.get("antifreeze")
        
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
        """Restituisce la stringa grezza del profilo termico (96 caratteri)."""
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
        """Passa in manuale impostando contestualmente il set-point desiderato.
        Un'unica richiesta: evita la corsa a due comandi separati (mode + set_point)."""
        set_point = int(temperature * 10)

        payload = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self._act_id,
            "mode": 1,  # manual
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

    def update_state(self, data: Dict[str, Any]):
        """Aggiorna lo stato in base ai dati ricevuti."""
        if data.get("act_id") != self.act_id:
            return False
        
        # Aggiorna i valori principali
        if "mode" in data:
            self._mode = data.get("mode")
        if "status" in data:
            self._status = data.get("status")
        if "temp_dec" in data:
            self._temperature = data.get("temp_dec")
        if "set_point" in data:
            self._set_point = data.get("set_point")
        if "fan_speed" in data:
            self._fan_speed = data.get("fan_speed")
        if "season" in data:
            self._season = data.get("season")
        
        # Aggiorna dati aggiuntivi
        if "hygro" in data:
            self._hygro = data.get("hygro")        
        if "f3a" in data:
            f3a = data["f3a"]
            self._f3a_window_open = f3a.get("window_open", 0) == 1
            self._f3a_presence = f3a.get("presence", 0) == 1
        if "profile_info" in data:
            self._profile_info = data.get("profile_info") or {}
        if "t1" in data:
            self._t1 = data.get("t1")
        if "t2" in data:
            self._t2 = data.get("t2")
        if "t3" in data:
            self._t3 = data.get("t3")  
        if "antifreeze" in data:
            self._antifreeze = data.get("antifreeze")            
                
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

    #_LOGGER.debug("🌡️ Thermostat update received: %s", device_info)

    updated = thermostat.update_state(device_info)

    if updated and gateway.hass:
        async_dispatcher_send(
            gateway.hass,
            SIGNAL_UPDATE_ENTITY,
            thermostat.unique_id
        )

    return updated
