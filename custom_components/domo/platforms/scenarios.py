"""
platforms/scenarios.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""
from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any, List

from homeassistant.helpers.dispatcher import async_dispatcher_send
 
from ..const import SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)

# Dizionario per tenere traccia degli scenari (usiamo un ID fisso -1 per il dispositivo contenitore)
_SCENARIO_DEVICE = None


class DomoScenarioDevice:
    """Dispositivo contenitore per tutti gli scenari Domo."""

    def __init__(self, gateway):
        self._gateway = gateway
        self._name = "Scenari"
        self._act_id = -1  # ID fisso per il contenitore scenari
        self._registration_state = "idle"  # "idle" | "recording"
        self._name_draft: str = ""
        self._target_id: int | None = None
        self._status_message: str | None = None
        self._status_token: int = 0
        self._pending_action: str | None = None
        self._pending_action_event: asyncio.Event | None = None
        self._scenarios_cache: List[Dict[str, Any]] = []
        self._rename_pending: bool = False
        self._rename_target_id: int | None = None
        
        global _SCENARIO_DEVICE
        _SCENARIO_DEVICE = self
        
        _LOGGER.debug("SCENARIO device created")

    @property
    def act_id(self) -> int:
        return self._act_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"scene.domo_scenarios"
        
    @property
    def registration_state(self) -> str:
        return self._registration_state

    @property
    def status_message(self) -> str | None:
        return self._status_message
        
    @property
    def can_start_registration(self) -> bool:
        return self._registration_state == "idle" and bool(self._name_draft)

    @property
    def can_stop_registration(self) -> bool:
        return self._registration_state == "recording"

    @property
    def name_draft(self) -> str:
        return self._name_draft

    def set_name_draft(self, value: str) -> None:
        self._name_draft = value
        self._notify_scenario_ui()
        
    @property
    def rename_pending(self) -> bool:
        return self._rename_pending
        
    @property
    def target_id(self) -> int | None:
        return self._target_id

    def set_target(self, scenario_id: int | None) -> None:
        self._target_id = scenario_id

    @property
    def user_defined_scenarios(self) -> List[Dict[str, Any]]:
        """Scenari creati dall'utente (esclude i 4 scenari di fabbrica)."""
        return [s for s in self._scenarios_cache if s.get("user-defined") == 1]
              

    async def available_scenarios(self) -> List[Dict[str, Any]]:
        """Restituisce la lista degli scenari disponibili."""
        return await self._get_scenarios()

    async def _get_scenarios(self) -> List[Dict[str, Any]]:
        """Recupera la lista degli scenari dal gateway."""
        resp = await self._gateway.tx_command({
            "cmd_name": "scenarios_list_req"
        }, resp_command="scenarios_list_resp")
        
        if not resp:
            _LOGGER.error("No response from gateway for scenarios list")
            return []
        
        scenarios = resp.get("array", [])
        _LOGGER.debug("Retrieved %d scenarios", len(scenarios))
        self._scenarios_cache = scenarios
        return scenarios

    async def activate_scenario(self, scenario_id: int) -> bool:
        """Attiva uno scenario esistente."""
        await self._gateway.tx_command({
            "cmd_name": "scenario_activation_req",
            "id": scenario_id
        }, resp_command=None)  # Non aspettiamo risposta specifica
        
        _LOGGER.debug("Activated scenario %d", scenario_id)
        return True

    async def create_scenario(self, name: str) -> bool:
        """Inizia la registrazione di un nuovo scenario."""
        resp = await self._gateway.tx_command({
            "cmd_name": "scenario_registration_start",
            "name": name
        }, resp_command="scenario_registration_resp")
        
        success = bool(resp and resp.get("result") == 1)
        if success:
            self._registration_state = "recording"
            self._arm_pending_action("create")
            _LOGGER.debug("Started scenario creation: %s", name)
        return success

    async def stop_scenario_registration(self) -> bool:
        """Termina la registrazione in corso e salva lo scenario (solo se
        sono stati registrati cambi di stato nel frattempo)."""
        resp = await self._gateway.tx_command({
            "cmd_name": "scenario_registration_done"
        }, resp_command="scenario_registration_done_resp")

        self._registration_state = "idle"
        return resp

    async def start_registration(self) -> bool:
        """Avvia la registrazione di un nuovo scenario usando il nome
        correntemente scritto in name_draft. Chiamato dal button
        'Avvia registrazione scenario'."""
        if self._registration_state == "recording":
            return False
        if self._rename_pending:
            self._set_status_message("Nuovo nome: ", transient=False)
            return False
            
        if not self._name_draft:
            self._set_status_message("Inserire nome nuovo scenario", transient=True)
            return False
            
        ok = await self.create_scenario(self._name_draft)
        if ok:
            self._notify_scenario_ui()
        else:
            self._set_status_message("Errore avvio registrazione", transient=True)
        return ok

    async def stop_registration(self) -> str:
        """Ferma la registrazione in corso. Se sono stati registrati
        cambiamenti, lo scenario e' salvato; altrimenti annulla.
        Chiamato dal button 'Ferma registrazione scenario'."""
        if self._registration_state != "recording":
            self._set_status_message("Nessuna registrazione in corso", transient=True)
            return "not_recording"
 
        name = self._name_draft
        resp = await self.stop_scenario_registration()
        result = resp.get("result") if resp else None

        if result == 1:
            confirmed = True
        elif result == 0:
            confirmed = False
        else:
            # Nessuna risposta dal gateway (caso raro osservato in test):
            # usiamo l'evento asincrono come rete di sicurezza.
            confirmed = await self.wait_for_user_action("create")
        await self._get_scenarios()
        self._name_draft = ""

        if confirmed:
            self._set_status_message(f"Scenario creato: {name}", transient=True)
        else:
            self._set_status_message("Annullato, scenario vuoto", transient=True)
        return "ok" if confirmed else "empty"


    async def delete_scenario(self, scenario_id: int) -> bool:
        """Elimina uno scenario esistente."""
        self._arm_pending_action("delete")
        await self._gateway.tx_command({
            "cmd_name": "scenario_delete_req",
            "id": scenario_id
        }, resp_command=None)  # il gateway risponde con un generic_reply

        _LOGGER.debug("Deleted scenario %d", scenario_id)
        return True

    async def delete_scenario_by_name(self, name: str) -> str:
        """Cancella lo scenario il cui nome corrisponde a `name` (letto dal
        text). Chiamato dal button 'Cancella scenario'."""
        if self._registration_state == "recording":
            self._set_status_message("Registrazione in corso", transient=True)
            return "recording"
        if self._rename_pending:
            self._set_status_message("Nuovo nome: ", transient=False)
            return "rename_pending"
        if not name:
            self._set_status_message("Inserire nome scenario da cancellare", transient=True)
            return "empty"

        scenarios = await self._get_scenarios()
        match = next((s for s in scenarios if s.get("name") == name), None)

        if match is None:
            self._name_draft = ""
            self._set_status_message("Scenario inesistente", transient=True)
            return "not_found"

        if match.get("user-defined") != 1:
            self._name_draft = ""
            self._set_status_message("Scenario non cancellabile", transient=True)
            return "not_deletable"

        ok = await self.delete_scenario(match.get("id"))
        confirmed = await self.wait_for_user_action("delete") if ok else False
        await self._get_scenarios()
        self._name_draft = ""

        if confirmed:
            self._set_status_message(f"Scenario cancellato: {name}", transient=True)
            return "ok"
        self._set_status_message("Errore durante la cancellazione", transient=True)
        return "error"

    async def start_rename(self) -> str:
        """Avvia il flusso di rinomina per lo scenario il cui nome e'
        scritto nel text. Se valido, entra in stato 'rename_pending': la
        prossima submit del text sara' interpretata come nuovo nome
        invece che come nome scenario. Chiamato dal button 'Rinomina
        scenario'."""
        if self._registration_state == "recording":
            self._set_status_message("Registrazione in corso", transient=True)
            return "recording"

        if self._rename_pending:
            return "already_pending"

        name = self._name_draft
        if not name:
            self._set_status_message("Inserire nome scenario da rinominare", transient=True)
            return "empty"

        scenarios = await self._get_scenarios()
        match = next((s for s in scenarios if s.get("name") == name), None)

        if match is None:
            self._name_draft = ""
            self._set_status_message("Scenario inesistente", transient=True)
            return "not_found"

        if match.get("user-defined") != 1:
            self._name_draft = ""
            self._set_status_message("Scenario non rinominabile", transient=True)
            return "not_renamable"

        self._rename_target_id = match.get("id")
        self._rename_pending = True
        self._name_draft = ""
        self._set_status_message("Nuovo nome: ", transient=False)
        return "pending"

    async def submit_text_value(self, value: str) -> None:
        """Punto di ingresso unico per il submit del text: se e' in corso
        un rename (rename_pending), interpreta `value` come nuovo nome
        (con o senza il prefisso 'Nuovo nome:'); altrimenti si comporta
        come il normale set_name_draft."""
        if not self._rename_pending:
            self.set_name_draft(value)
            return

        prefix = "Nuovo nome:"
        new_name = value[len(prefix):].strip() if value.startswith(prefix) else value

        if not new_name:
            self._set_status_message("Nuovo nome: ", transient=False)
            return

        scenarios = await self._get_scenarios()
        if any(s.get("name") == new_name for s in scenarios):
            self._set_status_message("Nome già esistente", transient=True)
            return

        target_id = self._rename_target_id
        try:
            await self.rename_scenario(target_id, new_name)
            confirmed = await self.wait_for_user_action("rename")
        except Exception:
            confirmed = False

        await self._get_scenarios()
        self._rename_pending = False
        self._rename_target_id = None

        if confirmed:
            self._set_status_message("Eseguito", transient=True)
        else:
            self._set_status_message("Errore durante la rinomina", transient=True)

    async def rename_scenario(self, scenario_id: int, name: str) -> None:
        """Rinomina uno scenario esistente."""
        self._arm_pending_action("rename")
        await self._gateway.tx_command({
            "cmd_name": "scenario_rename_req",
            "id": scenario_id,
            "name": name
        }, resp_command=None)  # il gateway risponde con un generic_reply

        _LOGGER.debug("Renamed scenario %d to %s", scenario_id, name)

    async def wait_for_user_action(self, expected_action: str, timeout: float = 5.0) -> bool:
        """Attende l'evento asincrono scenario_user_ind con l'azione attesa
        (create/rename/delete), entro `timeout` secondi."""
        if not (self._pending_action == expected_action and self._pending_action_event is not None):
            # Non era stato armato in anticipo (caso raro): arma ora.
            self._pending_action = expected_action
            self._pending_action_event = asyncio.Event()
        event = self._pending_action_event
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            self._pending_action = None
            self._pending_action_event = None

    def _arm_pending_action(self, action: str) -> None:
        """Predispone in anticipo l'attesa dell'evento scenario_user_ind per
        `action`. Necessario perché il gateway può inviare la notifica
        asincrona (es. 'create') non appena l'utente modifica qualcosa,
        molto prima che venga premuto lo stop / chiamato wait_for_user_action:
        senza armare subito l'evento, quella notifica verrebbe persa."""
        self._pending_action = action
        self._pending_action_event = asyncio.Event()

    def _set_status_message(self, message: str, transient: bool = False) -> None:
        """Aggiorna il messaggio del text di stato e notifica l'entità.
        Se `transient`, il messaggio viene rimosso dopo 2 secondi."""
        self._status_token += 1
        my_token = self._status_token
        self._status_message = message
        self._notify_scenario_ui()
        hass = self._gateway.hass

        if transient and hass:
            async def _revert():
                await asyncio.sleep(2)
                if my_token == self._status_token:
                    self._status_message = None
                    self._notify_scenario_ui()
            hass.async_create_task(_revert())

    def _notify_scenario_ui(self) -> None:
        """Notifica il text del nome/stato e i due button di
        avvio/stop registrazione (la loro availability dipende dallo
        stato del device)."""
        hass = self._gateway.hass
        if not hass:
            return
        for uid in (
            "domo_scenario_name_text",
            "domo_scenario_start_registration_button",
            "domo_scenario_stop_registration_button",
        ):
            async_dispatcher_send(hass, SIGNAL_UPDATE_ENTITY, uid)

    def _notify_target_select(self) -> None:
        hass = self._gateway.hass
        if hass:
            async_dispatcher_send(hass, SIGNAL_UPDATE_ENTITY, "domo_scenario_target_select")

    async def async_execute(self) -> str:
        """Orchestratore invocato dal pulsante 'esegui': decide start/stop
        registrazione oppure rename/delete in base allo stato corrente e al
        contenuto correntemente impostato in name_draft/target_id."""

        if self._registration_state == "recording":
            name = self._name_draft
            ok = await self.stop_scenario_registration()
            if not ok:
                message = "Errore durante il salvataggio"
            else:
                confirmed = await self.wait_for_user_action("create")
                await self._get_scenarios()
                message = (
                    f'Scenario "{name}" salvato' if confirmed
                    else "Nessuna modifica registrata: scenario non salvato"
                )
            self._name_draft = ""
            self._set_status_message(message, transient=True)
            self._notify_target_select()
            return message

        name = self._name_draft
        target_id = self._target_id

        if target_id is None:
            if not name:
                return ""
            ok = await self.create_scenario(name)
            message = f"Registrazione in corso: {name}" if ok else "Errore avvio registrazione"
            if not ok:
                self._set_status_message(message, transient=True)
            return message

        if not name:
            await self.delete_scenario(target_id)
            confirmed = await self.wait_for_user_action("delete")
            await self._get_scenarios()
            message = "Scenario eliminato" if confirmed else "Errore durante l'eliminazione"
        else:
            await self.rename_scenario(target_id, name)
            confirmed = await self.wait_for_user_action("rename")
            await self._get_scenarios()
            message = f'Scenario rinominato in "{name}"' if confirmed else "Errore durante il rename"

        self._name_draft = ""
        self._target_id = None
        self._set_status_message(message, transient=True)
        self._notify_target_select()
        return message        

