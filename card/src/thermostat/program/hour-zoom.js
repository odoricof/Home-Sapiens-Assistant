// Vista "lente": uno spicchio ingrandito con i 4 quarti d'ora di una sola ora.
// Occupa tutta l'area del quadrante (raggio = diametro del quadrante, apertura 60°),
// con la punta in basso al centro. Stessi colori e livelli (T1/T2/T3) del quadrante generale.
// Componente "solo vista": segnala le modifiche con gli eventi profile-change e hour-change.
import { LitElement, css, html } from "lit";
import { unsafeSVG } from "lit/directives/unsafe-svg.js";
import { CHAR_OF_LEVEL, LEVEL_COLORS, levelOf, pt, roundRun, sector } from "./geometry.js";

const R_OUT = 1080; // raggio dello spicchio = diametro del quadrante (unità 1080)
const R1 = 994; // bordo esterno delle celle (sopra restano gli orari)
const R0 = 360; // punta tagliata: sotto restano i pulsanti − ora +
const BAND = (R1 - R0) / 3;
const HALF = 30; // mezza apertura in gradi
const COLS = 4;
const COL_DEG = (HALF * 2) / COLS;

const edge = (k) => R0 + BAND * k;
const f2 = (n) => n.toFixed(2);
const pad = (n) => String(n).padStart(2, "0");

const arc = (r, a0, a1) => {
  const [x1, y1] = pt(r, a0);
  const [x2, y2] = pt(r, a1);
  return `M${f2(x1)} ${f2(y1)}A${r} ${r} 0 0 1 ${f2(x2)} ${f2(y2)}`;
};

// Piste continue (una per fascia, come gli anelli del quadrante), righe sottili del colore dello
// sfondo tra le fasce e raggi tra i quarti d'ora, sempre visibili.
const TRACKS = [1, 2, 3].map((k) => `<path class="track" d="${sector(edge(k - 1), edge(k), -HALF, HALF)}"/>`).join("");
const SEPS = [1, 2].map((k) => `<path d="${arc(edge(k), -HALF, HALF)}"/>`).join("");
const SPOKES = (() => {
  let g = "";
  for (let i = 1; i < COLS; i++) {
    const a = -HALF + i * COL_DEG;
    const [x1, y1] = pt(R0, a);
    const [x2, y2] = pt(R1, a);
    g += `<line x1="${f2(x1)}" y1="${f2(y1)}" x2="${f2(x2)}" y2="${f2(y2)}"/>`;
  }
  return g;
})();

