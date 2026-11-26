// Quadrante del programma orario (24 ore, 3 livelli T1/T2/T3), dalla came-thermo-card.
// Componente "solo vista": riceve il profilo e segnala le modifiche con eventi.
// Le dimensioni arrivano dalla variabile --dial-size impostata dalla card.
import { LitElement, css, html, nothing } from "lit";
import { unsafeSVG } from "lit/directives/unsafe-svg.js";
import {
  CHAR_OF_LEVEL,
  DEG_PER_QUARTER,
  DOT_R,
  LABELS_SVG,
  LEVEL_COLORS,
  R,
  RING_W,
  pt,
  roundRun,
  runsOf,
  sector,
} from "./geometry.js";

const SPOKES_MS = 2000; // i raggi delle ore restano visibili 2 secondi dopo il tocco

// Tre piste continue (una per fascia) con la stessa tinta della ghiera nativa.
const TRACKS_SVG = [1, 2, 3]
  .map((l) => `<circle class="track" r="${(R[l] + R[l + 1]) / 2}" stroke-width="${RING_W}"/>`)
  .join("");
// Righe sottili del colore dello sfondo tra un anello e l'altro.
const SEPS_SVG = [2, 3].map((l) => `<circle class="sep" r="${R[l]}"/>`).join("");
// Raggi che separano le ore: appaiono solo mentre si tocca il quadrante.
const SPOKES_SVG = (() => {
  let g = "";
  for (let h = 0; h < 24; h++) {
    const [x1, y1] = pt(R[1], h * 15);
    const [x2, y2] = pt(R[4], h * 15);
    g += `<line x1="${x1.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${x2.toFixed(2)}" y2="${y2.toFixed(2)}"/>`;
  }
  return g;
})();

// Puntini chiari sulle due righe di divisione (T1/T2 e T2/T3), uno per ogni raggio delle ore.
// Restano sempre visibili, anche quando i raggi sono nascosti.
const DOTS_SVG = (() => {
  let g = "";
  for (const r of [R[2], R[3]]) {
    for (let h = 0; h < 24; h++) {
      const [x, y] = pt(r, h * 15);
      g += `<circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="${DOT_R}"/>`;
    }
  }
  return g;
})();

export class DomoProgramDial extends LitElement {
  static properties = {
    profile: { type: String },
    stepMinutes: { type: Number, attribute: "step-minutes" },
    dayLabel: { type: String, attribute: "day-label" },
    season: { type: String, reflect: true },
    warning: { type: String },
    locked: { type: Boolean },
    highlightHour: { type: Number, attribute: "highlight-hour" },
    _drag: { state: true },
    _spokes: { state: true },
  };

