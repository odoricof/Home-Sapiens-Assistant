// Costanti condivise della card.

export const CARD_TYPE = "domo-thermostat-card";
export const EDITOR_TYPE = "domo-thermostat-card-editor";

export const SUPPORTED_DOMAINS = ["climate", "water_heater"];

// Icona "tre puntini verticali" (mdiDotsVertical), usata dal pulsante "more info".
export const MDI_DOTS_VERTICAL =
  "M12,16A2,2 0 0,1 14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18A2,2 0 0,1 12,16M12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12A2,2 0 0,1 12,10M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4Z";

// Elementi nativi di Home Assistant che la card riusa (come fa la card ufficiale).
export const CLIMATE_CONTROL = "ha-state-control-climate-temperature";
export const WATER_HEATER_CONTROL = "ha-state-control-water_heater-temperature";

// ---- Fase 2: modalità Jolly e programma orario ----
export const JOLLY_PRESET = "Jolly";
// Giallo della ghiera quando Jolly è attivo (personalizzabile dal tema).
export const JOLLY_COLOR = "var(--state-climate-jolly-color, #ffd600)";

export const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "jolly"];
export const STEP_MINUTES = [15, 30, 60];
export const DEFAULT_STEP_MINUTES = 60;

// Ordine delle modalità nel menu (come nel frontend); Jolly segue "auto".
export const HVAC_ORDER = ["auto", "jolly", "heat_cool", "heat", "cool", "dry", "fan_only", "off"];
export const HVAC_ICONS = {
  auto: "mdi:thermostat-auto",
  jolly: "mdi:star-outline",
  heat_cool: "mdi:sun-snowflake-variant",
  heat: "mdi:fire",
  cool: "mdi:snowflake",
  dry: "mdi:water-percent",
  fan_only: "mdi:fan",
  off: "mdi:power",
};

// ---- Fase 3 ----
export const MINIMAL_TYPE = "domo-thermostat-minimal-card";
export const MINIMAL_EDITOR_TYPE = "domo-thermostat-minimal-card-editor";

// Posizione delle icone finestra/presenza dentro la ghiera: distanza (in rapporto al diametro)
// tra una riga di testo e la successiva (stato -> numero grande -> temperatura piccola).
export const STATUS_STEP_RATIO = 0.1656;

// Etichette ridotte della vista estesa (manuale = riscaldamento o raffrescamento).
export const MODE_SHORT = { auto: "Auto", jolly: "Jolly", heat: "Man", cool: "Man", off: "Off" };

// Icone della ventola in base alla velocità impostata.
export const FAN_ICONS = {
  auto: "mdi:fan-auto",
  low: "mdi:fan-speed-1",
  medium: "mdi:fan-speed-2",
  high: "mdi:fan-speed-3",
};