export class DomoHourZoom extends LitElement {
  static properties = {
    profile: { type: String },
    hour: { type: Number },
    dayLabel: { type: String, attribute: "day-label" },
    hourLabel: { type: String, attribute: "hour-label" },
    season: { type: String, reflect: true },
    _drag: { state: true },
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
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      touch-action: none;
      font-family: inherit;
    }
    .track {
      fill: var(--disabled-color, #888);
      fill-opacity: 0.3;
    }
    .seps path,
    .spokes line {
      fill: none;
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
    .hl-light {
      fill: var(--primary-text-color);
      fill-opacity: 0.18;
    }
    .tl text {
      font-size: 100px;
      font-weight: 700;
      text-anchor: middle;
      dominant-baseline: central;
    }
    .tl text {
      fill: var(--primary-text-color);
    }
    .times text {
      fill: var(--secondary-text-color);
      font-size: 31px;
      font-weight: 600;
      dominant-baseline: central;
    }
    .day {
      fill: var(--primary-text-color);
      font-size: 64px;
      font-weight: 800;
      text-anchor: middle;
      dominant-baseline: central;
    }
    .controls {
      position: absolute;
      left: 50%;
      bottom: calc(var(--u) * 20);
      transform: translateX(-50%);
      display: flex;
      align-items: center;
      gap: calc(var(--u) * 28);
    }
    button {
      font: inherit;
      color: var(--secondary-text-color);
      background: none;
      cursor: pointer;
      width: calc(var(--u) * 150);
      height: calc(var(--u) * 150);
      border-radius: 50%;
      border: 1px solid var(--secondary-text-color);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }
    button ha-icon {
      --mdc-icon-size: calc(var(--u) * 80);
      display: flex;
    }
    input {
      font: inherit;
      font-size: calc(var(--u) * 100);
      font-weight: 600;
      width: calc(var(--u) * 190);
      height: calc(var(--u) * 150);
      box-sizing: border-box;
      text-align: center;
      color: var(--primary-text-color);
      background: none;
      border: 1px solid var(--divider-color, var(--secondary-text-color));
      border-radius: calc(var(--u) * 28);
      padding: 0;
      outline: none;
    }
    input:focus {
      border-color: var(--primary-color);
    }
  `,
  ];

  constructor() {
    super();
    this.profile = "";
    this.hour = 0;
    this._drag = null;
  }

  _qOf(col) {
    return this.hour * 4 + col;
  }

  // Come nel quadrante: barre piene con le estremità arrotondate, una per livello. Un lato resta
  // dritto (taglio della lente) solo se la barra prosegue oltre l'ora mostrata.
  _cellsSvg() {
    const arr = [...(this.profile || "1".repeat(96))];
    let over = "";
    if (this._drag) {
      for (const [q, l] of this._drag.cells) {
        arr[q] = CHAR_OF_LEVEL[l];
        const a0 = -HALF + (q - this.hour * 4) * COL_DEG;
        over += `<path class="hl-light" d="${sector(edge(l - 1), edge(l), a0, a0 + COL_DEG)}"/>`;
      }
    }
    const lv = arr.map(levelOf);
    const q0 = this.hour * 4;
    let body = "";
    for (let l = 1; l <= 3; l++) {
      let i = 0;
      while (i < COLS) {
        if (lv[q0 + i] !== l) {
          i++;
          continue;
        }
        let j = i;
        while (j + 1 < COLS && lv[q0 + j + 1] === l) j++;
        const flatStart = i === 0 && lv[(q0 - 1 + 96) % 96] === l;
        const flatEnd = j === COLS - 1 && lv[(q0 + COLS) % 96] === l;
        const d = roundRun(edge(l - 1), edge(l), -HALF + i * COL_DEG, -HALF + (j + 1) * COL_DEG, !flatStart, !flatEnd);
        body += `<path class="run${l}" d="${d}"/>`;
        i = j + 1;
      }
    }
    return body + over;
  }

  // Etichette T1/T2/T3 sul raggio centrale, al centro di ogni fascia (dimensioni proporzionali alla
  // lente), sempre nel colore normale del testo.
  _tlabelsSvg() {
    return [1, 2, 3].map((l) => `<text x="0" y="${f2(-(edge(l - 1) + edge(l)) / 2)}">T${l}</text>`).join("");
  }

  _timesSvg() {
    let s = "";
    for (let i = 0; i <= COLS; i++) {
      const a = -HALF + i * COL_DEG;
      const [x, y] = pt((R1 + R_OUT) / 2, a);
      const m = this.hour * 60 + i * 15;
      const anchor = i === 0 ? "start" : i === COLS ? "end" : "middle";
      s += `<text x="${f2(x)}" y="${f2(y)}" text-anchor="${anchor}">${pad(Math.floor(m / 60) % 24)}:${pad(m % 60)}</text>`;
    }
    return s;
  }

  // ---- interazione ----
  _pos(e) {
    const rect = this.renderRoot.querySelector("svg").getBoundingClientRect();
    const s = 1080 / rect.width;
    const x = (e.clientX - rect.left) * s - 540;
    const y = (e.clientY - rect.top) * s - 1080;
    return { r: Math.hypot(x, y), a: (Math.atan2(x, -y) * 180) / Math.PI };
  }

  _onDown(e) {
    const p = this._pos(e);
    if (p.r < R0 || p.r > R1 + 20 || Math.abs(p.a) > HALF) return;
    e.preventDefault();
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch (_err) {
      /* ignora */
    }
    this._drag = { cells: new Map(), id: e.pointerId };
    this._paint(p);
  }

  _onMove(e) {
    if (!this._drag || e.pointerId !== this._drag.id) return;
    const p = this._pos(e);
    if (p.r < R0) return;
    this._paint(p);
  }

  _paint(p) {
    const level = p.r < edge(1) ? 1 : p.r < edge(2) ? 2 : 3;
    const a = Math.max(-HALF, Math.min(HALF - 0.001, p.a));
    const col = Math.floor((a + HALF) / COL_DEG);
    const q = this._qOf(col);
    if (this._drag.cells.get(q) !== level) {
      this._drag.cells.set(q, level);
      this.requestUpdate();
    }
  }

  _onUp(e) {
    const d = this._drag;
    if (!d || e.pointerId !== d.id) return;
    this._drag = null;
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch (_err) {
      /* ignora */
    }
    if (!this.profile || !d.cells.size) return;
    const arr = [...this.profile];
    for (const [q, l] of d.cells) arr[q] = CHAR_OF_LEVEL[l];
    const next = arr.join("");
    if (next !== this.profile) {
      this.dispatchEvent(new CustomEvent("profile-change", { detail: { profile: next } }));
    }
  }

  _setHour(h) {
    const hour = ((Math.round(h) % 24) + 24) % 24;
    this.dispatchEvent(new CustomEvent("hour-change", { detail: { hour } }));
  }

  _typed(e) {
    const v = parseInt(e.target.value, 10);
    if (Number.isNaN(v)) {
      e.target.value = pad(this.hour);
      return;
    }
    this._setHour(Math.min(23, Math.max(0, v)));
    e.target.value = pad(Math.min(23, Math.max(0, v)));
  }

  render() {
    return html`
      <svg
        viewBox="-540 -1080 1080 1080"
        @pointerdown=${this._onDown}
        @pointermove=${this._onMove}
        @pointerup=${this._onUp}
        @pointercancel=${this._onUp}
      >
        <g class="tracks">${unsafeSVG(TRACKS)}</g>
        <g class="cells">${unsafeSVG(this._cellsSvg())}</g>
        <g class="seps">${unsafeSVG(SEPS)}</g>
        <g class="spokes">${unsafeSVG(SPOKES)}</g>
        <g class="tl">${unsafeSVG(this._tlabelsSvg())}</g>
        <g class="times">${unsafeSVG(this._timesSvg())}</g>
        <text class="day" x="0" y="-262">${this.dayLabel}</text>
      </svg>
      <div class="controls">
        <button aria-label="-" @click=${() => this._setHour(this.hour - 1)}>
          <ha-icon icon="mdi:minus"></ha-icon>
        </button>
        <input
          type="text"
          inputmode="numeric"
          maxlength="2"
          aria-label=${this.hourLabel}
          .value=${pad(this.hour)}
          @focus=${(e) => e.target.select()}
          @change=${this._typed}
          @keydown=${(e) => e.key === "Enter" && e.target.blur()}
        />
        <button aria-label="+" @click=${() => this._setHour(this.hour + 1)}>
          <ha-icon icon="mdi:plus"></ha-icon>
        </button>
      </div>
    `;
  }
}

