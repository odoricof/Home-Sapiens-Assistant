// Gestione delle modalità HVAC con Jolly (che per Home Sapiens Assistant è un preset).
import { HVAC_ICONS, HVAC_ORDER, JOLLY_PRESET, MODE_SHORT } from "./const.js";
import { t } from "./i18n.js";

export const isJolly = (stateObj) =>
  stateObj.attributes.preset_mode === JOLLY_PRESET ||
  stateObj.attributes.mode === "jolly";

export const supportsJolly = (stateObj) =>
  (stateObj.attributes.preset_modes || []).includes(JOLLY_PRESET);

// Estate se il termostato offre il raffrescamento ma non il riscaldamento; se offre entrambi,
// conta la modalità o l'azione in corso. In tutti gli altri casi è inverno.
export function isSummer(stateObj) {
  const modes = stateObj?.attributes?.hvac_modes || [];
  const cool = modes.includes("cool");
  const heat = modes.includes("heat");
  if (cool && !heat) return true;
  if (cool && heat) {
    return stateObj.state === "cool" || stateObj.attributes.hvac_action === "cooling";
  }
  return false;
}

// Modalità attuale: "jolly" se è attivo il preset Jolly, altrimenti lo stato.
export const currentMode = (stateObj) =>
  isJolly(stateObj) ? "jolly" : stateObj.state;

function modeLabel(hass, stateObj, mode) {
  if (mode === "jolly") return t(hass, "jollyLabel");
  const text = hass.formatEntityState?.(stateObj, mode);
  if (text) return text;
  return mode.charAt(0).toUpperCase() + mode.slice(1).replace(/_/g, " ");
}

// Elenco delle voci del menu: modalità dell'entità (filtrate come fa la card
// nativa dalla chiave hvac_modes) più Jolly, in ordine standard.
export function modeOptions(hass, stateObj, feature, short = false) {
  const wanted = feature?.hvac_modes;
  let modes = (stateObj.attributes.hvac_modes || []).filter(
    (m) => !wanted || wanted.includes(m)
  );
  if (supportsJolly(stateObj) && (!wanted || wanted.includes("jolly"))) {
    modes = [...modes, "jolly"];
  }
  const rank = (m) => {
    const i = HVAC_ORDER.indexOf(m);
    return i === -1 ? HVAC_ORDER.length : i;
  };
  return modes
    .sort((a, b) => rank(a) - rank(b))
    .map((value) => ({
      value,
      label: (short && MODE_SHORT[value]) || modeLabel(hass, stateObj, value),
      icon: HVAC_ICONS[value] || "mdi:thermostat",
    }));
}

// Comando da inviare a Home Assistant per la voce scelta.
export function modeService(entityId, mode) {
  if (mode === "jolly") {
    return ["climate", "set_preset_mode", { entity_id: entityId, preset_mode: JOLLY_PRESET }];
  }
  return ["climate", "set_hvac_mode", { entity_id: entityId, hvac_mode: mode }];
}
