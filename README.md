[![Current release](https://img.shields.io/github/release/odoricof/Home-Sapiens-Assistant.svg?style=plastic&label=Current%20release)](https://github.com/odoricof/Home-Sapiens-Assistant/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=plastic)](https://github.com/odoricof/Home-Sapiens-Assistant)
[![downloads](https://img.shields.io/github/downloads/odoricof/Home-Sapiens-Assistant/total?style=plastic&label=Total%20downloads)](https://github.com/odoricof/Home-Sapiens-Assistant/releases)
[![Buy me a beer 🍺🍺🍺](https://img.shields.io/badge/PayPal-Buy%20me%20a%20beer%20🍺🍺🍺-blue?style=plastic&logo=paypal)](https://paypal.me/odoricof)

<img src="https://raw.githubusercontent.com/odoricof/Home-Sapiens-Assistant/main/custom_components/domo/brand/logo@2x.png" width="96">

# Home Sapiens Assistant
---
Custom integration for **Home Assistant** to interface with **Bpt Home Automation / CAME Domotic 3.0 (Systems based of ETI-Domo server)** via the Home Sapiens web interface.

---

## Features

This integration allows Home Assistant to monitor and control a CAME Domotic system.

Currently supported:

- Activations
- Analogic inputs
- Climate control
- Digital inputs
- Energy meters
- Fan coils
- Intrusion alarm panel
- Lights
- Openings
- Scenes
- TVCC


---

## How It Works

The integration communicates with the system by reproducing the same HTTP requests used by the official **Home Sapiens web interface** exposed by ETI/Domo.

No direct API is provided by the manufacturer; therefore, the integration interacts with the system through observed web communication.

---

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant  
2. Go to **Integrations**  
3. Click the three dots → **Custom repositories**  
4. Add this repository: https://github.com/odoricof/Home-Sapiens-Assistant
5. Category: **Integration**  
6. Search for **Home Sapiens Assistant** and install  
7. Restart Home Assistant  

---

### Manual installation

1. Download this repository  
2. Copy the folder: custom_components/domo/
3. Restart Home Assistant  

---

## Configuration

After installation:

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **Home Sapiens Assistant**
4. Enter:
   - IP address of ETI/Domo server
   - Credentials of Home Sapiens web page login

---

## Requirements

- A working **Bpt Home Sapiens Domotic system / CameDomotic 3.0 system**
- Access to the **Home Sapiens web interface**
- Network connectivity between Home Assistant and the server Eti/Domo

---

## Disclaimer

This is an **independent project** developed by [@odoricof](https://github.com/odoricof).

- Not affiliated with or endorsed by CAME
- Uses publicly observable HTTP communication from the web interface
- Compatibility with all firmware versions is not guaranteed

Use at your own risk.  
For official configuration and system management, always refer to manufacturer tools.

---

## License

This project is released under the **MIT License**:  
https://opensource.org/licenses/MIT

---

## Project Status

Active development.  
Features and compatibility may evolve over time.

---

## Contributions

Contributions, issues, and suggestions are welcome:

https://github.com/odoricof/Home-Sapiens-Assistant/issues
