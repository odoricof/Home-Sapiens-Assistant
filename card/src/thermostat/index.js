// Punto di ingresso: registra i componenti e le due card, e le rende visibili nel selettore delle card.
//
// Dalla versione 2026.9 il frontend sostituisce il registro dei componenti: un componente definito
// troppo presto (prima che Home Assistant sia pronto) non viene visto. Per questo la registrazione
// avviene solo dopo che l'elemento "home-assistant" esiste (con un limite di attesa di sicurezza).

import {
  CARD_TYPE,
  EDITOR_TYPE,
  MINIMAL_EDITOR_TYPE,
  MINIMAL_TYPE,
} from "./const.js";
import { DomoThermostatDialog } from "./dialog/more-info-dialog.js";
import { DomoFeatureButton } from "./features/feature-button.js";
import { DomoFeatureSelect } from "./features/feature-select.js";
import { DomoMinimalCard } from "./minimal-card.js";
import { DomoMinimalCardEditor } from "./minimal-card-editor.js";
import { DomoCopyDialog } from "./program/copy-dialog.js";
import { DomoDayDialog } from "./program/day-dialog.js";
import { DomoHourZoom } from "./program/hour-zoom.js";
import { DomoProgramDial } from "./program/program-dial.js";
import { DomoTempFields } from "./program/temp-fields.js";
import { DomoStatusIcons } from "./status-icons.js";
import { DomoThermostatCard } from "./thermostat-card.js";
import { DomoThermostatCardEditor } from "./thermostat-card-editor.js";

// I componenti interni vanno definiti prima delle card che li usano.
const ELEMENTS = [
  ["domo-status-icons", DomoStatusIcons],
  ["domo-feature-button", DomoFeatureButton],
  ["domo-feature-select", DomoFeatureSelect],
  ["domo-program-dial", DomoProgramDial],
  ["domo-hour-zoom", DomoHourZoom],
  ["domo-temp-fields", DomoTempFields],
  ["domo-copy-dialog", DomoCopyDialog],
  ["domo-day-dialog", DomoDayDialog],
  ["domo-thermostat-dialog", DomoThermostatDialog],
  [EDITOR_TYPE, DomoThermostatCardEditor],
  [MINIMAL_EDITOR_TYPE, DomoMinimalCardEditor],
  [CARD_TYPE, DomoThermostatCard],
  [MINIMAL_TYPE, DomoMinimalCard],
];

const CARDS = [
  [
    CARD_TYPE,
    "Domo Thermostat",
    "Replica della Thermostat Card nativa per i termostati dell'integrazione domo.",
  ],
  [
    MINIMAL_TYPE,
    "Domo Thermostat Minimal",
    "Replica della tile card nativa con modalità, Jolly e icone finestra/presenza.",
  ],
];

const WAIT_FOR_HA_MS = 10000;

async function register() {
  await Promise.race([
    window.customElements.whenDefined("home-assistant"),
    new Promise((resolve) => setTimeout(resolve, WAIT_FOR_HA_MS)),
  ]);

  for (const [name, definition] of ELEMENTS) {
    if (!window.customElements.get(name)) {
      window.customElements.define(name, definition);
    }
  }

  window.customCards = window.customCards || [];
  for (const [type, name, description] of CARDS) {
    if (!window.customCards.some((card) => card.type === type)) {
      window.customCards.push({ type, name, description, preview: true });
    }
  }
}

register();
