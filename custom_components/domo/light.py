"""
domo/light.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""


from __future__ import annotations
import time
import logging

from homeassistant.components.light import (
    LightEntity,
    ColorMode,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import callback
from homeassistant.util.color import (
    color_RGB_to_hsv,
    color_hsv_to_RGB
)

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.lights import get_light, DomoLight

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup light platform."""
    from .platforms.lights import get_all_lights
    
    lights = get_all_lights()
    
    if not lights:
        _LOGGER.debug("No lights found yet")
        return
    
    entities = [DomoLightEntity(hass, light, entry) for light in lights]
    async_add_entities(entities, update_before_add=True)
    
    _LOGGER.info("Added %d light entities", len(entities))


class DomoLightEntity(LightEntity):
    """ETI Domo light entity."""

    def __init__(self, hass, light: DomoLight, entry):
        """Initialize the light entity."""
        self.hass = hass
        self._light = light

        self._attr_unique_id = light.unique_id
        self._attr_name = light.name
        self._attr_should_poll = False
        self._last_dimmer_value = 100  # default
        
        # Stato HSV corrente (hue, saturation, value/brightness)
        self._hsv = (0.0, 0.0, 0.0)  # h(0-360), s(0-100), v(0-100)
        
        # Inizializza HSV solo per luci RGB
        if light.light_type == "rgb" and light.rgb_color:
            r, g, b = light.rgb_color
            h, s, v = color_RGB_to_hsv(r, g, b)
            self._hsv = (h, s, v)
            _LOGGER.debug("Inizializzato HSV da RGB %s: %s", light.rgb_color, self._hsv)
        
        # Device info           
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_lights")},
            name="Lights",
            manufacturer="Home Sapiens Assistant",
            model="Eti/Domo",
        )
        
        # Area suggerita per l'entità
        self._attr_suggested_area = light.room        
        
        # Configurazione color mode in base al tipo
        if light.light_type == "DIMMER":
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        elif light.light_type == "rgb":
            self._attr_color_mode = ColorMode.HS
            self._attr_supported_color_modes = {ColorMode.HS}
        else:  # STEP_STEP
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_color_modes = {ColorMode.ONOFF}
        
        # Inizializza attributi per il tracking dello stato
        self._awaiting_confirmation = False
        self._command_ts = 0.0
        self._expected_state = None
        
        _LOGGER.debug("Created light entity: %s", self._attr_name)

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._light.is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light (0-255)."""
        if self._light.light_type == "DIMMER":
            return int(self._light.brightness * 2.55)
        if self._light.light_type == "rgb":
            return int(self._hsv[2] * 2.55)
        return None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hs color value."""
        if self._light.light_type == "rgb":
            return (self._hsv[0], self._hsv[1])
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """For backward compatibility, convert HSV to RGB."""
        if self._light.light_type == "rgb":
            h, s, v = self._hsv
            return color_hsv_to_RGB(h, s, v)
        return None

    def _state_matches_expected(self):
        """Verifica se lo stato attuale corrisponde a quello atteso."""
        if self._expected_state is None:
            return True

        if self._expected_state["is_on"] != self._light.is_on:
            _LOGGER.debug("MISMATCH is_on: expected=%s, actual=%s", 
                         self._expected_state["is_on"], self._light.is_on)        
            return False

        if self._light.light_type == "rgb":
            if self._expected_state["rgb"] != self._light.rgb_color:
                _LOGGER.debug("MISMATCH rgb: expected=%s, actual=%s", 
                             self._expected_state["rgb"], self._light.rgb_color)
                return False

        if self._light.light_type == "DIMMER":
            expected = self._expected_state["brightness"]
            actual = self._light.brightness
            
            # Tolleranza di 3 punti per gli arrotondamenti del bus
            if abs(expected - actual) <= 3:
                return True
                
            _LOGGER.debug("MISMATCH brightness: expected=%s, actual=%s", expected, actual)
            return False

        return True

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_HS_COLOR
        
        brightness = None
        rgb = None
        
        # CASO 1: Luce RGB
        if self._light.light_type == "rgb":

            if ATTR_HS_COLOR in kwargs:
                h, s = kwargs[ATTR_HS_COLOR]
                
                if ATTR_BRIGHTNESS in kwargs:
                    v = kwargs[ATTR_BRIGHTNESS] / 255.0 * 100
                else:
                    v = self._hsv[2]
                
                self._hsv = (h, s, v)
                _LOGGER.debug("Nuovo HS da UI: h=%f, s=%f, v=%f", h, s, v)
            
            elif ATTR_BRIGHTNESS in kwargs:
                h, s, _ = self._hsv
                v = kwargs[ATTR_BRIGHTNESS] / 255.0 * 100
                self._hsv = (h, s, v)
                _LOGGER.debug("Solo brightness da UI: h=%f, s=%f, v=%f", h, s, v)
            
            else:
                h, s, v = self._hsv
                _LOGGER.debug("Solo ON da UI: h=%f, s=%f, v=%f", h, s, v)
            
            h, s, v = self._hsv
            rgb = color_hsv_to_RGB(h, s, v)
                      
        # CASO 2: Luce DIMMER
        elif self._light.light_type == "DIMMER":
            if ATTR_BRIGHTNESS in kwargs:
                brightness = int(kwargs[ATTR_BRIGHTNESS] / 2.55)
                self._last_dimmer_value = brightness  # SALVA
                _LOGGER.debug("DIMMER turn_on: brightness HA=%s → bus=%s", 
                             kwargs[ATTR_BRIGHTNESS], brightness)
            else:
                # Toggle ON: usa l'ultimo valore salvato
                brightness = self._last_dimmer_value
                _LOGGER.debug("DIMMER toggle ON: uso last_dimmer_value=%s", brightness)
        
        # CASO 3: Luce ON/OFF
        else:
            pass
            
        _LOGGER.debug(
            "Turn ON request → %s | kwargs=%s | HSV=%s | RGB out=%s | brightness=%s",
            self._attr_unique_id, kwargs, self._hsv, rgb, brightness
        )
        
        # Stato atteso per la conferma
        self._awaiting_confirmation = True
        self._command_ts = time.monotonic()

        self._expected_state = {
            "is_on": True,
            "rgb": rgb,
            "brightness": brightness,
        }
      
                
        await self._light.turn_on(brightness, rgb)

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        await self._light.turn_off()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle update from bus."""
        if entity_id is None or entity_id == self._attr_unique_id:

            now = time.monotonic()

            # Se stiamo aspettando una conferma
            if self._awaiting_confirmation:

                # Caso 1: conferma corretta
                if self._state_matches_expected():
                    self._awaiting_confirmation = False
                    self.async_write_ha_state()
                    return

                # Timeout 0,5 secondo
                if now - self._command_ts >= 0.5:
                    self._awaiting_confirmation = False
                    self.async_write_ha_state()
                    return

                return

            # Aggiornamento spontaneo dal bus
            if self._light.light_type == "rgb" and self._light.rgb_color:
                r, g, b = self._light.rgb_color
                h, s, v = color_RGB_to_hsv(r, g, b)
                self._hsv = (h, s, v)
                _LOGGER.debug("BUS UPDATE: RGB=%s -> HSV=(%f, %f, %f)", (r, g, b), h, s, v)
                
            # PER I DIMMER
            elif self._light.light_type == "DIMMER" and self._light.brightness and self._light.brightness > 0:
                self._last_dimmer_value = self._light.brightness
                _LOGGER.debug("BUS UPDATE DIMMER: salvato last_dimmer_value=%s", self._light.brightness)                
                

            self.async_write_ha_state()
