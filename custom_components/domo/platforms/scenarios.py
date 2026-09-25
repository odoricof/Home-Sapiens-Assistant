"""
platforms/scenarios.py

Entities fed by this file:
- domo/text.py : scenario name/status text (name_draft, status_message, submit_text_value)
- domo/button.py : start/stop registration, delete and rename buttons
- domo/select.py : scenario target select (user_defined_scenarios, target_id)

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
import logging
from typing import Any

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)


_SCENARIO_DEVICE: DomoScenarioDevice | None = None


# ============================================================
# ===== SCENARIO DEVICE =====
# ============================================================

class DomoScenarioDevice:
    """Container device for all Domo scenarios."""

    def __init__(self, gateway):
        self._gateway = gateway
        self._name = "Scenarios"
        self._act_id = -1
        self._registration_state = "idle"
        self._name_draft: str = ""
        self._target_id: int | None = None
        self._status_message: str | None = None
        self._status_token: int = 0
        self._pending_action: str | None = None
        self._pending_action_event: asyncio.Event | None = None
        self._scenarios_cache: list[dict[str, Any]] = []
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
        return "scene.domo_scenarios"

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

    @property
    def rename_pending(self) -> bool:
        return self._rename_pending

    @property
    def target_id(self) -> int | None:
        return self._target_id

    @property
    def user_defined_scenarios(self) -> list[dict[str, Any]]:
        """User-created scenarios (excludes the factory ones)."""
        return [s for s in self._scenarios_cache if s.get("user-defined") == 1]

    def set_name_draft(self, value: str) -> None:
        self._name_draft = value
        self._notify_scenario_ui()

    def set_target(self, scenario_id: int | None) -> None:
        self._target_id = scenario_id

    async def available_scenarios(self) -> list[dict[str, Any]]:
        """Return the list of available scenarios."""
        return await self._get_scenarios()

    async def activate_scenario(self, scenario_id: int) -> bool:
        """Activate an existing scenario."""
        await self._gateway.tx_command({
            "cmd_name": "scenario_activation_req",
            "id": scenario_id
        }, resp_command=None)

        _LOGGER.debug("Activated scenario %d", scenario_id)
        return True

    async def create_scenario(self, name: str) -> bool:
        """Start recording a new scenario."""
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

    async def stop_scenario_registration(self) -> dict[str, Any] | None:
        """Stop the recording and return the gateway response, if any."""
        resp = await self._gateway.tx_command({
            "cmd_name": "scenario_registration_done"
        }, resp_command="scenario_registration_done_resp")

        self._registration_state = "idle"
        return resp

    async def start_registration(self) -> bool:
        """Start recording using the name currently in name_draft."""
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
        """Stop the recording; the scenario is saved only if changes were recorded."""
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
            confirmed = await self.wait_for_user_action("create")
        await self._get_scenarios()
        self._name_draft = ""

        if confirmed:
            self._set_status_message(f"Scenario creato: {name}", transient=True)
        else:
            self._set_status_message("Annullato, scenario vuoto", transient=True)
        return "ok" if confirmed else "empty"

    async def delete_scenario(self, scenario_id: int) -> bool:
        """Delete an existing scenario."""
        self._arm_pending_action("delete")
        await self._gateway.tx_command({
            "cmd_name": "scenario_delete_req",
            "id": scenario_id
        }, resp_command=None)

        _LOGGER.debug("Deleted scenario %d", scenario_id)
        return True

    async def delete_scenario_by_name(self, name: str) -> str:
        """Delete the user-defined scenario matching `name`."""
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
        """Enter rename_pending for the scenario named in name_draft."""
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
        """Single text submit entry point: new name while renaming, else name draft."""
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
        except Exception as err:
            _LOGGER.warning("Scenario rename failed: %s", err)
            confirmed = False

        await self._get_scenarios()
        self._rename_pending = False
        self._rename_target_id = None

        if confirmed:
            self._set_status_message("Eseguito", transient=True)
        else:
            self._set_status_message("Errore durante la rinomina", transient=True)

    async def rename_scenario(self, scenario_id: int, name: str) -> None:
        """Rename an existing scenario."""
        self._arm_pending_action("rename")
        await self._gateway.tx_command({
            "cmd_name": "scenario_rename_req",
            "id": scenario_id,
            "name": name
        }, resp_command=None)

        _LOGGER.debug("Renamed scenario %d to %s", scenario_id, name)

    async def wait_for_user_action(self, expected_action: str, timeout: float = 5.0) -> bool:
        """Wait up to `timeout` seconds for the scenario_user_ind event of `expected_action`."""
        if not (self._pending_action == expected_action and self._pending_action_event is not None):
            self._pending_action = expected_action
            self._pending_action_event = asyncio.Event()
        event = self._pending_action_event
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except TimeoutError:
            return False
        finally:
            self._pending_action = None
            self._pending_action_event = None

    async def async_execute(self) -> str:
        """Execute button orchestrator: start/stop recording, rename or delete."""
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
            if ok:
                self._notify_scenario_ui()
            else:
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

    def notify_user_action(self, action: str) -> None:
        """Release the pending wait if `action` matches the armed one."""
        if self._pending_action == action and self._pending_action_event is not None:
            self._pending_action_event.set()

    async def _get_scenarios(self) -> list[dict[str, Any]]:
        """Fetch the scenarios list from the gateway and refresh the cache."""
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

    def _arm_pending_action(self, action: str) -> None:
        """Arm the scenario_user_ind wait early so the gateway notification is not lost."""
        self._pending_action = action
        self._pending_action_event = asyncio.Event()

    def _set_status_message(self, message: str, transient: bool = False) -> None:
        """Update the status text; a transient message is cleared after 2 seconds."""
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
        """Refresh the name/status text and the start/stop registration buttons."""
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
        """Refresh the scenario target select."""
        hass = self._gateway.hass
        if hass:
            async_dispatcher_send(hass, SIGNAL_UPDATE_ENTITY, "domo_scenario_target_select")


# ============================================================
# ===== DISCOVERY AND ACCESSORS =====
# ============================================================

async def discover_scenarios(gateway) -> list[DomoScenarioDevice]:
    """Create the scenarios device."""
    _LOGGER.debug("Discovering scenarios device")

    scenario_device = DomoScenarioDevice(gateway)
    _LOGGER.debug("Scenarios device created")
    return [scenario_device]


def get_scenario_device() -> DomoScenarioDevice | None:
    """Return the scenarios device."""
    return _SCENARIO_DEVICE


# ============================================================
# ===== GATEWAY EVENT HANDLERS =====
# ============================================================

def handle_scenario_status_update(gateway, device_info) -> None:
    """Handle scenario status and user-action events from the gateway."""
    cmd_name = device_info.get("cmd_name")
    if not cmd_name:
        return

    if cmd_name == "scenario_status_ind":
        scenario_id = device_info.get("id")
        _LOGGER.debug("Scenario status update for ID %s: %s", scenario_id, device_info)

        if gateway and gateway.hass:
            async_dispatcher_send(
                gateway.hass,
                "domo_scenario_update",
                scenario_id,
                device_info
            )

    elif cmd_name == "scenario_user_ind":
        action = device_info.get("action")
        _LOGGER.debug("Scenario user action: %s", action)

        device = get_scenario_device()
        if device:
            device.notify_user_action(action)

        if action in ("add", "create", "rename", "delete"):
            if gateway and gateway.hass:
                async_dispatcher_send(
                    gateway.hass,
                    "domo_scenarios_refreshed"
                )
