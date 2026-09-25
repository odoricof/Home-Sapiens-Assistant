"""
domo/const.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues

status: passed
"""

# ============================================================
# ===== DOMAIN =====
# ============================================================

DOMAIN = "domo"


# ============================================================
# ===== DEFAULT VALUES =====
# ============================================================

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"


# ============================================================
# ===== CONFIG KEYS =====
# ============================================================

CONF_PENDING = "pending"


# ============================================================
# ===== SIGNALS =====
# ============================================================

SIGNAL_DISCOVERY_NEW = "domo_discovery_new_{}"
SIGNAL_UPDATE_ENTITY = "domo_update_entity"
SIGNAL_GATEWAY_ONLINE = "domo_gateway_online"
SIGNAL_GATEWAY_OFFLINE = "domo_gateway_offline"


# ============================================================
# ===== PLATFORMS =====
# ============================================================

PLATFORMS = [
    "alarm_control_panel",
    "binary_sensor",
    "button",
    "light",
    "climate",
    "number",
    "select",
    "sensor",
    "scene",
    "switch",
    "cover",
    "camera",
    "text",
    "time",
]
