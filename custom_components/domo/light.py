"""
domo/light.py

Entities fed by:
- platforms/lights.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues

status: passed
"""

from __future__ import annotations

import logging
import time

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util.color import color_hsv_to_RGB, color_RGB_to_hsv

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .platforms.lights import (
    SLIDER_PROFILE_INTENSITY_SATURATION,
    HUE_MIN_SATURATION,
    DomoLight,
    get_all_lights,
    rgb_light_device_info,
    rgb_to_slider,
    slider_to_hsv,
)


_LOGGER = logging.getLogger(__name__)

# A point of the color wheel with at least this saturation (%) is on the outer edge.
_WHEEL_EDGE_SATURATION = 99.0


# ============================================================
# ===== SETUP ENTRY =====
# ============================================================

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the light platform."""
    lights = get_all_lights()

    if not lights:
        _LOGGER.debug("No lights found")
        return

    entities = [DomoLightEntity(hass, light, entry) for light in lights]
    async_add_entities(entities, update_before_add=True)

    _LOGGER.info("Added %d light entities", len(entities))


# ============================================================
# ===== LIGHT ENTITY =====
# ============================================================

class DomoLightEntity(LightEntity):
    """ETI/Domo light entity."""

    def __init__(self, hass, light: DomoLight, entry):
        """Initialize the light entity."""
        self.hass = hass
        self._light = light

        self._attr_unique_id = light.unique_id
        self._attr_name = light.name
        self._attr_should_poll = False
        self._last_dimmer_value = 100

        self._hsv = (0.0, 0.0, 0.0)
        # Used only by the "intensity + saturation" profile
        self._hue = 0.0
        self._slider = 0.0

        if light.light_type == "rgb" and light.rgb_color:
            r, g, b = light.rgb_color
            h, s, v = color_RGB_to_hsv(r, g, b)
            self._hsv = (h, s, v)
            self._slider = rgb_to_slider(r, g, b)
            if s >= HUE_MIN_SATURATION:
                self._hue = h
            _LOGGER.debug("Initialized HSV from RGB %s: %s", light.rgb_color, self._hsv)

        if light.light_type == "rgb":
            self._attr_device_info = rgb_light_device_info(hass, entry, light)
        else:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry.entry_id}_lights")},
                name="Lights",
                manufacturer="Home Sapiens Assistant",
                model="Eti/Domo",
            )

        self._attr_suggested_area = light.room

        if light.light_type == "DIMMER":
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        elif light.light_type == "rgb":
            self._attr_color_mode = ColorMode.HS
            self._attr_supported_color_modes = {ColorMode.HS}
        else:
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_color_modes = {ColorMode.ONOFF}

        self._awaiting_confirmation = False
        self._command_ts = 0.0
        self._expected_state = None

        _LOGGER.debug("Created light entity: %s", self._attr_name)

    @property
    def _alt_profile(self) -> bool:
        """Return True if this RGB light follows the "intensity + saturation" profile."""
        return (
            self._light.light_type == "rgb"
            and self._light.slider_profile == SLIDER_PROFILE_INTENSITY_SATURATION
        )

    @property
    def is_on(self) -> bool:
        """Return True if the light is on."""
        return self._light.is_on

    @property
    def brightness(self) -> int | None:
        """Return the light brightness (0-255)."""
        if self._light.light_type == "DIMMER":
            return int(self._light.brightness * 2.55)
        if self._light.light_type == "rgb":
            if self._alt_profile:
                return round(self._slider / 100.0 * 255)
            return int(self._hsv[2] * 2.55)
        return None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the HS color value."""
        if self._light.light_type == "rgb":
            if self._alt_profile:
                h, s, _ = slider_to_hsv(self._hue, self._slider)
                return (h, s)
            return (self._hsv[0], self._hsv[1])
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Convert HSV to RGB for compatibility."""
        if self._light.light_type == "rgb":
            if self._alt_profile:
                h, s, v = slider_to_hsv(self._hue, self._slider)
            else:
                h, s, v = self._hsv
            return color_hsv_to_RGB(h, s, v)
        return None

    async def async_turn_on(self, **kwargs):
        """Turn on the light."""
        brightness = None
        rgb = None

        if self._alt_profile and ATTR_HS_COLOR not in kwargs and ATTR_BRIGHTNESS not in kwargs:
            # Plain ON: no color is sent, ETI Domo applies its own default
            # and the new color is read back from the bus.
            _LOGGER.debug("Intensity+saturation profile: plain ON, color left to ETI Domo")

        elif self._alt_profile:
            # Slider = position on the black -> color -> white path.
            # A point chosen on the color wheel stays where it is and the slider
            # follows it, like in the official app.
            if ATTR_HS_COLOR in kwargs:
                hue, sat = kwargs[ATTR_HS_COLOR]
            else:
                hue, sat = self._hue, None

            if ATTR_BRIGHTNESS in kwargs:
                slider = kwargs[ATTR_BRIGHTNESS] / 255.0 * 100
            else:
                slider = self._slider

            if sat is not None:
                if sat >= _WHEEL_EDGE_SATURATION:
                    # Outer edge: only the first half of the slider exists here
                    slider = min(slider, 50.0)
                else:
                    # Inside the wheel: the distance from the edge sets the slider
                    slider = 50.0 + (100.0 - sat) / 2.0

            self._hue = hue
            self._slider = slider
            self._hsv = slider_to_hsv(hue, slider)
            rgb = color_hsv_to_RGB(*self._hsv)
            _LOGGER.debug(
                "Intensity+saturation profile from UI: hue=%f, slider=%f -> HSV=%s",
                hue, slider, self._hsv,
            )

        elif self._light.light_type == "rgb":

            if ATTR_HS_COLOR in kwargs:
                h, s = kwargs[ATTR_HS_COLOR]

                if ATTR_BRIGHTNESS in kwargs:
                    v = kwargs[ATTR_BRIGHTNESS] / 255.0 * 100
                else:
                    v = self._hsv[2]

                self._hsv = (h, s, v)
                _LOGGER.debug("New HS from UI: h=%f, s=%f, v=%f", h, s, v)

            elif ATTR_BRIGHTNESS in kwargs:
                h, s, _ = self._hsv
                v = kwargs[ATTR_BRIGHTNESS] / 255.0 * 100
                self._hsv = (h, s, v)
                _LOGGER.debug("Brightness only from UI: h=%f, s=%f, v=%f", h, s, v)

            else:
                h, s, v = self._hsv
                _LOGGER.debug("ON only from UI: h=%f, s=%f, v=%f", h, s, v)

            h, s, v = self._hsv
            rgb = color_hsv_to_RGB(h, s, v)

        elif self._light.light_type == "DIMMER":
            if ATTR_BRIGHTNESS in kwargs:
                brightness = int(kwargs[ATTR_BRIGHTNESS] / 2.55)
                self._last_dimmer_value = brightness
                _LOGGER.debug(
                    "DIMMER turn_on: brightness HA=%s -> bus=%s",
                    kwargs[ATTR_BRIGHTNESS], brightness,
                )
            else:
                brightness = self._last_dimmer_value
                _LOGGER.debug("DIMMER toggle ON: using last_dimmer_value=%s", brightness)

        else:
            pass

        _LOGGER.debug(
            "Turn ON request -> %s | kwargs=%s | HSV=%s | RGB out=%s | brightness=%s",
            self._attr_unique_id, kwargs, self._hsv, rgb, brightness,
        )

        self._awaiting_confirmation = True
        self._command_ts = time.monotonic()

        self._expected_state = {
            "is_on": True,
            "rgb": rgb,
            "brightness": brightness,
        }

        await self._light.turn_on(brightness, rgb)

    async def async_turn_off(self, **kwargs):
        """Turn off the light."""
        await self._light.turn_off()

    def _state_matches_expected(self):
        """Check whether the current state matches the expected one."""
        if self._expected_state is None:
            return True

        if self._expected_state["is_on"] != self._light.is_on:
            _LOGGER.debug(
                "MISMATCH is_on: expected=%s, actual=%s",
                self._expected_state["is_on"], self._light.is_on,
            )
            return False

        if self._light.light_type == "rgb" and self._expected_state["rgb"] is not None:
            if self._expected_state["rgb"] != self._light.rgb_color:
                _LOGGER.debug(
                    "MISMATCH rgb: expected=%s, actual=%s",
                    self._expected_state["rgb"], self._light.rgb_color,
                )
                return False

        if self._light.light_type == "DIMMER":
            expected = self._expected_state["brightness"]
            actual = self._light.brightness

            if abs(expected - actual) <= 3:
                return True

            _LOGGER.debug("MISMATCH brightness: expected=%s, actual=%s", expected, actual)
            return False

        return True

    async def async_added_to_hass(self):
        """Run when the entity is added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ENTITY,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, entity_id: str = None):
        """Handle an update from the bus."""
        if entity_id is None or entity_id == self._attr_unique_id:

            now = time.monotonic()

            if self._awaiting_confirmation:

                if self._state_matches_expected():
                    self._awaiting_confirmation = False
                    if self._light.light_type != "rgb" or self._expected_state["rgb"] is not None:
                        self.async_write_ha_state()
                        return
                    # Plain ON: ETI Domo chose the color, read it from the bus below

                elif now - self._command_ts >= 0.5:
                    self._awaiting_confirmation = False
                    self.async_write_ha_state()
                    return

                else:
                    return

            if self._light.light_type == "rgb" and self._light.rgb_color:
                r, g, b = self._light.rgb_color
                h, s, v = color_RGB_to_hsv(r, g, b)
                self._hsv = (h, s, v)
                self._slider = rgb_to_slider(r, g, b)
                if s >= HUE_MIN_SATURATION:
                    self._hue = h
                _LOGGER.debug("BUS UPDATE: RGB=%s -> HSV=(%f, %f, %f)", (r, g, b), h, s, v)

            elif self._light.light_type == "DIMMER" and self._light.brightness and self._light.brightness > 0:
                self._last_dimmer_value = self._light.brightness
                _LOGGER.debug("BUS UPDATE DIMMER: saved last_dimmer_value=%s", self._light.brightness)

            self.async_write_ha_state()
