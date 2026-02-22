"""Constants for the Domo integration."""

DOMAIN = "domo"

# Default values
DEFAULT_HOST = "192.168.1.150"
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
PLATFORMS = ["alarm_control_panel"]
