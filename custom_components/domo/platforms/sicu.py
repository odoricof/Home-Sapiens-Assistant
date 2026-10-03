"""
platforms/sicu.py

Entities fed by this file:
- domo/alarm_control_panel.py : Alarm panel entity (arm/disarm, scenarios, central status)
- domo/binary_sensor.py       : Security outputs
- domo/sensor.py              : Security areas, security inputs
- domo/text.py                : Silencing, reset event memory
- domo/button.py              : Bypass open inputs
- domo/switch.py              : Input bypass

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
import threading
import time
from typing import Any

from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)


# ============================================================
# ===== UTILITY =====
# ============================================================

_SCENARIO_ROLE_KEYWORDS: dict[str, list[str]] = {
    "armed_away": ["esco", "fuori casa", "going out", "out", "sortir chez", "sortir", "abwesend", "weg", "fuera", "salir", "ухожу", "вне дома"],
    "armed_night": ["notte", "letto", "going to bed", "bed", "aller au lit", "lit", "nacht", "schlafen", "noche", "dormir", "ночь", "сон"],
    "armed_home": ["resto", "in casa", "staying home", "home", "rester chez", "rester", "zuhause", "bleibe", "casa", "quedo", "дома", "остаюсь"],
}


def _match_scenario_role(name: str | None) -> str | None:
    """Deduce the role (armed_away/night/home) from the central's scenario name."""
    upper = (name or "").upper()
    best_role = None
    best_len = 0
    for role, keywords in _SCENARIO_ROLE_KEYWORDS.items():
        for kw in keywords:
            if kw.upper() in upper and len(kw) > best_len:
                best_role = role
                best_len = len(kw)
    return best_role


# ============================================================
# ===== STATUS DECODING =====
# ============================================================

CENTRAL_STATUS_MAP = {
    0: "disarmed",
    256: "transition",
    1024: "unarmed_inputs_open",
    1280: "armed_with_bypassed_inputs_open",
    2048: "unknown",
    2304: "violation",
    3072: "intrusion_alarm_silenced",
    3328: "transition",
    4096: "exit_time_with_open_inputs",
    4352: "exit_time_with_open_areas",
    8192: "ready",
    8448: "transition",
    9216: "armed",
    10240: "alarm_memory",
    10496: "violation",
    11264: "alarm_silenced",
    11520: "alarm_triggered",
    12288: "arming_in_progress",
    14336: "exit_time_with_stored_events",
}

_AREA_STATUS_GROUPS = (
    ((32, 48), "not_ready"),
    ((33, 49), "arming_open_inputs"),
    ((34, 50), "input_open_pending_disarm"),
    ((36, 52), "intrusion_open_inputs"),
    ((40, 56), "ready"),
    ((41, 57), "arming"),
    ((42, 58), "armed"),
    ((44, 60), "alarm_memory"),
    ((38, 182), "intrusion_alarm"),
    ((46, 190), "intrusion_detected"),
    ((96, 112), "open_and_bypassed"),
    ((97, 113), "arming_open_and_bypassed"),
    ((104, 120), "ready_bypassed"),
    ((105, 121), "arming_bypassed"),
    ((106, 122), "armed_bypassed"),
)
AREA_STATUS_MAP = {code: status for codes, status in _AREA_STATUS_GROUPS for code in codes}

INPUT_STATUS_MAP = {
    1: "closed",
    5: "bypassed",
    9: "alarm_memory",
    16: "unknown",
    17: "open",
    21: "open_bypassed",
    25: "alarm",
    65: "low_battery",
}

BYPASSED_INPUT_STATUSES = {5, 21}

AREA_NOT_READY_STATUS = {32, 33, 48, 49, 96, 112}

SICU_INPUT_OPER_INCLUDE = 1
SICU_INPUT_OPER_EXCLUDE = 2
INPUT_BYPASS_CODE_WINDOW = 10
SICU_CODE_LENGTH = 6


