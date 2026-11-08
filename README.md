[![Marketplace](https://img.shields.io/badge/Marketplace-Default-41BDF5.svg?style=plastic&labelColor=555555&logo=homeassistant&logoColor=white)](https://github.com/odoricof/Home-Sapiens-Assistant)
[![Current release](https://img.shields.io/github/release/odoricof/Home-Sapiens-Assistant.svg?style=plastic&label=Current%20release&labelColor=555555&color=41BDF5)](https://github.com/odoricof/Home-Sapiens-Assistant/releases)  
[![Validate with hassfest](https://img.shields.io/github/actions/workflow/status/odoricof/Home-Sapiens-Assistant/hassfest.yaml?style=plastic&label=hassfest&labelColor=555555)](https://github.com/odoricof/Home-Sapiens-Assistant/actions/workflows/hassfest.yaml)
[![Validate](https://img.shields.io/github/actions/workflow/status/odoricof/Home-Sapiens-Assistant/validate.yml?style=plastic&label=Validate&labelColor=555555)](https://github.com/odoricof/Home-Sapiens-Assistant/actions/workflows/validate.yml)  
[![downloads](https://img.shields.io/github/downloads/odoricof/Home-Sapiens-Assistant/total?style=plastic&label=Total%20downloads&labelColor=555555&color=41BDF5)](https://github.com/odoricof/Home-Sapiens-Assistant/releases)
---
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/odoricof/Home-Sapiens-Assistant/main/custom_components/domo/brand/dark_logo@2x.png">
  <img alt="Home Sapiens Assistant" src="https://raw.githubusercontent.com/odoricof/Home-Sapiens-Assistant/main/custom_components/domo/brand/logo@2x.png">
</picture>

---
**Multilingual Custom integration** for **Home Assistant** to interface with **Bpt Home Automation / CAME Domotic 3.0 (Systems based of ETI/DOMO server)** through the Home Sapiens web interface.

---
### 🌍 Translations

| 🇮🇹 Italian | 🇬🇧 English | 🇪🇸 Spanish | 🇫🇷 French | 🇩🇪 German | 🇷🇺 Russian |
|:---:|:---:|:---:|:---:|:---:|:---:|
- Need support for another language? Open an issue and let us know.  
---
- README Version: [English](README.md) | [Italiano](README.it.md)
---
#### ⭐ If this integration is useful to you, please give the project a star and, if you like, buy me a beer! Thank you!

[![Give a star](https://img.shields.io/github/stars/odoricof/Home-Sapiens-Assistant?style=for-the-badge&logo=github&label=Give%20a%20star&color=FFC107&labelColor=555555)](https://github.com/odoricof/Home-Sapiens-Assistant) [![Buy me a beer](https://img.shields.io/badge/PayPal-Buy%20me%20a%20beer🍺-0070BA?style=for-the-badge&logo=paypal&labelColor=555555)](https://paypal.me/odoricof)

---
## Features

This integration allows Home Assistant to monitor and control a Bpt Home Automation / CAME Domotic system.

Currently supported:

- Activations
   - On/Off
   - Icon catalog
   
- Analogic inputs
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
   - Input bypass
   
- Lights
   - On/Off
   - Dimmers
   - RGB
     - Slider: brightness / brightness+saturation
   
- Load control
   - Full replication of all functions exposed for reading and writing
   
- Openings
   - Shutters / Covers
   
- Scenarios
   - Activation
   - Recording
   - Exposed states: on, off, transitioning
   
- Schedule
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

### Marketplace (recommended)

- Go to **Settings → Marketplace** and search for **Home Sapiens Assistant**, or use this link:  
  [![Open your Home Assistant instance and open a repository inside the Home Assistant Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=Home-Sapiens-Assistant&category=Integration&owner=odoricof)
- Click **Install**, check the version and confirm with **Install** again.
- Restart Home Assistant

### Manual installation

- Download this repository
- Copy the folder: custom_components/domo/
- Restart Home Assistant  

---

## Configuration

- Simply click here and confirm:  
  [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=domo)
- Or else, go to **Settings → Devices & Services** or click here:  
  [![Open your Home Assistant instance and show your integrations.](https://my.home-assistant.io/badges/integrations.svg)](https://my.home-assistant.io/redirect/integrations/)
  - Click **Add Integration**
  - Search for **Home Sapiens Assistant**
  - Enter:
    - IP address of the ETI/DOMO server
    - Credentials of the Home Sapiens web page login


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
