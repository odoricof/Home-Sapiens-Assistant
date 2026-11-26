// Funzioni di appoggio che nel frontend ufficiale sono moduli interni
// (non raggiungibili da una card esterna): qui sono riscritte in modo equivalente.

import { CLIMATE_CONTROL, JOLLY_COLOR, STATUS_STEP_RATIO, WATER_HEATER_CONTROL } from "./const.js";

export const computeDomain = (entityId) => entityId.split(".")[0];

export function fireEvent(node, type, detail = {}) {
  node.dispatchEvent(
    new CustomEvent(type, { detail, bubbles: true, composed: true })
  );
}

// Nome mostrato nel titolo: usa l'API del frontend se disponibile.
export function computeName(hass, stateObj, configName) {
  if (typeof hass.formatEntityName === "function") {
    try {
      return hass.formatEntityName(stateObj, configName);
    } catch (_err) {
      /* ripiega sul nome semplice */
    }
  }
  if (typeof configName === "string" && configName) return configName;
  return stateObj.attributes.friendly_name ?? stateObj.entity_id;
}

// Colore dello stato, passato alle funzioni della card come --feature-color.
export function stateColorCss(stateObj) {
  const domain = computeDomain(stateObj.entity_id);
  if (stateObj.state === "unavailable") return "var(--state-unavailable-color)";
  if (stateObj.state === "unknown") return "var(--state-unknown-color)";
  // Spento: grigio, come nella tile nativa (non il colore "attivo").
  if (stateObj.state === "off") {
    return `var(--state-${domain}-off-color, var(--state-inactive-color))`;
  }
  return `var(--state-${domain}-${stateObj.state}-color, var(--state-${domain}-active-color, var(--state-active-color)))`;
}

// Testo di avviso quando l'entità non esiste (stesso testo della card nativa).
export function entityNotFoundText(hass, entityId) {
  return hass.localize("ui.panel.lovelace.warning.entity_not_found", {
    entity: entityId || "[empty]",
  });
}

// Applica un tema HA a un elemento (versione ridotta di applyThemesOnElement).
export function applyThemeOnElement(element, themes, themeName) {
  const prev = element.__appliedThemeVars || [];
  prev.forEach((name) => element.style.removeProperty(name));
  element.__appliedThemeVars = [];

  if (!themeName || themeName === "default" || !themes?.themes?.[themeName]) {
    return;
  }

  const raw = themes.themes[themeName];
  const dark = themes.darkMode;
  const { modes, ...base } = raw;
  const vars = { ...base, ...(modes ? modes[dark ? "dark" : "light"] : {}) };

  Object.entries(vars).forEach(([key, value]) => {
    const name = `--${key}`;
    element.style.setProperty(name, String(value));
    element.__appliedThemeVars.push(name);
  });
}

// Assicura che gli elementi nativi usati dalla card siano caricati.
// Il frontend li carica "a richiesta": creando una thermostat card ufficiale
// (mai inserita in pagina) si forza il caricamento.
export async function ensureHaElements(entityId) {
  const required = [
    "ha-card",
    "ha-icon-button",
    CLIMATE_CONTROL,
    WATER_HEATER_CONTROL,
  ];
  const missing = () => required.filter((n) => !customElements.get(n));
  if (!missing().length) return;

  try {
    const helpers = await window.loadCardHelpers?.();
    helpers?.createCardElement({ type: "thermostat", entity: entityId });
  } catch (_err) {
    /* si prosegue: sotto c'è l'attesa con limite di tempo */
  }

  const timeout = new Promise((resolve) => setTimeout(resolve, 5000));
  await Promise.race([
    Promise.all(missing().map((n) => customElements.whenDefined(n))),
    timeout,
  ]);
}

// Colora di giallo SOLO la ghiera del quadrante nativo (alone e scritte restano del colore ufficiale).
// Aggiunge un foglio di stile dentro il quadrante, che agisce solo sullo slider circolare.
let jollySheet = null;
export function applyJollyRing(control, active) {
  const root = control?.shadowRoot;
  if (!root || !("adoptedStyleSheets" in root)) return;
  if (!jollySheet) {
    jollySheet = new CSSStyleSheet();
    jollySheet.replaceSync(
      `ha-control-circular-slider{--control-circular-slider-color:${JOLLY_COLOR} !important;` +
        `--control-circular-slider-low-color:${JOLLY_COLOR} !important;` +
        `--control-circular-slider-high-color:${JOLLY_COLOR} !important;` +
        `--state-color:${JOLLY_COLOR} !important;}`
    );
  }
  const has = root.adoptedStyleSheets.includes(jollySheet);
  if (active && !has) {
    root.adoptedStyleSheets = [...root.adoptedStyleSheets, jollySheet];
  } else if (!active && has) {
    root.adoptedStyleSheets = root.adoptedStyleSheets.filter((x) => x !== jollySheet);
  }
}

// Mette le icone di stato dentro la ghiera, sopra la scritta dello stato,
// a una distanza pari a quella tra le righe di testo del quadrante.
export function placeStatusIcons(container, control, overlay) {
  if (!container || !control || !overlay) return;
  const c = container.getBoundingClientRect();
  const r = control.getBoundingClientRect();
  const d = Math.max(0, r.width - 16);
  const centerY = r.top - c.top + 8 + d / 2;
  overlay.style.left = `${r.left - c.left + r.width / 2}px`;
  overlay.style.top = `${centerY - 2 * STATUS_STEP_RATIO * d}px`;
}

// Azione in corso del termostato (hvac_action) -> nome usato nei colori del tema.
const ACTION_COLOR_KEY = {
  heating: "heat",
  cooling: "cool",
  drying: "dry",
  fan: "fan_only",
  preheating: "heat",
  defrosting: "heat",
  idle: "idle",
  off: "off",
};

// Icone del badge sull'icona della tile (le stesse della card nativa).
export const ACTION_BADGE_ICONS = {
  heating: "mdi:fire",
  cooling: "mdi:snowflake",
  drying: "mdi:water-percent",
  fan: "mdi:fan",
  idle: "mdi:clock-outline",
  off: "mdi:power",
  preheating: "mdi:heat-wave",
  defrosting: "mdi:snowflake-melt",
};

// Colori del badge: riscaldamento sempre arancione, raffrescamento sempre azzurro,
// inattivo/spento sempre grigio.
const ORANGE = "var(--state-climate-heat-color, #ff8100)";
const BLUE = "var(--state-climate-cool-color, #2b9af9)";
const GREY = "var(--state-inactive-color, #9e9e9e)";
const BADGE_COLORS = {
  heating: ORANGE,
  preheating: ORANGE,
  defrosting: ORANGE,
  cooling: BLUE,
  drying: "var(--state-climate-dry-color, #efbd07)",
  fan: "var(--state-climate-fan_only-color, #8ac24a)",
  idle: GREY,
  off: GREY,
};
export const actionColor = (action) => BADGE_COLORS[action] || null;

// Colore del termostato come nella card nativa: l'azione in corso (riscaldamento, raffrescamento,
// inattivo...) prevale sulla modalità; senza azione si usa il colore dello stato.
export function hvacColor(stateObj) {
  const action = stateObj.attributes.hvac_action;
  if (action === "idle" || action === "off") {
    return `var(--state-climate-${action}-color, var(--state-inactive-color))`;
  }
  return actionColor(action) || stateColorCss(stateObj);
}