class InputBypassDenied(ValueError):
    """Raised when an input bypass command is denied; carries which feedback applies."""

    def __init__(self, feedback: str, message: str):
        super().__init__(message)
        self.feedback = feedback


TYPE_SECURITY_CENTRAL = -10
_SECURITY_DEVICE: "SecurityCentral | None" = None


# ============================================================
# ===== CENTRAL DISCOVERY =====
# ============================================================

async def discover_security(gateway):
    """Discover the available security central."""
    global _SECURITY_DEVICE

    if _SECURITY_DEVICE is not None:
        return _SECURITY_DEVICE

    _LOGGER.info("SECURITY starting central discovery")

    try:
        feat_resp = await gateway.tx_command(
            {"cmd_name": "feature_list_req"},
            resp_command=None
        )

        if not feat_resp:
            _LOGGER.debug("SECURITY discovery: no response to feature list")
            return None

        features = feat_resp.get("list", [])
        if "sicu" not in features:
            _LOGGER.debug("SECURITY discovery: sicu feature not supported")
            return None

        _LOGGER.info("SECURITY sicu feature supported")

        areas_resp = await gateway.tx_command({
            "appl_msg_type": "sicu",
            "cmd_name": "sicu_areas_list_req",
            "central_id": 0
        }, resp_command=None)

        inputs_resp = await gateway.tx_command({
            "appl_msg_type": "sicu",
            "cmd_name": "sicu_inputs_list_req",
            "central_id": 0
        }, resp_command=None)

        scenarios_resp = await gateway.tx_command({
            "appl_msg_type": "sicu",
            "cmd_name": "sicu_scenarios_list_req",
            "central_id": 0
        }, resp_command=None)

        _LOGGER.debug("SECURITY requesting outputs list for central_id=0")
        outputs_resp = await gateway.tx_command({
            "appl_msg_type": "sicu",
            "cmd_name": "sicu_outputs_list_req",
            "central_id": 0
        }, resp_command=None)
        _LOGGER.debug("SECURITY outputs response: %s", outputs_resp)

        central_info = {
            "central_id": 0,
            "name": "Proxinet",
            "areas_num": len(areas_resp.get("array", [])) if areas_resp else 0,
            "inputs_num": len(inputs_resp.get("array", [])) if inputs_resp else 0,
            "scenarios_num": len(scenarios_resp.get("array", [])) if scenarios_resp else 0
        }

        _LOGGER.info("SECURITY central discovered | central_id=0 name=Proxinet")

        _SECURITY_DEVICE = SecurityCentral(gateway, central_info)

        if areas_resp:
            await _SECURITY_DEVICE.update(areas_resp)
        if inputs_resp:
            await _SECURITY_DEVICE.update(inputs_resp)
        if scenarios_resp:
            await _SECURITY_DEVICE.update(scenarios_resp)
        if outputs_resp:
            await _SECURITY_DEVICE.update(outputs_resp)

        return _SECURITY_DEVICE

    except Exception as err:
        _SECURITY_DEVICE = None
        _LOGGER.error("SECURITY central discovery failed: %s", err)
        return None


# ============================================================
# ===== RESYNC ON RECONNECT =====
# ============================================================

async def refresh_all_security(gateway):
    """Resync areas/inputs/outputs/scenarios after a gateway reconnect."""

    if _SECURITY_DEVICE is None:
        _LOGGER.debug("SECURITY refresh_all ignored: central not yet discovered")
        return

    central_id = _SECURITY_DEVICE.central_id or 0

    areas_resp = await gateway.tx_command({
        "appl_msg_type": "sicu",
        "cmd_name": "sicu_areas_list_req",
        "central_id": central_id
    }, resp_command=None)

    inputs_resp = await gateway.tx_command({
        "appl_msg_type": "sicu",
        "cmd_name": "sicu_inputs_list_req",
        "central_id": central_id
    }, resp_command=None)

    outputs_resp = await gateway.tx_command({
        "appl_msg_type": "sicu",
        "cmd_name": "sicu_outputs_list_req",
        "central_id": central_id
    }, resp_command=None)

    scenarios_resp = await gateway.tx_command({
        "appl_msg_type": "sicu",
        "cmd_name": "sicu_scenarios_list_req",
        "central_id": central_id
    }, resp_command=None)

    updated_count = 0
    for resp in (areas_resp, inputs_resp, outputs_resp, scenarios_resp):
        if resp and await _SECURITY_DEVICE.update(resp):
            updated_count += 1

    _LOGGER.info("SECURITY refresh_all completed | responses updated=%s/4", updated_count)


