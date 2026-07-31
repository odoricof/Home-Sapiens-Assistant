### 🌐 Lingua / Language
- [English](Changelog.md) | [Italiano](Changelog.it.md)

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

### Added

#### Automatic Thermal Profile added fature

- **Thermal profile exposure** for climate entities
- **Readable profile decoding**: new `thermal_profile_schedule` attribute that condenses the 96 quarter-hour slots into compressed time ranges (e.g. `00:00-09:00: t3 | 30.0°C`), one line per range, ready for quick consultation and automations.
- **Currently active set-point**: new `scheduled_setpoint` attribute, calculated in real time from the thermal profile according to the current time — useful to know "what temperature it should be right now" without having to consult the scheduler.
- **More readable state attributes**: `mode` and `status` now return textual labels instead of raw numeric codes.
- **Automatic profile refresh on restart**: thermostats already in AUTO mode now actively request the complete thermal profile and expose it immediately.

#### Interaction with the Climate Card added feature

- **AUTO mode now displays the scheduled set-point** on the native card (number + slider), instead of only showing the text "Automatic" — consistent with the standard behavior of other Home Assistant climate integrations.
- **OFF mode (winter only) displays the antifreeze value** (`antifreeze`) on the card, instead of blocking all interaction. In summer it remains "Off" without a slider, since the concept of antifreeze does not apply to cooling.
- **Assisted interaction**: if the user moves the slider while the thermostat is in AUTO or OFF mode (OFF only in winter), the thermostat automatically switches to **manual** mode and immediately applies the requested temperature, with a single call to the gateway (mode + set_point in a single command).
- New `antifreeze` (°C) attribute exposed on the entity.

### Fixed 

- **Merge pull request #4 from brokkolo/patch-1**: Fix false 0°C history dips: climate entities defaulted temp_dec/set_point to 0/200 instead of None

## [1.5.0] - 2026-07-17

### Alarm Panel

Handling of arming when one or more areas of the requested scenario are not ready (open inputs), to prevent the alarm from triggering immediately.

#### Implemented Behavior

When the user requests arming (arm_home / arm_night / arm_away) and one or more areas involved in the scenario are not ready:

1. The command is **not** sent immediately to the control panel.
2. A **30-second** wait period begins, during which the entity shows ARMING status.
3. A push notification is sent to all mobile devices along with a persistent notification in Home Assistant: *"⚠️ Arming pending"*.
4. If areas become ready before the 30s elapse → arming proceeds immediately and the notification is dismissed.
5. If 30s expire and areas are still not ready → arming **is still executed**, as requested by the user who was warned.
6. If the user sends disarm during the wait → the arming request is canceled, no command is ever sent to the control panel. The persistent notification is dismissed; the push notification remains on the phone until manually cleared by the user (explicit choice, no automatic recall).

#### Push Notifications for Alarm Panel State Changes

1. Added push notification system that informs the user of every state change of the control panel.

### Added

#### Timer management (Scheduler platform)

![Scheduler](images/scheduler.png)

- [Feature] expose CAME activation (relay) timers/schedules as entity attributes
 #2

### Fixed 

- [Bug] alarm_control_panel state stuck at "unknown" after restart — central status never queried during discovery
 #3
## [1.6.0] - 2026-07-26

### Added

#### Irrigation Platform

![Irrigation](images/irrigation.png)

Full irrigation platform support, exposing all native irrigation management features as Home Assistant entities.

##### Irrigation Sectors

- Enable/disable irrigation sector
- Irrigation duration percentage relative to the programmed nominal duration
- Weekly schedule configuration with individual enable/disable for each day
- Configurable irrigation start time
- Irrigation status indicating whether the current irrigation cycle was started manually or automatically by schedule
- Manual start/stop of irrigation

##### Sprinklers

- Enable/disable individual sprinkler
- Configurable maximum irrigation time
- Configurable duty cycle percentage
- Real-time operating status shown directly on the switch entity through a dynamic icon

#### Climate Platform

##### Weekly Thermal Schedule

![Thermal Schedule](images/thermal_scheduler.png)

Added complete weekly thermal schedule management directly from Home Assistant, matching the functionality available in the native interface.

- Day selector entity automatically synchronized with the active thermal profile
- Editable daily profile using a human-readable time-range format
- Direct upload of modified schedules to the thermostat

The following parameters are now exposed for both reading and writing:

- Antifreeze
- Thermal differential
- Thermal profile day
- Algorithm mode
- Daily thermal profile
- T1 / T2 / T3

#### Thermal Profile Backup & Restore

![Thermo bk](images/thermo_bk.png)

##### Backup

- New **Backup Thermal Profiles** button
- Saves T1/T2/T3 set-points and weekly schedules for every thermostat
- Backup files stored in `config/thermo_profile_bk/`
- Automatic seasonal filename generation (winter/summer)

##### Restore

- Automatic backup file selector
- Seasonal filtering prevents restoring incompatible profiles
- New **Restore Thermal Profiles** button
- Automatic verification of every restored thermostat
- Temporary progress/completion status shown directly by the selector
- Thermostats missing from the installation are skipped with a warning without interrupting the restore process

### Minor Fix

- Added anti-glitch filtering during ETI/DOMO bus programming to discard invalid `temp_dec` values (outside 3–35°C) and `hygro` values (outside 0–100%), preventing invalid temperature and humidity readings from propagating to Climate entities.
- Alarm panel now exposes only the scenarios actually configured in the installation. **Away** is always available, while **Night** and **Home** are created only when the corresponding scenarios exist and contain configured areas.
- Fixed an issue where, on some systems, the app could display the wrong button instead of "Stay at Home" (e.g. "Night"). The system now recognizes each scenario by its actual name configured in the control panel, rather than by assuming a fixed order.
- Added automatic detection of any custom scenario configured in the control panel, which was previously not handled.