  static styles = [
    LEVEL_COLORS,
    css`
    :host {
      display: block;
      position: relative;
      width: var(--dial-size, 100%);
      height: var(--dial-size, 100%);
      color: var(--primary-text-color);
      font-family: inherit;
      user-select: none;
      -webkit-user-select: none;
      -webkit-touch-callout: none;
      --u: calc(var(--dial-size, 1080px) / 1080);
    }
    svg {
      display: block;
    }
    button {
      font: inherit;
      color: inherit;
      background: none;
      border: 0;
      padding: 0;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }
    .ringsvg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      touch-action: none;
      font-family: inherit;
      pointer-events: none;
    }
    .hit {
      fill: transparent;
      pointer-events: all;
    }
    .track {
      fill: none;
      stroke: var(--disabled-color, #888);
      stroke-opacity: 0.3;
    }
    .sep {
      fill: none;
      stroke: var(--card-background-color, #1c1c1c);
      stroke-width: 3;
    }
    .spokes {
      opacity: 0;
      transition: opacity 180ms ease-in-out;
    }
    .spokes.on {
      opacity: 1;
    }
    .spokes line {
      stroke: var(--card-background-color, #1c1c1c);
      stroke-width: 3;
    }
    .run1 {
      fill: var(--lvl1);
    }
    .run2 {
      fill: var(--lvl2);
    }
    .run3 {
      fill: var(--lvl3);
    }
    .full {
      fill: none;
    }
    .full1 {
      stroke: var(--lvl1);
    }
    .full2 {
      stroke: var(--lvl2);
    }
    .full3 {
      stroke: var(--lvl3);
    }
    .now {
      fill: var(--primary-text-color);
      fill-opacity: 0.12;
      stroke: none;
    }
    .hl-light {
      fill: var(--primary-text-color);
      fill-opacity: 0.18;
    }
    /* Ora attuale: le barre colorate di quell'ora vengono scurite un poco. */
    .dk path {
      fill: #000;
      fill-opacity: 0.16;
    }
    .dk circle {
      fill: none;
      stroke: #000;
      stroke-opacity: 0.16;
    }
    .dots circle {
      fill: var(--primary-text-color);
      fill-opacity: 0.5;
    }
    .tl text {
      font-size: 34px;
      font-weight: 700;
      text-anchor: middle;
      dominant-baseline: central;
    }
    .tl text {
      fill: var(--primary-text-color);
    }
    .labels text {
      fill: var(--secondary-text-color);
      font-size: 31px;
      font-weight: 600;
      text-anchor: middle;
      dominant-baseline: central;
    }
    .warn {
      position: absolute;
      left: 0;
      right: 0;
      top: 50%;
      transform: translateY(calc(var(--u) * 150));
      text-align: center;
      font-size: calc(var(--u) * 30);
      color: var(--warning-color, #ffb74d);
      padding: 0 calc(var(--u) * 200);
      pointer-events: none;
    }
    .center {
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      width: calc(var(--u) * 400);
      text-align: center;
      display: flex;
      justify-content: center;
      pointer-events: none;
    }
    .center > * {
      pointer-events: auto;
    }
    .daybtn {
      padding: calc(var(--u) * 10) calc(var(--u) * 30);
      border-radius: 12px;
      position: relative;
      overflow: hidden;
    }
    .daybtn::before {
      content: "";
      position: absolute;
      inset: 0;
      background: var(--disabled-color, rgba(127, 127, 127, 0.5));
      opacity: 0.2;
      transition: opacity 180ms ease-in-out;
    }
    .daybtn:hover::before {
      opacity: 0.28;
    }
    .daylbl {
      position: relative;
      display: block;
      font-size: calc(var(--u) * 60);
      font-weight: 800;
      line-height: calc(var(--u) * 80);
      white-space: nowrap;
    }
  `,
  ];

  constructor() {
    super();
    this.profile = "";
    this.stepMinutes = 60;
    this.highlightHour = -1;
    this._spokes = false;
    this._drag = null;
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearTimeout(this._spokesTimer);
  }

  // ---- disegno delle barre (con l'anteprima del trascinamento) ----
  // Ogni livello è una barra piena nel proprio anello, con le estremità arrotondate come la ghiera;
  // i quarti d'ora consecutivi dello stesso livello si uniscono in un'unica barra.
  _runs() {
    const n = this.stepMinutes / 15;
    const arr = [...(this.profile || "1".repeat(96))];
    if (this._drag) {
      for (const [q, l] of this._drag.cells) {
        for (let i = 0; i < n; i++) arr[q + i] = CHAR_OF_LEVEL[l];
      }
    }
    return runsOf(arr);
  }

  _cellsSvg(runs) {
    let body = "";
    for (const r of runs) {
      if (r.full) {
        body += `<circle class="full full${r.lvl}" r="${(R[r.lvl] + R[r.lvl + 1]) / 2}" stroke-width="${RING_W}"/>`;
        continue;
      }
      const d = roundRun(R[r.lvl], R[r.lvl + 1], r.start * DEG_PER_QUARTER, (r.start + r.len) * DEG_PER_QUARTER);
      body += `<path class="run${r.lvl}" d="${d}"/>`;
    }
    return body;
  }

  // Parte scurita: la stessa forma delle barre, ritagliata sull'ora attuale.
  _darkSvg(runs) {
    const h = this.highlightHour;
    if (!(h >= 0 && h < 24)) return "";
    let g = "";
    for (const r of runs) {
      if (r.full) g += `<circle r="${(R[r.lvl] + R[r.lvl + 1]) / 2}" stroke-width="${RING_W}"/>`;
      else g += `<path d="${roundRun(R[r.lvl], R[r.lvl + 1], r.start * DEG_PER_QUARTER, (r.start + r.len) * DEG_PER_QUARTER)}"/>`;
    }
    return `<defs><clipPath id="nowclip"><path d="${sector(R[1], R[4], h * 15, (h + 1) * 15)}"/></clipPath></defs><g class="dk" clip-path="url(#nowclip)">${g}</g>`;
  }

  // Etichette T1/T2/T3 sul raggio delle 0, al centro di ogni anello, sempre nel colore normale del testo.
  _tlabelsSvg() {
    return [1, 2, 3]
      .map((l) => `<text x="0" y="${(-(R[l] + R[l + 1]) / 2).toFixed(2)}">T${l}</text>`)
      .join("");
  }

