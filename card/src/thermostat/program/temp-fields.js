// Tre campi T1 / T2 / T3 in orizzontale, ripresi da "ha-control-number-buttons" di Home Assistant
// (la barra con − valore + della panoramica): etichetta T1/T2/T3 in alto a sinistra, fuori dalla barra, sopra il meno.
// Componente "solo vista": segnala le modifiche con l'evento temp-change {key, value}.
import { LitElement, css, html } from "lit";
import { LEVEL_COLORS } from "./geometry.js";
import { TEMP_KEYS } from "./temps.js";

const ARROW_STEP = 0.5;
// Stessi simboli (mdiMinus / mdiPlus) usati da Home Assistant.
const MINUS = html`<svg viewBox="0 0 24 24"><path d="M19,13H5V11H19V13Z" /></svg>`;
const PLUS = html`<svg viewBox="0 0 24 24"><path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z" /></svg>`;

export class DomoTempFields extends LitElement {
  static properties = {
    values: { attribute: false },
    language: { type: String },
    disabled: { type: Boolean },
    season: { type: String, reflect: true },
  };

  static styles = [
    LEVEL_COLORS,
    css`
    /* La fascia sopra il quadrante resta alta come prima (45 px): le barre, alte come i pulsanti
       sotto (--feature-height), partono dall'alto senza spostare nulla. */
    :host {
      display: flex;
      align-items: flex-start;
      justify-content: center;
      gap: 12px;
      width: 100%;
      height: 100%;
      box-sizing: border-box;
      padding: 0 16px;
      font-family: inherit;
      --mdc-icon-size: 16px;
    }
    /* Come ha-control-number-buttons: sfondo --disabled-color al 20%, − e + larghi 35 px ai lati. */
    /* Contenitore: tiene l'etichetta fuori dalla barra, nel margine sopra, senza spostare la barra. */
    .cell {
      position: relative;
      flex: 1 1 0;
      min-width: 0;
      max-width: 190px;
    }
    .box {
      position: relative;
      width: 100%;
      height: var(--feature-height, 48px);
      box-sizing: border-box;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--feature-border-radius, 12px);
      overflow: hidden;
      color: var(--primary-text-color);
      font-weight: var(--ha-font-weight-medium, 500);
    }
    .box::before {
      content: "";
      position: absolute;
      inset: 0;
      background: var(--disabled-color, rgba(127, 127, 127, 0.5));
      opacity: 0.2;
    }
    .box:focus-within {
      box-shadow: 0 0 0 2px var(--secondary-text-color);
    }
    .lbl {
      position: absolute;
      bottom: 100%;
      margin-bottom: 3px;
      left: 0;
      width: 35px;
      text-align: center;
      font-size: 11px;
      font-weight: 700;
      line-height: 12px;
      color: var(--primary-text-color);
      pointer-events: none;
    }
    .val {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: var(--ha-font-size-l, 16px);
    }
    button {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 35px;
      padding: 0;
      border: 0;
      background: none;
      color: inherit;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      -webkit-tap-highlight-color: transparent;
    }
    button.minus {
      left: 0;
    }
    button.plus {
      right: 0;
    }
    button:active {
      background: rgba(127, 127, 127, 0.25);
    }
    button svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }
    input {
      font: inherit;
      color: inherit;
      min-width: 0;
      text-align: center;
      background: none;
      border: 0;
      outline: none;
      padding: 0;
    }
    .deg {
      width: 0.5em;
    }
    :host([disabled]) {
      opacity: 0.5;
      pointer-events: none;
    }
  `,
  ];

  _fmt(v) {
    if (v == null) return "--";
    return Number(v).toLocaleString(this.language || "it", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    });
  }

  _emit(key, value) {
    if (Number.isNaN(value)) return;
    this.dispatchEvent(new CustomEvent("temp-change", { detail: { key, value } }));
  }

  _typed(key, e) {
    const v = parseFloat(String(e.target.value).replace(",", "."));
    e.target.value = this._fmt(this.values?.[key]);
    e.target.style.width = `${Math.max(2, e.target.value.length)}ch`;
    this._emit(key, v);
  }

  render() {
    return html`${TEMP_KEYS.map((key) => {
      const v = this.values?.[key];
      return html`<div class="cell">
        <span class="lbl">${key.toUpperCase()}</span>
        <div class="box">
        <button class="minus" aria-label="-" @click=${() => v != null && this._emit(key, v - ARROW_STEP)}>
          ${MINUS}
        </button>
        <span class="val">
          <input
            inputmode="decimal"
            aria-label=${key.toUpperCase()}
            .value=${this._fmt(v)}
            style="width:${Math.max(2, this._fmt(v).length)}ch"
            @input=${(e) => (e.target.style.width = `${Math.max(2, e.target.value.length)}ch`)}
            @focus=${(e) => e.target.select()}
            @change=${(e) => this._typed(key, e)}
            @keydown=${(e) => e.key === "Enter" && e.target.blur()}
          /><span class="deg">°</span>
        </span>
        <button class="plus" aria-label="+" @click=${() => v != null && this._emit(key, v + ARROW_STEP)}>
          ${PLUS}
        </button>
        </div>
      </div>`;
    })}`;
  }
}
