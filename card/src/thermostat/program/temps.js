// T1 / T2 / T3 del termostato: sono entità "number" (categoria config) dello stesso dispositivo
// del climate (platform domo), esposte da number.py dell'integrazione.

export const TEMP_KEYS = ["t1", "t2", "t3"];
const DEFAULT = { min: 5, max: 35, step: 0.1 };

// Cerca le tre entità number T1/T2/T3 che appartengono allo stesso dispositivo del climate.
export function findTempEntities(hass, climateId) {
  const device = hass?.entities?.[climateId]?.device_id;
  if (!device) return null;
  const found = {};
  for (const [id, ent] of Object.entries(hass.entities)) {
    if (!id.startsWith("number.") || ent.device_id !== device) continue;
    const name = String(hass.states[id]?.attributes?.friendly_name || "").trim().toLowerCase();
    const slug = id.split(".")[1];
    for (const key of TEMP_KEYS) {
      if (name === key || name.endsWith(` ${key}`) || slug.endsWith(`_${key}`)) found[key] = id;
    }
  }
  return TEMP_KEYS.every((k) => found[k]) ? found : null;
}

export function readTemps(hass, entities) {
  const out = {};
  for (const key of TEMP_KEYS) {
    const st = hass.states[entities[key]];
    const v = st ? parseFloat(st.state) : NaN;
    out[key] = Number.isNaN(v) ? null : v;
  }
  return out;
}

export function limitsOf(hass, entityId) {
  const a = hass.states[entityId]?.attributes || {};
  return {
    min: Number(a.min ?? DEFAULT.min),
    max: Number(a.max ?? DEFAULT.max),
    step: Number(a.step ?? DEFAULT.step),
  };
}

const round1 = (v) => Math.round(v * 10) / 10;

// Stessa regola di number.py: T1 < T2 < T3, si corregge solo il valore appena cambiato.
export function clampTemp(key, value, temps, limits) {
  const { t1, t2, t3 } = temps;
  const { min, max, step } = limits;
  let v = round1(Math.round(value / step) * step);
  if (key === "t1" && t2 != null && v >= t2) v = round1(t2 - step);
  else if (key === "t2") {
    if (t1 != null && v <= t1) v = round1(t1 + step);
    else if (t3 != null && v >= t3) v = round1(t3 - step);
  } else if (key === "t3" && t2 != null && v <= t2) v = round1(t2 + step);
  return Math.max(min, Math.min(max, v));
}

// Ordine di scrittura che non scatena correzioni del gateway:
// prima gli aumenti dal più alto al più basso, poi le diminuzioni dal più basso al più alto.
export function writeOrder(changes, current) {
  const ups = ["t3", "t2", "t1"].filter((k) => k in changes && changes[k] > (current[k] ?? -Infinity));
  const downs = ["t1", "t2", "t3"].filter((k) => k in changes && !ups.includes(k));
  return [...ups, ...downs];
}