async def discover_scenarios(gateway):
    """Scopri il device scenari."""
    _LOGGER.debug("Discovering scenarios device")
    
    scenario_device = DomoScenarioDevice(gateway)
    _LOGGER.debug("Scenarios device created")
    return [scenario_device]


def get_scenario_device():
    """Restituisce il device scenari."""
    return _SCENARIO_DEVICE


def handle_scenario_status_update(gateway, device_info):
    """Gestisce aggiornamenti di stato degli scenari."""
    cmd_name = device_info.get("cmd_name")
    if not cmd_name:
        return
    
    # Gestisci aggiornamento stato scenario
    if cmd_name == "scenario_status_ind":
        scenario_id = device_info.get("id")
        _LOGGER.debug("Scenario status update for ID %d: %s", scenario_id, device_info)
        
        if gateway and gateway.hass:
            # Invia segnale per aggiornamento specifico scenario
            async_dispatcher_send(
                gateway.hass,
                "domo_scenario_update",
                scenario_id,
                device_info
            )
            
    # Gestisci creazione/modifica scenario da UI
    elif cmd_name == "scenario_user_ind":
        action = device_info.get("action")
        _LOGGER.debug("Scenario user action: %s", action)

        device = get_scenario_device()
        if device and device._pending_action == action and device._pending_action_event:
            device._pending_action_event.set()

        if action in ("add", "create", "rename", "delete"):
            if gateway and gateway.hass:
                # Invia segnale per refresh lista scenari
                async_dispatcher_send(
                    gateway.hass,
                    "domo_scenarios_refreshed"
                )
