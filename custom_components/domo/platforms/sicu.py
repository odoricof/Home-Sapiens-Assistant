"""
domo/platforms/sicu.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""

from __future__ import annotations
from homeassistant.helpers.dispatcher import async_dispatcher_send
from ..const import DOMAIN, SIGNAL_UPDATE_ENTITY
import logging
import threading
from typing import Dict, Any, Optional



_LOGGER = logging.getLogger(__name__)

TYPE_SECURITY_CENTRAL = -10

_SECURITY_DEVICE: Optional["SecurityCentral"] = None

# ============================================================
# INTERROGA PRESENZA CENTRALI
# ============================================================

async def discover_security(gateway):
    """Scopri le centrali di sicurezza disponibili."""
    global _SECURITY_DEVICE
    
    if _SECURITY_DEVICE is not None:
        return _SECURITY_DEVICE
    
    _LOGGER.info("SECURITY starting discovery")
    
    try:
        # 1. Feature list per vedere se 'sicu' è supportato
        feat_resp = await gateway.tx_command(
            {"cmd_name": "feature_list_req"},
            resp_command=None
        )
        
        if not feat_resp:
            _LOGGER.debug("SECURITY discovery: no feature list response")
            return None
            
        features = feat_resp.get("list", [])
        if "sicu" not in features:
            _LOGGER.debug("SECURITY discovery: sicu not supported")
            return None
            
        _LOGGER.info("SECURITY: sicu feature supported")
        
        # 2. Richiedi lista aree (central_id=0)
        areas_resp = await gateway.tx_command({
            "appl_msg_type": "sicu",
            "cmd_name": "sicu_areas_list_req",
            "central_id": 0
        }, resp_command=None)
        
        # 3. Richiedi lista ingressi (central_id=0)
        inputs_resp = await gateway.tx_command({
            "appl_msg_type": "sicu",
            "cmd_name": "sicu_inputs_list_req",
            "central_id": 0
        }, resp_command=None)
        
        # 4. Richiedi lista scenari (central_id=0)
        scenarios_resp = await gateway.tx_command({
            "appl_msg_type": "sicu",
            "cmd_name": "sicu_scenarios_list_req",
            "central_id": 0
        }, resp_command=None)
        
        # 5. Crea la centrale con i dati raccolti
        central_info = {
            "central_id": 0,
            "name": "Proxinet",
            "areas_num": len(areas_resp.get("array", [])),
            "inputs_num": len(inputs_resp.get("array", [])),
            "scenarios_num": len(scenarios_resp.get("array", []))
        }
        
        _LOGGER.info(
            "SECURITY central discovered | central_id=0 name=Proxinet"
        )
        
        _SECURITY_DEVICE = SecurityCentral(gateway, central_info)
        
        # Popola aree e ingressi con i dati già ricevuti
        if areas_resp:
            await _SECURITY_DEVICE.update(areas_resp)
        if inputs_resp:
            await _SECURITY_DEVICE.update(inputs_resp)
        if scenarios_resp:
            await _SECURITY_DEVICE.update(scenarios_resp)
            
        return _SECURITY_DEVICE
        
    except Exception as err:
        _LOGGER.error("SECURITY discovery failed: %s", err)
        return None

# ============================================================
# FACTORY / HANDLER
# ============================================================

async def handle_security_status_update(gateway, device_info: Dict[str, Any]) -> bool:
    """
    Punto UNICO di ingresso per i pacchetti SECURITY dal gateway.
    gateway: il gateway che ha ricevuto l'evento
    event_data: il payload dell'evento
    """
    global _SECURITY_DEVICE

    cmd = device_info.get("cmd_name")
    if not isinstance(cmd, str) or not cmd.startswith("sicu_"):
        return False

    # Se la centrale non esiste ancora, ignora TUTTI gli eventi
    # La discovery deve essere fatta prima separatamente
    if _SECURITY_DEVICE is None:
        _LOGGER.debug(
            "SECURITY RX %s ignorato (centrale non ancora scoperta - chiamare discover_security() prima)",
            cmd,
        )
        return False


    # --------------------------------------------------
    # UPDATE DEL DEVICE SECURITY
    # --------------------------------------------------
    updated = await _SECURITY_DEVICE.update(device_info)
    return updated



# ============================================================
# DEVICE
# ============================================================

class SecurityCentral:
    """Centrale di sicurezza (singleton)."""

    DEVICE_TYPE = "Security"

    def __init__(self, gateway, central_info: Optional[Dict] = None):
        self._gateway = gateway
        self._type_id = TYPE_SECURITY_CENTRAL
        self._act_id = None
        self._hass = gateway.hass
        self._initialized = False
        
        # ---- stato centrale ----
        self._state: Dict[str, Any] = {
            "central_id": None,
            "name": "Security",
            "status": 0,
            "areas_num": 0,
            "inputs_num": 0,
            "outputs_num": 0,
            "scenarios_num": 0,
            "extra": None,
        }

        # Se abbiamo info iniziali, aggiorna
        if central_info:
            self._state.update({
                "central_id": central_info.get("central_id"),
                "name": central_info.get("name", "Security"),
                "areas_num": central_info.get("areas_num", 0),
                "inputs_num": central_info.get("inputs_num", 0),
                "outputs_num": central_info.get("outputs_num", 0),
                "scenarios_num": central_info.get("scenarios_num", 0),
                "extra": central_info.get("extra"),
            })



        # ---- dati dinamici ----
        self._areas: list[dict] = []
        self._known_area_ids: set[int] = set()
        self._areas_state: dict[int, dict] = {}
       
        # ---- snapshot HA ----
        self._last_snapshot: Optional[Dict[str, Any]] = None
        self._scenarios: dict[int, dict] = {}
        
        # MAPPING DEGLI SCENARI
        self._scenario_by_arm: dict[str, int] = {
            "armed_away": 0,   # ESCO DI CASA
            "armed_night": 1,  # VADO A LETTO
            "armed_home": 2,   # RESTO IN CASA
        }
        self.available = False
        self.update_pending = False
        
        # ---- ingressi ----
        self._inputs_state: dict[int, dict] = {}
        self._inputs: list[dict] = []

        _LOGGER.debug(
            "SECURITY device initialized | uid=%s | thread=%s | mapping=%s",
            self.unique_id,
            threading.current_thread().name,
            self._scenario_by_arm,
        )

    # --------------------------------------------------
    # REQUEST ALL LISTS
    # --------------------------------------------------
    async def _request_all_lists(self):
        """Richiedi tutte le liste di configurazione."""
        if self._initialized:
            return
            
        _LOGGER.info("SECURITY requesting all lists for central_id=%s", self.central_id)
        
        # Richiedi lista aree
        await self._gateway.tx_command({
            "cmd_name": "sicu_areas_list_req",
            "central_id": self.central_id
        })
        
        # Richiedi lista ingressi
        await self._gateway.tx_command({
            "cmd_name": "sicu_inputs_list_req",
            "central_id": self.central_id
        })
        
        # Richiedi lista scenari
        await self._gateway.tx_command({
            "cmd_name": "sicu_scenarios_list_req",
            "central_id": self.central_id
        })
        
        self._initialized = True




    # --------------------------------------------------
    # IDENTITÀ
    # --------------------------------------------------

    @property
    def unique_id(self) -> str:
        return "security_central"

    @property
    def name(self) -> str:
        return self._state.get("name") or "Security"

    @property
    def state(self) -> Dict[str, Any]:
        return self._state
        
    @property
    def central_id(self) -> Optional[int]:
        return self._state.get("central_id")        

    # --------------------------------------------------
    # UPDATE CORE
    # --------------------------------------------------
    async def update(self, data: Dict[str, Any]) -> bool:
        """
        Accetta pacchetti sicu_* in QUALSIASI ordine.
        Tutta la logica SECURITY vive qui.
        """
        cmd = data.get("cmd_name")
        if not isinstance(cmd, str) or not cmd.startswith("sicu_"):
            return False

        updated = False

        # --------------------------------------------------
        # CENTRALE
        # --------------------------------------------------
        if cmd == "sicu_central_status_ind":
            updated = self._update_central(data)
   

        # --------------------------------------------------
        # AREE
        # --------------------------------------------------
        if cmd == "sicu_areas_status_ind":
            return self._update_areas(data)
            
        if cmd == "sicu_areas_list_resp":
            _LOGGER.info("SECURITY received areas list (%d items)", len(data.get("array", [])))
            for area in data.get("array", []):
                area_id = area.get("area_id")
                if area_id is not None:
                    self._areas_state[area_id] = area
                    self._known_area_ids.add(area_id)
            self._areas = list(self._areas_state.values())
            self._rebuild_snapshot()
            
            for area in self._areas:
                _LOGGER.debug("SECURITY area: %s (ID: %s, status base: %s)", 
                             area.get("name"), area.get("area_id"), area.get("status")) 
            
            return True            
            
 
        # --------------------------------------------------
        # SCENARI
        # --------------------------------------------------
        if cmd == "sicu_scenarios_list_resp":
            self._scenarios.clear()
            
            # Mapping fisso basato su ID
            self._scenario_by_arm = {
                "armed_away": 0,    # ESCO DI CASA
                "armed_night": 1,   # VADO A LETTO
                "armed_home": 2,    # RESTO IN CASA
            }

            for item in data.get("array", []) or []:
                scenario_id = item.get("scenario_id")
                if scenario_id is None:
                    continue
                self._scenarios[int(scenario_id)] = item

            _LOGGER.info(
                "SECURITY scenarios loaded | count=%s",
                len(self._scenarios),
            )

            for sid, scenario in self._scenarios.items():
                _LOGGER.debug("SECURITY scenario %d: %s (areas: %s) -> %s", 
                             sid,
                             scenario.get("name"),
                             scenario.get("areas"),
                             {0: "armed_away", 1: "armed_night", 2: "armed_home"}.get(sid, "unknown"))            
            return True
        # --------------------------------------------------
        # INGRESSI
        # --------------------------------------------------
        
        if cmd == "sicu_inputs_list_resp":
            _LOGGER.info("SECURITY received inputs list (%d items)", len(data.get("array", [])))
            for inp in data.get("array", []):
                input_id = inp.get("input_id")
                if input_id is not None:
                    self._inputs_state[input_id] = inp
            self._inputs = list(self._inputs_state.values())
            self._rebuild_snapshot()
            for inp in self._inputs:
                _LOGGER.debug("SECURITY input: %s (ID: %s, type: %s, areas: %s)", 
                             inp.get("name"), inp.get("input_id"), 
                             inp.get("type"), inp.get("areas"))                 
            return True        
        

        
        if cmd == "sicu_input_status_ind":
            input_id = data.get("input_id")
            if input_id is None:
                return False

            # aggiorna stato cumulativo ingresso
            self._inputs_state[input_id] = {
                "input_id": input_id,
                "name": data.get("name"),
                "status": data.get("status"),
                "areas": data.get("areas", []),
            }

            self._inputs = list(self._inputs_state.values())

            self._rebuild_snapshot()
            self.update_pending = True

            _LOGGER.debug(
                "SECURITY input updated | id=%s name=%s status=%s areas=%s",
                input_id,
                data.get("name"),
                data.get("status"),
                data.get("areas"),
            )
            return True
            
            
            
            
            
            

    # --------------------------------------------------
    # HANDLER SPECIFICI
    # --------------------------------------------------

    def _update_central(self, data: Dict[str, Any]) -> bool:
        self._state.update(
            {
                "central_id": data.get("central_id"),
                "name": data.get("name", self._state["name"]),
                "status": data.get("status", self._state["status"]),
                "areas_num": data.get("areas_num", self._state["areas_num"]),
                "inputs_num": data.get("inputs_num", self._state["inputs_num"]),
                "outputs_num": data.get("outputs_num", self._state["outputs_num"]),
                "scenarios_num": data.get("scenarios_num", self._state["scenarios_num"]),
                "extra": data.get("extra", self._state["extra"]),
            }
        )

        self.available = True
        self._rebuild_snapshot()
        self.update_pending = True

        _LOGGER.debug(
            "SECURITY central updated | id=%s status=%s",
            self._state.get("central_id"),
            self._state.get("status"),
        )
        return True

    def _update_areas(self, data: Dict[str, Any]) -> bool:
        # delta update: ETI/Domo invia solo le aree cambiate
        for area in data.get("array", []) or []:
            area_id = area.get("area_id")
            if area_id is None:
                continue

            # aggiorna stato cumulativo
            self._areas_state[area_id] = area
            self._known_area_ids.add(area_id)

        # ricostruisci SEMPRE la lista completa delle aree
        self._areas = list(self._areas_state.values())

        self._rebuild_snapshot()
        self.update_pending = True

        _LOGGER.debug(
            "SECURITY areas updated | count=%s | known=%s",
            len(self._areas),
            sorted(self._known_area_ids),
        )
        return True

        


    @property
    def alarm_state(self):
        """Determina lo stato dell'allarme basato sulle aree armate."""
        status = self.state.get("status", 0)

        if status == 0:
            return "disarmed"

        # Verifica quali aree sono armate
        armed_areas = self.get_current_armed_areas()
        
        if not armed_areas:
            return "disarmed"
        
        # Confronta con le aree di ogni scenario
        if armed_areas == set(self._scenarios.get(0, {}).get("areas", [])):  # ESCO DI CASA
            return "armed_away"
        elif armed_areas == set(self._scenarios.get(1, {}).get("areas", [])):  # VADO A LETTO
            return "armed_night"
        elif armed_areas == set(self._scenarios.get(2, {}).get("areas", [])):  # RESTO IN CASA
            return "armed_home"
        
        # Fallback
        return "armed_away"

    async def arm(self, arm_type: str, code: str | None = None):
        scenario_id = self._scenario_by_arm.get(arm_type)
        if scenario_id is None:
            _LOGGER.error("SECURITY no scenario for %s", arm_type)
            return

        # PRIMA chiamata HA (senza code) → IGNORA
        if not code:
            _LOGGER.debug("SECURITY arm pre-call without code (%s)", arm_type)
            return

        payload = {
            "cmd_name": "sicu_scenario_set_req",
            "scenario_id": scenario_id,
            "central_id": self.central_id,
            "code": code,
        }

        _LOGGER.info(
            "SECURITY TX | arm=%s scenario_id=%s",
            arm_type,
            scenario_id,
        )

        await self._gateway.tx_command(payload, resp_command=None)



        
    async def arm_away(self, code: str | None = None):
        await self.arm("armed_away", code)

    async def arm_home(self, code: str | None = None):
        await self.arm("armed_home", code)

    async def arm_night(self, code: str | None = None):
        await self.arm("armed_night", code)

    async def disarm(self, code: str | None = None):
        if not self._gateway:
            return

        payload = {
            "cmd_name": "sicu_areas_set_status_req",
            "central_id": 0,
            "status_vector": "000",
            "code": code or "",
            "client": "",
            "appl_msg_type": "sicu",
            "cseq": self._gateway.get_cseq(),
        }
        await self._gateway.tx_command(payload, resp_command=None)

    async def reset_event_memory(self, code: str | None = None):
        _LOGGER.info(">>> reset_event_memory CALLED with code: %s", code)
        if not self._gateway:
            return

        payload = {
            "cmd_name": "sicu_reset_req",
            "central_id": 0,
            "code": code or "",
            "client": "",
            "appl_msg_type": "sicu",
            "cseq": self._gateway.get_cseq(),
        }

        await self._gateway.tx_command(payload, resp_command=None)

    async def silence(self, code: str | None = None):
        """Tacita sirene / allarme in corso."""
        if not self._gateway:
            return

        payload = {
            "cmd_name": "sicu_silence_req",
            "central_id": 0,
            "code": code or "",
            "client": "",
            "appl_msg_type": "sicu",
            "cseq": self._gateway.get_cseq(),
        }

        await self._gateway.tx_command(payload, resp_command=None)


    def get_current_armed_areas(self) -> set[int]:
        data = self._last_snapshot or {}
        areas = data.get("areas", [])
        return {
            a["area_id"]
            for a in areas
            if a.get("status") == 42
        }

    def has_pending_areas(self) -> bool:
        data = self._last_snapshot or {}
        areas = data.get("areas", [])
        return any(a.get("status") == 41 for a in areas)
            

    # --------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------

    def _rebuild_snapshot(self):
        _LOGGER.debug(
            "SECURITY SNAPSHOT | central_status=%s | areas=%s | known_area_ids=%s",
            self._state.get("status"),
            self._areas,
            sorted(self._known_area_ids),
        )    
        self._last_snapshot = {
            "central": dict(self._state),
            "areas": list(self._areas),
            "inputs": list(self._inputs),
            "known_area_ids": sorted(self._known_area_ids),
            
            }
            
        self.update_pending = True

        # ⚡ Notifica l’entità HA che ci sono nuovi dati
        if self._hass:
            async_dispatcher_send(self._hass, SIGNAL_UPDATE_ENTITY)            
            
            
            

def get_security_device():
    """Return the SECURITY central singleton, if available."""
    return _SECURITY_DEVICE
