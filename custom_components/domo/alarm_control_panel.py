"""
domo/alarm_control_panel.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""


import logging
import time
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelState,
    AlarmControlPanelEntityFeature,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY


_LOGGER = logging.getLogger(__name__)

CENTRAL_STATUS_MAP = {
    0: "disinserita",
    256: "transizione",
    1024: "ingressi_non_armati_aperti",
    1280: "inserita_con_ingressi_esclusi_aperti",
    2048: "sconosciuto",
    2304: "violazione",
    3328: "allarme_intrusione",
    4096: "tempo_uscita_con_ingressi_aperti",
    4352: "tempo_uscita_con_aree_aperte",
    8192: "pronta",
    9216: "inserita",
    10240: "allarme_memorizzato",
    10496: "violazione",
    11264: "allarme_silenziato",
    11520: "allarme_innescato",
    12288: "inserimento_in_corso",
    14336: "tempo_uscita_con_eventi_memorizzati",    
}

AREA_STATUS_MAP = {
    #proxinet
    32: "non_pronta_con_ingressi_aperti",
    33: "inserimento_con_ingressi_aperti",
    34: "apertura_ingresso_in_attesa_disarmo",
    36: "intrusione_rilevata_e_ingressi_aperti",
    40: "pronta_con_ingressi_chiusi",
    41: "inserimento_in_corso",
    42: "inserita",
    38: "allarme_intrusione_in_corso",
    46: "intrusione_rilevata",
    44: "memoria_allarme",
    96: "ingressi_aperti_e_ingressi_esclusi",
    104: "pronta_con_ingressi_esclusi",
    
    #pxc
    48: "non_pronta_con_ingressi_aperti",
    56: "pronta_con_ingressi_chiusi",
    58: "inserita",
    60: "memoria_allarme",
    182: "allarme_intrusione_in_corso",
    190: "sconosciuto",

}

INPUT_STATUS_MAP = {
    1: "chiuso",
    5: "escluso",
    9: "memoria_allarme",
    16: "sconosciuto",
    17: "aperto",
    25: "allarme",
    65: "batteria_scarica",
}

SECURITY_DOMAIN = "alarm_control_panel"


# --------------------------------------------------
# SETUP / DISCOVERY
# --------------------------------------------------
async def async_setup_entry(hass, entry, async_add_entities):
    """Setup alarm control panel platform."""
    _LOGGER.debug("Setup piattaforma alarm_control_panel (SECURITY)")

    hass.data[DOMAIN].setdefault("_security_panel_added", False)

    from .platforms.sicu import get_security_device
    
    security = get_security_device()
    if security and not hass.data[DOMAIN]["_security_panel_added"]:
        _LOGGER.info(
            "SECURITY central already available, creating alarm panel | name=%s",
            security.name,
        )
        async_add_entities([DomoSecurityCentralEntity(security)])
        hass.data[DOMAIN]["_security_panel_added"] = True
    else:
        _LOGGER.debug("SECURITY central not yet available, will be created later")


# --------------------------------------------------
# ENTITY
# --------------------------------------------------
class DomoSecurityCentralEntity(AlarmControlPanelEntity):
    """ETI Domo security alarm panel."""

    def __init__(self, device):
        """Initialize the alarm panel."""
        self._device = device
        self._attr_unique_id = f"{device.unique_id}_panel"
        self._attr_name = device.name
        self._attr_should_poll = False
        self._last_armed_state = None
        self._alarm_notified = False
        self._alarm_notification_id = None
        
    @property
    def device_info(self):
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"central_{self._device.central_id}")},
            name=self._device.name,
            manufacturer="Home Sapiens",
            model=" ",
        )   
     
    # --------------------------------------------------
    # FEATURE
    # --------------------------------------------------
    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.ARM_NIGHT
        )

    # --------------------------------------------------
    # CODICE
    # --------------------------------------------------
    @property
    def code_arm_required(self) -> bool:
        """Whether the code is required for arm actions."""
        return True

    @property
    def code_format(self) -> str | None:
        """Return the code format."""
        return "number"

    # --------------------------------------------------
    # STATO
    # --------------------------------------------------
    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the state of the device."""
        device = self._device
        data = getattr(device, "_last_snapshot", None)

        if not data:
            return AlarmControlPanelState.DISARMED

        areas = data.get("areas", [])
        central = data.get("central", {})
        central_status = central.get("status")

        # 0. TRIGGERED
        if central_status in (3328, 11520, 11264, 2304, 10496):
            # Raccogli i sensori violati
            violated_inputs = []
            for inp in data.get("inputs", []):
                if inp.get("status") in (25, 17):
                    area_names = []
                    for area_id in inp.get("areas", []):
                        area = next((a for a in areas if a.get("area_id") == area_id), None)
                        if area:
                            area_names.append(area.get("name", f"area_{area_id}"))
                    
                    violated_inputs.append({
                        "name": inp.get("name", f"input_{inp.get('input_id')}"),
                        "area": ", ".join(area_names) if area_names else "Sconosciuta"
                    })
            
            # Invia notifiche (solo se non già inviate per questo evento)
            if violated_inputs and not self._alarm_notified:
                self._alarm_notified = True
                self.hass.async_create_task(
                    self._send_alarm_notifications(violated_inputs)
                )
            
            self._last_valid_state = AlarmControlPanelState.TRIGGERED
            return self._last_valid_state

        # 1. ARMING
        if central_status in (4096, 4352, 12288, 14336):
            return AlarmControlPanelState.ARMING

        # 2. insieme delle aree armate correnti
        armed_now = {
            a.get("area_id")
            for a in areas
            if a.get("status") in [42, 58]
        }

        # 3. DISARMED
        if not armed_now:
            self._last_armed_state = None
            return AlarmControlPanelState.DISARMED

        # 4. matching con scenari
        if central_status in (8192, 9216):
            scenarios = getattr(device, "_scenarios", {})

            if armed_now == set(scenarios.get(0, {}).get("areas", [])):
                self._last_armed_state = AlarmControlPanelState.ARMED_AWAY
                return self._last_armed_state
                
            if armed_now == set(scenarios.get(1, {}).get("areas", [])):
                self._last_armed_state = AlarmControlPanelState.ARMED_NIGHT
                return self._last_armed_state
                
            if armed_now == set(scenarios.get(2, {}).get("areas", [])):
                self._last_armed_state = AlarmControlPanelState.ARMED_HOME
                return self._last_armed_state
        
        # 5. Se abbiamo aree armate ma non matchiamo (sensori attivi), mantieni ultimo stato
        if armed_now and self._last_armed_state:
            return self._last_armed_state

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------
    async def async_added_to_hass(self):
        """When entity is added to hass."""
        _LOGGER.debug("SECURITY PANEL added to hass | entity_id=%s", self.entity_id)
        
        # Registra il servizio personalizzato
        if not self.hass.services.has_service(DOMAIN, "security_panel_action"):
            async def async_security_panel_action(call):
                entity_id = call.data.get("entity_id")
                action = call.data.get("action")
                code = call.data.get("code")

                _LOGGER.debug("security_panel_action called | entity_id=%s | action=%s", entity_id, action)
                _LOGGER.info(">>> SERVICE CALLED: %s - %s - target: %s", action, code, entity_id)
                _LOGGER.info(">>> MY ENTITY ID IS: %s", self.entity_id)

                if entity_id != self.entity_id:
                    _LOGGER.info(">>> ENTITY ID MISMATCH: %s != %s", entity_id, self.entity_id)
                    return
                _LOGGER.info(">>> SERVICE MATCHED - calling method on panel")  # <-- LOG
                
                if action == "reset_event_memory":
                    await self.reset_event_memory(code)
                elif action == "silence":
                    await self.silence(code)

            self.hass.services.async_register(
                DOMAIN,
                "security_panel_action",
                async_security_panel_action,
            )        
    
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle update signal."""
        if entity_id is not None and entity_id != self._attr_unique_id:
            return        
        data = getattr(self._device, "_last_snapshot", None)
        if data:
            central = data.get("central", {})
            central_status = central.get("status")
            
            # Se la centrale torna in stato 8192 (pronta), rimuovi la notifica
            if central_status == 8192 and self._alarm_notification_id:
                self.hass.async_create_task(self._clear_alarm_notification())
                self._alarm_notified = False
        
        self.async_write_ha_state()

    # --------------------------------------------------
    # COMANDI
    # --------------------------------------------------
    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self._device.disarm(code)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self._device.arm_home(code)
        
    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""
        await self._device.arm_night(code)
        
    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self._device.arm_away(code)
        
    async def reset_event_memory(self, code: str | None = None) -> None:
        _LOGGER.info(">>> PANEL.reset_event_memory called with code: %s", code)
        """Reset event memory."""
        await self._device.reset_event_memory(code)

    async def silence(self, code: str | None = None) -> None:
        """Silence alarm."""
        await self._device.silence(code)        
        
        
        
    # --------------------------------------------------
    # ATTRIBUTI EXTRA
    # --------------------------------------------------
    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        data = getattr(self._device, "_last_snapshot", None)
        if not data:
            return {}

        # CENTRALE
        central = data.get("central", {}) or {}
        central_raw = central.get("status")

        central_status = None
        if central_raw is not None:
            central_status = {
                "raw": central_raw,
                "state": CENTRAL_STATUS_MAP.get(
                    central_raw, f"sconosciuto_{central_raw}"
                ),
            }

        # AREE
        areas = data.get("areas", [])
        areas_status = {}

        # mappa area_id -> nome area
        area_id_to_name = {}

        for a in areas:
            area_id = a.get("area_id")
            raw_status = a.get("status")

            area_name = (
                a.get("name")
                or a.get("area_name")
                or f"area_{area_id}"
            )

            if area_id is not None:
                area_id_to_name[area_id] = area_name

            if raw_status is None:
                continue

            areas_status[area_name] = {
                "raw": raw_status,
                "state": AREA_STATUS_MAP.get(
                    raw_status, f"sconosciuto_{raw_status}"
                ),
            }

        # INGRESSI
        inputs = data.get("inputs", [])
        inputs_status = {}

        for i in inputs:
            input_id = i.get("input_id")
            raw_status = i.get("status")

            input_name = (
                i.get("name")
                or i.get("input_name")
                or f"input_{input_id}"
            )

            if raw_status is None:
                continue

            # traduzione aree [0,1,2] -> ["AREA GIORNO", ...]
            input_areas = [
                area_id_to_name.get(aid, f"area_{aid}")
                for aid in (i.get("areas") or [])
            ]

            inputs_status[input_name] = {
                "raw": raw_status,
                "state": INPUT_STATUS_MAP.get(
                    raw_status, f"sconosciuto_{raw_status}"
                ),
                "areas": input_areas,
            }

        return {
            "central": central_status,
            "areas": areas_status,
            "inputs": inputs_status,
        }
        
        
    async def _send_alarm_notifications(self, violated_inputs):
        """Invia notifiche push e persistenti per l'allarme."""
        
        # Prepara il messaggio
        if len(violated_inputs) == 1:
            msg = f"Sensore violato: {violated_inputs[0]['name']} (area {violated_inputs[0]['area']})"
        else:
            sensori = [f"{i['name']} (area {i['area']})" for i in violated_inputs]
            msg = f"Sensori violati: {', '.join(sensori)}"
        
        # 1. Notifiche push a TUTTI i dispositivi mobile_app
        # Ottieni tutti i servizi notify.mobile_app_*
        all_services = self.hass.services.async_services()
        mobile_app_services = [
            service for service in all_services.get("notify", [])
            if service.startswith("mobile_app_")
        ]
        
        if mobile_app_services:
            for service in mobile_app_services:
                try:
                    await self.hass.services.async_call(
                        "notify",
                        service,
                        {
                            "title": "🚨 ALLARME IN CORSO!",
                            "message": msg,
                            "data": {
                                "priority": "high",
                                "ttl": 0,
                                "importance": "max",
                                "vibrate": [500, 500, 500],
                                "color": "#FF0000",
                                "channel": "alarm",
                                "sound": "alarm.caf"
                            }
                        },
                        blocking=False  # non bloccare per inviare a più dispositivi
                    )
                except Exception as err:
                    _LOGGER.error("Failed to send push notification to %s: %s", service, err)
        else:
            _LOGGER.warning("Nessun dispositivo mobile_app registrato, notifiche push ignorate")
        
        # 2. Notifica persistente in Home Assistant (con ID fisso)
        self._alarm_notification_id = f"alarm_{int(time.time())}"
        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "🚨 ALLARME IN CORSO!",
                    "message": msg,
                    "notification_id": self._alarm_notification_id
                },
                blocking=True
            )
        except Exception as err:
            _LOGGER.error("Failed to create persistent notification: %s", err)
            
            
    async def _clear_alarm_notification(self):
        """Rimuove la notifica persistente quando l'allarme termina."""
        if self._alarm_notification_id:
            try:
                await self.hass.services.async_call(
                    "persistent_notification",
                    "dismiss",
                    {
                        "notification_id": self._alarm_notification_id
                    },
                    blocking=True
                )
                self._alarm_notification_id = None
                _LOGGER.debug("Alarm notification cleared")
            except Exception as err:
                _LOGGER.error("Failed to clear notification: %s", err)            