  // Anteprima mentre si trascina: la casella toccata un po' più chiara.
  _previewSvg() {
    if (!this._drag) return "";
    const n = this.stepMinutes / 15;
    let over = "";
    for (const [q, l] of this._drag.cells) {
      over += `<path class="hl-light" d="${sector(R[l], R[l + 1], q * DEG_PER_QUARTER, (q + n) * DEG_PER_QUARTER)}"/>`;
    }
    return over;
  }

  // Fascia dell'ora attuale: sfondo un po' più chiaro su tutte le fasce.
  // Va costruita come testo SVG: un frammento "html" dentro il disegno non verrebbe mostrato.
  _nowSvg() {
    const h = this.highlightHour;
    if (!(h >= 0 && h < 24)) return "";
    return `<path class="now" d="${sector(R[1], R[4], h * 15, (h + 1) * 15)}"/>`;
  }

  // ---- interazione ----
  _pos(e) {
    const rect = this.renderRoot.querySelector(".ringsvg").getBoundingClientRect();
    const s = 1080 / rect.width;
    const x = (e.clientX - rect.left) * s - 540;
    const y = (e.clientY - rect.top) * s - 540;
    let ang = (Math.atan2(x, -y) * 180) / Math.PI;
    if (ang < 0) ang += 360;
    return { r: Math.hypot(x, y), a: ang };
  }

  _onDown(e) {
    if (this.locked) return;
    const p = this._pos(e);
    if (p.r < R[1] || p.r > R[4] + 25) return;
    e.preventDefault();
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch (_err) {
      /* ignora */
    }
    this._drag = { cells: new Map(), id: e.pointerId };
    clearTimeout(this._spokesTimer);
    this._spokes = true;
    this._paint(p);
  }

  _onMove(e) {
    if (!this._drag || e.pointerId !== this._drag.id) return;
    const p = this._pos(e);
    if (p.r < R[1]) return;
    this._paint(p);
  }

  _paint(p) {
    const level = p.r < R[2] ? 1 : p.r < R[3] ? 2 : 3;
    const n = this.stepMinutes / 15;
    const q = Math.min(Math.floor((p.a * 4) / this.stepMinutes) * n, 96 - n);
    if (this._drag.cells.get(q) !== level) {
      this._drag.cells.set(q, level);
      this.requestUpdate();
    }
  }

  _onUp(e) {
    const d = this._drag;
    if (!d || e.pointerId !== d.id) return;
    this._drag = null;
    clearTimeout(this._spokesTimer);
    this._spokesTimer = setTimeout(() => (this._spokes = false), SPOKES_MS);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch (_err) {
      /* ignora */
    }
    if (!this.profile || !d.cells.size) return;
    const n = this.stepMinutes / 15;
    const arr = [...this.profile];
    for (const [q, l] of d.cells) for (let i = 0; i < n; i++) arr[q + i] = CHAR_OF_LEVEL[l];
    const next = arr.join("");
    if (next !== this.profile) {
      this.dispatchEvent(new CustomEvent("profile-change", { detail: { profile: next } }));
    }
  }

  _fire(name, detail) {
    this.dispatchEvent(new CustomEvent(name, { detail }));
  }

  render() {
    const runs = this._runs();
    return html`
      <svg
        class="ringsvg"
        viewBox="-540 -540 1080 1080"
        @pointerdown=${this._onDown}
        @pointermove=${this._onMove}
        @pointerup=${this._onUp}
        @pointercancel=${this._onUp}
      >
        <circle class="hit" r=${R[4] + 25}></circle>
        <g class="tracks">${unsafeSVG(TRACKS_SVG)}</g>
        ${unsafeSVG(this._nowSvg())}
        <g class="cells">${unsafeSVG(this._cellsSvg(runs))}</g>
        ${unsafeSVG(this._darkSvg(runs))}
        <g class="seps">${unsafeSVG(SEPS_SVG)}</g>
        <g class="spokes ${this._spokes ? "on" : ""}">${unsafeSVG(SPOKES_SVG)}</g>
        <g class="dots">${unsafeSVG(DOTS_SVG)}</g>
        ${unsafeSVG(this._previewSvg())}
        <g class="tl">${unsafeSVG(this._tlabelsSvg())}</g>
        <g class="labels">${unsafeSVG(LABELS_SVG)}</g>
      </svg>
      ${this.warning ? html`<div class="warn">${this.warning}</div>` : nothing}
      <div class="center">
        <button class="daybtn" @click=${() => this._fire("day-open")}>
          <span class="daylbl">${this.dayLabel}</span>
        </button>
      </div>
    `;
  }
}
