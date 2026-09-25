[![Current release](https://img.shields.io/github/release/odoricof/Home-Sapiens-Assistant.svg?style=plastic&label=Current%20release)](https://github.com/odoricof/Home-Sapiens-Assistant/releases)
[![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=plastic)](https://github.com/odoricof/Home-Sapiens-Assistant)  
[![downloads](https://img.shields.io/github/downloads/odoricof/Home-Sapiens-Assistant/total?style=plastic&label=Total%20downloads)](https://github.com/odoricof/Home-Sapiens-Assistant/releases)
[![Buy me a beer 🍺🍺🍺](https://img.shields.io/badge/PayPal-Buy%20me%20a%20beer%20🍺🍺🍺-blue?style=plastic&logo=paypal)](https://paypal.me/odoricof)


<img src="https://raw.githubusercontent.com/odoricof/Home-Sapiens-Assistant/main/custom_components/domo/brand/logo@2x.png" width="96" alt="">

# Home Sapiens Assistant
---
**Multilingual Custom integration** for **Home Assistant** to interface with **Bpt Home Automation / CAME Domotic 3.0 (Systems based of ETI/DOMO server)** through the Home Sapiens web interface.

---
### 🌍 Languages translations

| 🇮🇹 Italian | 🇬🇧 English | 🇪🇸 Spanish | 🇫🇷 French | 🇩🇪 German | 🇷🇺 Russian |
|:---:|:---:|:---:|:---:|:---:|:---:|

- README Version: [English](README.md) | [Italiano](README.it.md)
---
## Features

This integration allows Home Assistant to monitor and control a Bpt Home Automation / CAME Domotic system.

Currently supported:

- Activations
   - On/Off
   - Icon catalog
   
- Analog inputs
   - Value and unit of measurement
   - Appropriate icons based on the measured quantity
   
- Climate control
   - Thermostats
   - Fan coils
   - Thermal profile management
   - Copy/paste thermal profiles
   - Exposure and management of all configurable parameters

- Digital inputs
   - Value exposure
   
- Irrigation
   - Full replication of all functions exposed for reading and writing
   
- Energy meters
   - Energy produced / consumed as exposed by the system

- Intrusion alarm panel
   - Areas
   - Inputs
   - Outputs
   - Scenarios
   - Trigger and alarm notifications
   - Siren silencing
   - Event memory deletion
   
- Lights
   - On/Off
   - Dimmers
   - RGB
   
- Load control
   - Full replication of all functions exposed for reading and writing
   
- Openings
   - Shutters / Covers
   
- Scenarios
   - Activation
   - Recording
   - Exposed states: on, off, transitioning
   
- Scheduling
   - Full management of the 4 programmable time slots
   
- CCTV
   - Video streams exposed as camera entities

Additional Services:

- Offline/Online status notifications for the ETI/DOMO server
- Weekly Security event log
- Local backup and restore of all thermal profiles for all thermostats, for both seasons
---

## How It Works

The integration communicates with the system by reproducing the same HTTP requests used by the official **Home Sapiens web interface** exposed by ETI/DOMO.

No direct API is provided by the manufacturer; therefore, the integration interacts with the system through observed web communication.

---

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant  
2. Go to **Integrations**  
3. Search for **Home Sapiens Assistant** and install  
4. Restart Home Assistant  

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

---

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
