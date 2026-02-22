from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .const import SIGNAL_GATEWAY_ONLINE, SIGNAL_GATEWAY_OFFLINE

_LOGGER = logging.getLogger(__name__)

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

DOMO_ENDPOINT = "/domo/"
STATUS_UPDATE_CMD = "status_update_req"


class DomoGateway:
    """
    Gateway ETI/Domo:
    - login
    - polling rx_status
    - logging pacchetti grezzi
    - nessuna logica di piattaforma
    """

    def __init__(
        self,
        hass,
        host: str,
        username: str = DEFAULT_USERNAME,
        password: str = DEFAULT_PASSWORD,
        poll_interval: float = 2.0,  # MODIFICATO: aumentato a 2 secondi per non sovraccaricare
    ):
        self.hass = hass
        self.host = host
        self.username = username
        self.password = password
        self.poll_interval = poll_interval

        self._session: aiohttp.ClientSession | None = None
        self._client_id: str = ""
        self._keep_alive_sec: int = 0
        self._session_expire_ts: float = 0.0

        self._running = False
        self._task: asyncio.Task | None = None
        self._event_callbacks = []
     
        self._was_connected = True

    async def test_connection(self):
        """Test connection to gateway."""
        self._session = aiohttp.ClientSession()
        try:
            await self._login()
            return True
        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False
        finally:
            await self.stop() 
         
     
     
     
    def register_event_callback(self, callback):
        """Registra una funzione da chiamare per ogni evento ricevuto."""
        self._event_callbacks.append(callback)
        _LOGGER.debug("DOMO Event callback registered, total: %d", len(self._event_callbacks))        

    # --------------------------------------------------
    # Lifecycle
    # --------------------------------------------------

    async def start(self):
        """Avvia il gateway."""
        if self._running:
            return

        _LOGGER.info("DOMO gateway starting (%s)", self.host)

        self._session = aiohttp.ClientSession()
        await self._login()

        self._running = True
        self._task = self.hass.loop.create_task(self._poll_loop())

    async def stop(self):
        """Ferma il gateway."""
        _LOGGER.info("DOMO gateway stopping")

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._session:
            await self._session.close()
            self._session = None

    # --------------------------------------------------
    # Core loop
    # --------------------------------------------------

    async def _poll_loop(self):
        """Loop continuo rx_status."""
        while self._running:
            try:
                await self.rx_status()
            except Exception as err:
                _LOGGER.error("DOMO rx_status error: %s", err)
                
            await asyncio.sleep(self.poll_interval)

    # --------------------------------------------------
    # HTTP helpers
    # --------------------------------------------------

    def _endpoint_url(self) -> str:
        return f"http://{self.host}{DOMO_ENDPOINT}"

    async def _post(self, payload: dict) -> dict:
        assert self._session is not None

        data = {"command": json.dumps(payload)}

        try:
            async with self._session.post(
                self._endpoint_url(),
                data=data,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Connection": "Keep-Alive",
                },
                timeout=aiohttp.ClientTimeout(total=10),  # MODIFICATO: timeout fisso di 10 secondi
            ) as resp:
                resp.raise_for_status()
                text = await resp.text()  # MODIFICATO: leggo come testo prima
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    _LOGGER.error("DOMO Invalid JSON response: %s", text[:200])
                    return {}
        except asyncio.TimeoutError:
            _LOGGER.debug("DOMO Timeout during POST")
            raise
        except aiohttp.ClientError as err:
            _LOGGER.error("DOMO HTTP error: %s", err)
            raise

    # --------------------------------------------------
    # Login / session
    # --------------------------------------------------

    async def _login(self):
        """Login ETI/Domo (registration request)."""
        _LOGGER.info("DOMO login")

        payload = {
            "sl_cmd": "sl_registration_req",
            "sl_appl_msg_type": "domo",
            "sl_appl_msg": {},
            "sl_client_id": "",
            "sl_login": self.username,
            "sl_pwd": self.password,
        }

        resp = await self._post(payload)

        ack = resp.get("sl_data_ack_reason")
        if ack not in (None, 0):
            raise RuntimeError(f"DOMO login failed, ack={ack}")

        self._client_id = resp.get("sl_client_id", "")
        self._keep_alive_sec = resp.get("sl_keep_alive_timeout_sec", 60)  # MODIFICATO: default 60 se non fornito
        self._session_expire_ts = time.monotonic() + self._keep_alive_sec

        _LOGGER.info(
            "DOMO login ok | client_id=%s keep_alive=%ss",
            self._client_id,
            self._keep_alive_sec,
        )

    def _session_valid(self) -> bool:
        return bool(self._client_id) and time.monotonic() < self._session_expire_ts

    # --------------------------------------------------
    # RX STATUS
    # --------------------------------------------------

    async def rx_status(self):
        if not self._session_valid():
            try:
                await self._login()
            except Exception as err:
                _LOGGER.debug("DOMO login failed (offline?): %s", err)
                return
            
        payload = {
            "sl_cmd": "sl_data_req",
            "sl_appl_msg_type": "domo",
            "sl_client_id": self._client_id,
            "sl_appl_msg": {
                "cmd_name": STATUS_UPDATE_CMD,
            },
        }

        try:
            resp = await self._post(payload)
            
            if not self._was_connected:
                self._was_connected = True
                self.online = True
                _LOGGER.info("DOMO gateway ONLINE")
                async_dispatcher_send(self.hass, SIGNAL_GATEWAY_ONLINE)            
            
            
            if not resp:
                _LOGGER.debug("DOMO empty response")
                return
                
            cmd_name = resp.get("cmd_name")
            
            if cmd_name == "generic_reply":
                _LOGGER.debug("DOMO generic_reply: %s", resp)
                return

            if cmd_name == "status_update_resp":
                events = resp.get("result", []) or []
                
                if events:
                    _LOGGER.debug("DOMO received %d events", len(events))
                    
                    for event in events:
                        cmd = event.get("cmd_name", "unknown")
                        _LOGGER.debug(
                            "DOMO RX cmd_name=%s payload=%s",
                            cmd,
                            event,
                        )
                    
                        for callback in self._event_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(self, event)  # <-- se è async, usa await
                                else:
                                    callback(self, event)  # <-- se è sync, chiama normale
                            except Exception as err:
                                _LOGGER.error("DOMO Error in event callback: %s", err)                  
                        
                else:
                    _LOGGER.debug("DOMO status_update_resp with no events")
            else:
                _LOGGER.debug("DOMO unexpected response: cmd_name=%s", cmd_name)

        except asyncio.TimeoutError:
            _LOGGER.debug("DOMO rx_status timeout - no events")
        except aiohttp.ClientConnectorError as err:
            if self._was_connected:
                self._was_connected = False
                self.online = False
                _LOGGER.error("DOMO gateway OFFLINE: %s", err)
                async_dispatcher_send(self.hass, SIGNAL_GATEWAY_OFFLINE)
            return   
        except Exception as err:
            _LOGGER.error("DOMO rx_status error: %s", err)
            self._session_expire_ts = 0
            
    # --------------------------------------------------
    # TX COMMAND
    # --------------------------------------------------            
            
    async def tx_command(self, payload: dict, resp_command: str | None = None) -> dict | None:
        if not self._session_valid():
            await self._login()

        request_payload = {
            "sl_cmd": "sl_data_req",
            "sl_appl_msg_type": "domo",
            "sl_client_id": self._client_id,
            "sl_appl_msg": payload,
        }

        _LOGGER.debug("DOMO tx_command: %s", payload.get("cmd_name"))
       
        

        try:
            # Il timeout è già gestito in _post (total=10)
            resp = await self._post(request_payload)
            
            if resp_command and resp.get("cmd_name") != resp_command:
                _LOGGER.warning(
                    "DOMO Unexpected response command: expected %s, got %s",
                    resp_command,
                    resp.get("cmd_name"),
                )
            
            return resp
        
        except Exception as err:
            _LOGGER.error("DOMO tx_command failed: %s", err)
            return None         


    def get_cseq(self) -> int:
        """Genera il prossimo sequence number per i comandi."""
        if not hasattr(self, "_cseq"):
            self._cseq = 0
        self._cseq += 1
        return self._cseq
