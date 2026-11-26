// Finestra "Seleziona il giorno": si apre al centro della scheda, nello stesso stile di "Copia su".
// Si sceglie un solo giorno (compreso Jolly): toccandolo la finestra si chiude e il giorno cambia.
import { LitElement, css, html } from "lit";
import { DAYS } from "../const.js";
import { t } from "../i18n.js";

export class DomoDayDialog extends LitElement {
  static properties = {
    hass: { attribute: false },
    day: { type: String },
  };

  static styles = css`
    :host {
      position: absolute;
      inset: 0;
      z-index: 30;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.55);
      border-radius: var(--ha-card-border-radius, 12px);
    }
    .panel {
      width: 86%;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      border-radius: 16px;
      padding: 20px;
      box-sizing: border-box;
    }
    .title {
      font-size: 1.15rem;
      font-weight: 600;
      text-align: center;
      margin-bottom: 16px;
    }
    .chips {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
    }
    button {
      font: inherit;
      color: inherit;
      background: none;
      border: 0;
      cursor: pointer;
    }
    .chip {
      min-width: 0;
      padding: 9px 4px;
      border-radius: 24px;
      border: 2px solid transparent;
      background: var(--secondary-background-color, rgba(127, 127, 127, 0.2));
      font-weight: 700;
      text-align: center;
    }
    .chip.on {
      color: var(--primary-color);
      background-image: linear-gradient(rgba(var(--rgb-primary-color, 3, 169, 244), 0.14), rgba(var(--rgb-primary-color, 3, 169, 244), 0.14));
    }
    .btns {
      display: flex;
      margin-top: 20px;
    }
    .btns button {
      flex: 1;
      padding: 11px;
      border-radius: 24px;
      font-weight: 700;
      color: var(--primary-color);
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.14);
    }
  `;

  _fire(name, detail) {
    this.dispatchEvent(new CustomEvent(name, { detail }));
  }

  render() {
    return html`<div class="panel">
      <div class="title">${t(this.hass, "dayTitle")}</div>
      <div class="chips">
        ${DAYS.map(
          (d) => html`<button class="chip ${d === this.day ? "on" : ""}" @click=${() => this._fire("select", d)}>
            ${t(this.hass, d)}
          </button>`
        )}
      </div>
      <div class="btns">
        <button @click=${() => this._fire("cancel")}>${t(this.hass, "cancel")}</button>
      </div>
    </div>`;
  }
}
