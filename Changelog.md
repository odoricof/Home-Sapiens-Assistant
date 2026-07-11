# Changelog

All notable changes to this project will be documented in this file.

---

## [1.0.0] - 2026-03-12

### Added
- Initial public release of the **ETI/DOMO integration for Home Assistant**
- Gateway of communication with ETI/Domo systems through the **Home Sapiens web interface**

### Supported platforms
- Activations
- Analogic inputs
- Climate control
- Energy meters
- Fan coils
- Intrusion alarm panel
- Lights
- Intrusion alarm panel
- Scenes

## [1.1.0] - 2026-04-04

### Added
### Supported platforms
- TVCC
- Openings
- Digital inputs

## [1.1.1] - 2026-04-09

- Minor improvements

## [1.2.0] - 2026-04-12

### Added
- Security Areas
- Security Inputs
- security Outputs

## [1.3.0] - 2026-04-12

### Added
- Offline/Online status notifications for the ETI/DOMO server

## [1.3.1] - 2026-06-21

- Bugfix: correct thermostat summer mode

## [1.4.0] - 2026-07-11

### 🌡️ Automatic Thermal Profile added fature

- **Thermal profile exposure** for climate entities
- **Readable profile decoding**: new `thermal_profile_schedule` attribute that condenses the 96 quarter-hour slots into compressed time ranges (e.g. `00:00-09:00: t3 | 30.0°C`), one line per range, ready for quick consultation and automations.
- **Currently active set-point**: new `scheduled_setpoint` attribute, calculated in real time from the thermal profile according to the current time — useful to know "what temperature it should be right now" without having to consult the scheduler.
- **More readable state attributes**: `mode` and `status` now return textual labels instead of raw numeric codes.
- **Automatic profile refresh on restart**: thermostats already in AUTO mode now actively request the complete thermal profile and expose it immediately.

### 🎛️ Interaction with the Climate Card added feature

- **AUTO mode now displays the scheduled set-point** on the native card (number + slider), instead of only showing the text "Automatic" — consistent with the standard behavior of other Home Assistant climate integrations.
- **OFF mode (winter only) displays the antifreeze value** (`antifreeze`) on the card, instead of blocking all interaction. In summer it remains "Off" without a slider, since the concept of antifreeze does not apply to cooling.
- **Assisted interaction**: if the user moves the slider while the thermostat is in AUTO or OFF mode (OFF only in winter), the thermostat automatically switches to **manual** mode and immediately applies the requested temperature, with a single call to the gateway (mode + set_point in a single command).
- New `antifreeze` (°C) attribute exposed on the entity.

### 🐛 Minor Fix 

- **Merge pull request #4 from brokkolo/patch-1**: Fix false 0°C history dips: climate entities defaulted temp_dec/set_point to 0/200 instead of None

