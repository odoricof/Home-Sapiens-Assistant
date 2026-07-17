"""
domo/const.py

Custom integration: Home-Sapiens-Assistant
Author: Flavio Odorico (github.com/odoricof)
License: MIT

This file is part of the Home-Sapiens-Assistant integration for Home Assistant.
Report any bugs or feature requests via GitHub Issues:
https://github.com/odoricof/Home-Sapiens-Assistant/issues
"""

DOMAIN = "domo"

# Default values
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"
DEFAULT_POLL_INTERVAL = 2.0

# Config
CONF_PENDING = "pending"

# Signals
SIGNAL_DISCOVERY_NEW = "domo_discovery_new_{}"
SIGNAL_UPDATE_ENTITY = "domo_update_entity"
SIGNAL_GATEWAY_ONLINE = "domo_gateway_online"
SIGNAL_GATEWAY_OFFLINE = "domo_gateway_offline"

# Platforms
PLATFORMS = [
    "alarm_control_panel",
    "binary_sensor",
    "light",
    "climate",
    "sensor",
    "scene",
    "switch",
    "cover",
    "camera",
    "text",
]