# ============================================================
# ===== EVENT HANDLER =====
# ============================================================

async def handle_security_status_update(_gateway, device_info: dict[str, Any]) -> bool:
    """Single entry point for SECURITY packets from the gateway."""
    global _SECURITY_DEVICE

    cmd = device_info.get("cmd_name")
    if not isinstance(cmd, str) or not cmd.startswith("sicu_"):
        return False

    if _SECURITY_DEVICE is None:
        _LOGGER.debug(
            "SECURITY RX %s ignored (central not yet discovered - call discover_security() first)",
            cmd,
        )
        return False

    updated = await _SECURITY_DEVICE.update(device_info)
    return updated


# ============================================================
# ===== SECURITY CENTRAL =====
# ============================================================

class SecurityCentral:
    """Security central (singleton)."""

    DEVICE_TYPE = "Security"

    def __init__(self, gateway, central_info: dict | None = None):
        self._gateway = gateway
        self._type_id = TYPE_SECURITY_CENTRAL
        self._act_id = None
        self._hass = gateway.hass

        self._state: dict[str, Any] = {
            "central_id": None,
            "name": "Security",
            "status": 0,
            "areas_num": 0,
            "inputs_num": 0,
            "outputs_num": 0,
            "scenarios_num": 0,
            "extra": None,
        }

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

        self._areas: list[dict] = []
        self._known_area_ids: set[int] = set()
        self._areas_state: dict[int, dict] = {}

        self._last_snapshot: dict[str, Any] | None = None
        self._scenarios: dict[int, dict] = {}

        self._scenario_by_arm: dict[str, int] = {}

        self.available = False
        self.update_pending = False

        self._inputs_state: dict[int, dict] = {}
        self._inputs: list[dict] = []

        self._outputs_state: dict[int, dict] = {}
        self._outputs: list[dict] = []

        self._bypass_code: str | None = None
        self._bypass_code_expiry: float = 0.0
        self._bypass_feedback: str | None = None
        self._bypass_window_token: int = 0
        # Serializes code verification and bypass commands towards the central,
        # so a switch toggled right after typing the code waits for the check.
        self._bypass_lock = asyncio.Lock()

        _LOGGER.debug(
            "SECURITY device initialized | uid=%s | thread=%s | mapping=%s",
            self.unique_id,
            threading.current_thread().name,
            self._scenario_by_arm,
        )

    # --- Identity ---

    @property
    def unique_id(self) -> str:
        return "security_central"

    @property
    def name(self) -> str:
        return self._state.get("name") or "Security"

    @property
    def state(self) -> dict[str, Any]:
        return self._state

    @property
    def central_id(self) -> int | None:
        return self._state.get("central_id")

    @property
    def inputs(self) -> list[dict]:
        return list(self._inputs)

    # --- Input state helpers ---

    def get_input_status(self, input_id: int) -> int | None:
        """Return the raw status of a single input, or None if unknown."""
        entry = self._inputs_state.get(input_id)
        return entry.get("status") if entry else None

    def is_input_bypassed(self, input_id: int) -> bool:
        """Return True if the input is bypassed, whether physically closed or still open."""
        return self.get_input_status(input_id) in BYPASSED_INPUT_STATUSES

    def get_open_input_ids(self) -> list[int]:
        """Return the ids of all inputs currently open or in alarm."""
        return [
            input_id
            for input_id, entry in self._inputs_state.items()
            if entry.get("status") in (17, 25)
        ]

    # --- Packet updates ---

    async def update(self, data: dict[str, Any]) -> bool:
        """Accept sicu_* packets in any order. All SECURITY logic lives here."""
        cmd = data.get("cmd_name")
        if not isinstance(cmd, str) or not cmd.startswith("sicu_"):
            return False

        if cmd == "sicu_central_status_ind":
            return self._update_central(data)

        if cmd == "sicu_areas_status_ind":
            return self._update_areas(data)

        if cmd == "sicu_areas_list_resp":
            _LOGGER.info("SECURITY areas list received (%d items)", len(data.get("array", [])))
            for area in data.get("array", []):
                area_id = area.get("area_id")
                if area_id is not None:
                    self._areas_state[area_id] = area
                    self._known_area_ids.add(area_id)
            self._areas = list(self._areas_state.values())
            self._rebuild_snapshot()

            for area in self._areas:
                _LOGGER.debug("SECURITY area: %s (ID: %s, base status: %s)",
                             area.get("name"), area.get("area_id"), area.get("status"))

            return True

        if cmd == "sicu_scenarios_list_resp":
            self._scenarios.clear()

            for item in data.get("array", []) or []:
                scenario_id = item.get("scenario_id")
                if scenario_id is None:
                    continue
                self._scenarios[int(scenario_id)] = item

            self._scenario_by_arm = {}
            for sid, scenario in self._scenarios.items():
                role = _match_scenario_role(scenario.get("name"))
                if role and role not in self._scenario_by_arm:
                    self._scenario_by_arm[role] = sid

            for sid in self._scenarios:
                if sid not in self._scenario_by_arm.values():
                    self._scenario_by_arm["armed_custom_bypass"] = sid
                    break

            _LOGGER.info("SECURITY scenarios loaded | count=%s", len(self._scenarios))

            for sid, scenario in self._scenarios.items():
                role = next((r for r, i in self._scenario_by_arm.items() if i == sid), "unknown")
                _LOGGER.debug("SECURITY scenario %d: %s (areas: %s) -> %s",
                             sid,
                             scenario.get("name"),
                             scenario.get("areas"),
                             role)
            return True

        if cmd == "sicu_inputs_list_resp":
            _LOGGER.info("SECURITY inputs list received (%d items)", len(data.get("array", [])))
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

        if cmd == "sicu_outputs_list_resp":
            _LOGGER.info("SECURITY outputs list received (%d items)", len(data.get("array", [])))
            for out in data.get("array", []):
                output_id = out.get("output_id")
                if output_id is not None:
                    self._outputs_state[output_id] = out
                    _LOGGER.debug("SECURITY output: %s (ID: %s, status: %s, extra: %s)",
                                 out.get("name"), output_id,
                                 out.get("status"), out.get("extra"))
            self._outputs = list(self._outputs_state.values())
            self._rebuild_snapshot()
            return True

        if cmd == "sicu_output_status_ind":
            output_id = data.get("output_id")
            if output_id is None:
                return False

            self._outputs_state[output_id] = {
                "output_id": output_id,
                "name": data.get("name"),
                "status": data.get("status"),
                "type": data.get("type", "generic"),
            }
            self._outputs = list(self._outputs_state.values())
            self._rebuild_snapshot()
            self.update_pending = True

            _LOGGER.debug(
                "SECURITY output updated | id=%s name=%s status=%s",
                output_id,
                data.get("name"),
                data.get("status"),
            )
            return True

        return False

    def _update_central(self, data: dict[str, Any]) -> bool:
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

    def _update_areas(self, data: dict[str, Any]) -> bool:
        for area in data.get("array", []) or []:
            area_id = area.get("area_id")
            if area_id is None:
                continue

            self._areas_state[area_id] = area
            self._known_area_ids.add(area_id)

        self._areas = list(self._areas_state.values())

        self._rebuild_snapshot()
        self.update_pending = True

        _LOGGER.debug(
            "SECURITY areas updated | count=%s | known=%s",
            len(self._areas),
            sorted(self._known_area_ids),
        )
        return True

    # --- Status decoding ---

    @staticmethod
    def decode_central_status(raw):
        if raw is None:
            return None
        return {"raw": raw, "state": CENTRAL_STATUS_MAP.get(raw, f"unknown_{raw}")}

    @staticmethod
    def decode_area_status(raw):
        if raw is None:
            return None
        return {"raw": raw, "state": AREA_STATUS_MAP.get(raw, f"unknown_{raw}")}

    @staticmethod
    def decode_input_status(raw):
        if raw is None:
            return None
        return {"raw": raw, "state": INPUT_STATUS_MAP.get(raw, f"unknown_{raw}")}

    # --- Scenario readiness ---

    def scenario_ready(self, arm_key: str) -> tuple[bool, list[str]]:
        """Return (ready, names of not-ready areas) for the areas of a role's scenario."""
        scenario_id = self._scenario_by_arm.get(arm_key)
        target_area_ids = set(self._scenarios.get(scenario_id, {}).get("areas", []))

        data = self._last_snapshot
        if not data or not target_area_ids:
            return True, []

        not_ready = []
        for area in data.get("areas", []):
            if area.get("area_id") in target_area_ids and area.get("status") in AREA_NOT_READY_STATUS:
                not_ready.append(area.get("name", f"area_{area.get('area_id')}"))

        return (len(not_ready) == 0), not_ready

    # --- Commands ---

    async def arm(self, arm_type: str, code: str | None = None):
        scenario_id = self._scenario_by_arm.get(arm_type)
        if scenario_id is None:
            _LOGGER.error("SECURITY no scenario for %s", arm_type)
            return

        if not code:
            _LOGGER.debug("SECURITY preliminary arm call without code (%s)", arm_type)
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

    async def arm_custom_bypass(self, code: str | None = None):
        await self.arm("armed_custom_bypass", code)

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
        _LOGGER.debug("SECURITY reset_event_memory called | code_provided=%s", bool(code))
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
        """Silence the active siren/alarm."""
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

    # --- Input bypass ---

    def start_input_bypass_window(self, code: str) -> None:
        """Open a time-limited window during which set_input_bypass() accepts `code`."""
        self._bypass_code = code
        self._extend_input_bypass_window()

        _LOGGER.info(
            "SECURITY input bypass window opened | duration=%ss",
            INPUT_BYPASS_CODE_WINDOW,
        )

    def _extend_input_bypass_window(self) -> None:
        """Reset the countdown to INPUT_BYPASS_CODE_WINDOW seconds and schedule its expiry."""
        self._bypass_code_expiry = time.monotonic() + INPUT_BYPASS_CODE_WINDOW
        self._bypass_window_token += 1
        my_token = self._bypass_window_token

        async def _expire():
            await asyncio.sleep(INPUT_BYPASS_CODE_WINDOW)
            if my_token == self._bypass_window_token:
                self._bypass_code = None
                if self._hass:
                    async_dispatcher_send(self._hass, SIGNAL_UPDATE_ENTITY)

        if self._hass:
            self._hass.async_create_task(_expire())
            async_dispatcher_send(self._hass, SIGNAL_UPDATE_ENTITY)

    @property
    def input_bypass_window_active(self) -> bool:
        return self._bypass_code is not None and time.monotonic() < self._bypass_code_expiry

    def _report_bypass_feedback(self, feedback: str) -> None:
        """Store transient bypass feedback for the code text entity to display."""
        self._bypass_feedback = feedback
        if self._hass:
            async_dispatcher_send(self._hass, SIGNAL_UPDATE_ENTITY)

    def pop_bypass_feedback(self) -> str | None:
        """Return and clear the last bypass feedback, if any (consumed once)."""
        feedback = self._bypass_feedback
        self._bypass_feedback = None
        return feedback

    async def verify_and_open_bypass_window(self, code: str) -> bool:
        """Verify `code` against the central with a harmless no-op command before
        opening the input bypass window. Returns True if the code was accepted.
        """
        async with self._bypass_lock:
            probe_id = self._get_bypass_probe_input_id()
            if probe_id is None:
                self.start_input_bypass_window(code)
                return True

            try:
                await self._send_bypass_wire_command(code, [probe_id], False)
            except ValueError:
                self._bypass_code = None
                return False

            self.start_input_bypass_window(code)
            return True

    def _get_bypass_probe_input_id(self) -> int | None:
        """Return the id of an already-included input, safe to use as a no-op code probe."""
        for input_id in self._inputs_state:
            if not self.is_input_bypassed(input_id):
                return input_id
        return None

    async def set_input_bypass(self, input_id: int, exclude: bool) -> None:
        """Bypass (exclude) or restore (include) a single alarm input.

        Requires a code opened via start_input_bypass_window() within the last
        INPUT_BYPASS_CODE_WINDOW seconds.
        """
        await self._send_input_bypass_command([input_id], exclude)

    async def bypass_open_inputs(self) -> list[int]:
        """Exclude every currently open (or in alarm) input in a single command.

        Requires a code opened via start_input_bypass_window() within the last
        INPUT_BYPASS_CODE_WINDOW seconds. Returns the ids that were excluded.
        """
        async with self._bypass_lock:
            open_ids = self.get_open_input_ids()
            if open_ids:
                await self._send_input_bypass_command_locked(open_ids, True)
            else:
                self._ensure_bypass_window()
            return open_ids

    def _ensure_bypass_window(self) -> None:
        if not self.input_bypass_window_active:
            self._report_bypass_feedback("no_code")
            raise InputBypassDenied("no_code", "Input bypass code window expired or not started")

    async def _send_input_bypass_command(self, input_ids: list[int], exclude: bool) -> None:
        # Waits here if the code is still being verified by the central.
        async with self._bypass_lock:
            await self._send_input_bypass_command_locked(input_ids, exclude)

    async def _send_input_bypass_command_locked(self, input_ids: list[int], exclude: bool) -> None:
        self._ensure_bypass_window()
        await self._send_bypass_wire_command(self._bypass_code, input_ids, exclude)
        self._extend_input_bypass_window()

    async def _send_bypass_wire_command(self, code: str, input_ids: list[int], exclude: bool) -> None:
        """Send sicu_multi_input_set_req and raise ValueError if the central rejects it."""
        payload = {
            "cmd_name": "sicu_multi_input_set_req",
            "central_id": self.central_id,
            "code": code,
            "client": "",
            "appl_msg_type": "sicu",
            "cseq": self._gateway.get_cseq(),
            "id": input_ids,
            "oper": SICU_INPUT_OPER_EXCLUDE if exclude else SICU_INPUT_OPER_INCLUDE,
        }

        _LOGGER.info(
            "SECURITY TX | input bypass | input_ids=%s exclude=%s",
            input_ids, exclude,
        )

        ack = await self._gateway.tx_command(payload, resp_command="sicu_multi_input_set_ack")

        if not ack:
            _LOGGER.warning(
                "SECURITY input bypass no confirmation from central | input_ids=%s",
                input_ids,
            )
            return

        if ack.get("ack_type"):
            _LOGGER.warning(
                "SECURITY input bypass rejected by central | input_ids=%s ack_type=%s",
                input_ids, ack.get("ack_type"),
            )
            self._report_bypass_feedback("wrong_code")
            raise InputBypassDenied("wrong_code", "Input bypass command rejected by central unit")

    # --- Snapshot ---

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
            "outputs": list(self._outputs),
            "known_area_ids": sorted(self._known_area_ids),
        }

        self.update_pending = True

        if self._hass:
            async_dispatcher_send(self._hass, SIGNAL_UPDATE_ENTITY)


def get_security_device():
    """Return the SECURITY central singleton, if available."""
    return _SECURITY_DEVICE
