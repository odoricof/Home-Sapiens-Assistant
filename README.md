[![Current release](https://img.shields.io/github/release/odoricof/Home-Sapiens-Assistant.svg?style=plastic&label=Current%20release)](https://github.com/odoricof/Home-Sapiens-Assistant/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=plastic)](https://github.com/odoricof/Home-Sapiens-Assistant)
[![HACS Repository](https://img.shields.io/badge/HACS_Repository-%2341BDF5.svg?style=plastic&logo=homeassistant&logoColor=white)](https://my.home-assistant.io/redirect/hacs_repository/?owner=odoricof&repository=Home-Sapiens-Assistant&category=integration)  
[![downloads](https://img.shields.io/github/downloads/odoricof/Home-Sapiens-Assistant/total?style=plastic&label=Total%20downloads)](https://github.com/odoricof/Home-Sapiens-Assistant/releases)
[![Buy me a beer 🍺🍺🍺](https://img.shields.io/badge/PayPal-Buy%20me%20a%20beer%20🍺🍺🍺-blue?style=plastic&logo=paypal)](https://paypal.me/odoricof)

<img src="https://raw.githubusercontent.com/odoricof/Home-Sapiens-Assistant/main/custom_components/domo/brand/logo@2x.png" width="96" alt="">

# Home Sapiens Assistant
---
Custom integration for **Home Assistant** to interface with **Bpt Home Automation / CAME Domotic 3.0 (Systems based of ETI/DOMO server)** via the Home Sapiens web interface.

---

## Features

This integration allows Home Assistant to monitor and control a Bpt Home Automation / CAME Domotic system.

Currently supported:

- Activations
- Analogic inputs
- Climate control
- Digital inputs
- Energy meters
- Fan coils
- Intrusion alarm panel
   - Areas
   - Inputs
   - Outputs
   - Scenarios
   - Trigger and warnings notifications
- Lights
- Openings
- Scenes
- TVCC

Services:

- Offline/Online status notifications for the ETI/DOMO server
- Weekly Security event log

---

## How It Works

The integration communicates with the system by reproducing the same HTTP requests used by the official **Home Sapiens web interface** exposed by ETI/DOMO.

No direct API is provided by the manufacturer; therefore, the integration interacts with the system through observed web communication.

---

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant  
2. Go to **Integrations**  
3. Click the three dots → **Custom repositories**  
4. Add the repository `https://github.com/odoricof/Home-Sapiens-Assistant`

   or click on [![HACS Repository](https://img.shields.io/badge/HACS_Repository-%2341BDF5.svg?style=plastic&logo=homeassistant&logoColor=white)](https://my.home-assistant.io/redirect/hacs_repository/?owner=odoricof&repository=Home-Sapiens-Assistant&category=integration)
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
   - IP address of ETI/DOMO server
   - Credentials of Home Sapiens web page login

---
## Note on Scenario Visualization in the Home Assistant Alarm Panel

To ensure proper and consistent visualization of scenarios within the Home Assistant Alarm Panel, the following condition must be met:

> **Each scenario programmed on the alarm control panel must include at least one area that differs from the others.**  
> This differentiation allows the system to correctly recognize and display the current status of the security system.

### Practical Example

#### Defined Areas:
- **Day Area**
- **Night Area**
- **Perimeter Area**

#### Scenarios and Associated Areas:

| Scenario          | Associated Areas                       |
|-------------------|----------------------------------------|
| **"Armed away"**  | Day Area + Night Area + Perimeter Area |
| **"Armed home"**  | Perimeter Area                         |
| **"Armed night"** | Day Area + Perimeter Area              |

In this example, each scenario features a unique combination of areas, enabling the Home Assistant panel to distinguish between them correctly and update the user interface accordingly.

> **Important:** When configuring your alarm control panel, ensure that each scenario is assigned a **distinct set of areas** different from all the others.
## Requirements

- A working **Bpt Home Sapiens Domotic system / CameDomotic 3.0 system**
- Access to the **Home Sapiens web interface**
- Network connectivity between Home Assistant and the server ETI/DOMO

---

## Disclaimer

This is an **independent project** developed by [@odoricof](https://github.com/odoricof).

- Not affiliated with or endorsed by manufacturer of ETI/DOMO.
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
