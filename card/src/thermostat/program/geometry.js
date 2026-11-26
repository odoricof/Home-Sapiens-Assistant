import { css } from "lit";

// Geometria del quadrante del programma (ricavata da came-thermo-card).
// Unità = pixel dello screenshot originale di 1080 px.
// R[4] = bordo esterno (invariato, coincide con quello della ghiera nativa). I tre anelli sono
// larghi come la ghiera del termostato nativo: 24 su un diametro esterno di 314 = circa 72 unità.
// R[1] = inizio della fascia T1, R[0] = R[1].
export const RING_W = 72;
export const R = [256, 256, 328, 400, 472];
// Le ore stanno subito dentro la fascia T1.
export const LABEL_R = 228;
// Colori dei livelli: tutti e tre uguali, l'arancione (inverno) o l'azzurro (estate) della ghiera
// ufficiale al 50%, come la ghiera a temperatura raggiunta (senza alone acceso). Il livello si legge
// dall'anello (T1 dentro, T3 fuori) e dalle etichette. Il componente imposta season="summer" per l'estate.
export const LEVEL_COLORS = css`
  :host {
    --season: var(--state-climate-heat-color, #ff8100);
  }
  :host([season="summer"]) {
    --season: var(--state-climate-cool-color, #2b9af9);
  }
  :host {
    --lvl1: color-mix(in srgb, var(--season) 50%, transparent);
    --lvl2: var(--lvl1);
    --lvl3: var(--lvl1);
  }
`;
// Puntino sulle righe di divisione tra i livelli, in corrispondenza dei raggi delle ore:
// diametro uguale allo spessore della riga di divisione (3 unità).
export const DOT_R = 1.5;
export const CHAR_OF_LEVEL = { 1: "1", 2: "3", 3: "5" };
export const LEVEL_OF_CHAR = { 1: 1, 2: 1, 3: 2, 4: 2, 5: 3 };
export const DEG_PER_QUARTER = 3.75;
export const pt = (r, a) => {
  const t = (a * Math.PI) / 180;
  return [r * Math.sin(t), -r * Math.cos(t)];
};
const f2 = (n) => n.toFixed(2);

export const sector = (r0, r1, a0, a1) => {
  const [x1, y1] = pt(r1, a0);
  const [x2, y2] = pt(r1, a1);
  const [x3, y3] = pt(r0, a1);
  const [x4, y4] = pt(r0, a0);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M${f2(x1)} ${f2(y1)}A${r1} ${r1} 0 ${large} 1 ${f2(x2)} ${f2(y2)}L${f2(x3)} ${f2(y3)}A${r0} ${r0} 0 ${large} 0 ${f2(x4)} ${f2(y4)}Z`;
};

export const levelOf = (ch) => LEVEL_OF_CHAR[ch] || 1;
export const isValidProfile = (p) => typeof p === "string" && p.length === 96;

// Numeri delle ore (non cambiano mai: calcolati una volta sola).
export const LABELS_SVG = (() => {
  let labels = "";
  for (let h = 0; h < 24; h++) {
    const [x, y] = pt(LABEL_R, h * 15);
    labels += `<text x="${f2(x)}" y="${f2(y)}">${h}</text>`;
  }
  return labels;
})();

const RAD = Math.PI / 180;

// Raggio di arrotondamento di un'estremità: al massimo metà della larghezza dell'anello
// (semicerchio); se la barra è corta si riduce, così gli angoli restano solo arrotondati.
// "span" è l'ampiezza della barra in gradi.
export const capRadius = (ri, ro, span) => {
  const half = (ro - ri) / 2;
  const sn = Math.sin((span * RAD) / 2);
  const lim = (ri * sn) / (1 - sn); // oltre questo i due angoli interni si incrocerebbero
  const len = (((ri + ro) / 2) * span * RAD) / 2;
  return Math.max(0, Math.min(half, len, lim * 0.98));
};

// Barra di anello (da a0 a a1 gradi, tra i raggi ri e ro) con le estremità arrotondate come la
// ghiera nativa. roundStart / roundEnd = false lascia quel lato dritto (taglio radiale).
export const roundRun = (ri, ro, a0, a1, roundStart = true, roundEnd = true) => {
  const rho = capRadius(ri, ro, a1 - a0);
  const ps = roundStart ? rho : 0;
  const pe = roundEnd ? rho : 0;
  const shift = (r, p, outer) => Math.asin(p / (outer ? r - p : r + p)) / RAD;
  const foot = (r, p, outer) => {
    const c = outer ? r - p : r + p;
    return Math.sqrt(c * c - p * p);
  };
  const P = (r, a) => pt(r, a).map(f2).join(" ");
  const aOs = a0 + (ps > 0 ? shift(ro, ps, true) : 0);
  const aOe = a1 - (pe > 0 ? shift(ro, pe, true) : 0);
  const aIs = a0 + (ps > 0 ? shift(ri, ps, false) : 0);
  const aIe = a1 - (pe > 0 ? shift(ri, pe, false) : 0);
  let d = ps > 0 ? `M${P(foot(ro, ps, true), a0)}A${f2(ps)} ${f2(ps)} 0 0 1 ${P(ro, aOs)}` : `M${P(ro, a0)}`;
  d += `A${ro} ${ro} 0 ${aOe - aOs > 180 ? 1 : 0} 1 ${P(ro, aOe)}`;
  if (pe > 0) d += `A${f2(pe)} ${f2(pe)} 0 0 1 ${P(foot(ro, pe, true), a1)}L${P(foot(ri, pe, false), a1)}A${f2(pe)} ${f2(pe)} 0 0 1 ${P(ri, aIe)}`;
  else d += `L${P(ri, a1)}`;
  d += `A${ri} ${ri} 0 ${aIe - aIs > 180 ? 1 : 0} 0 ${P(ri, aIs)}`;
  if (ps > 0) d += `A${f2(ps)} ${f2(ps)} 0 0 1 ${P(foot(ri, ps, false), a0)}`;
  return `${d}Z`;
};

// Raggruppa i quarti d'ora consecutivi dello stesso livello, in cerchio (nessuno stacco a
// mezzanotte). Ogni gruppo: { lvl, start, len }; se tutto il giorno è dello stesso livello: full.
export const runsOf = (arr) => {
  const n = arr.length;
  const lv = arr.map(levelOf);
  let s0 = -1;
  for (let i = 0; i < n; i++) {
    if (lv[i] !== lv[(i + n - 1) % n]) {
      s0 = i;
      break;
    }
  }
  if (s0 < 0) return [{ lvl: lv[0], start: 0, len: n, full: true }];
  const runs = [];
  let cur = null;
  for (let k = 0; k < n; k++) {
    const i = (s0 + k) % n;
    if (cur && cur.lvl === lv[i]) cur.len++;
    else {
      cur = { lvl: lv[i], start: i, len: 1 };
      runs.push(cur);
    }
  }
  return runs;
};
