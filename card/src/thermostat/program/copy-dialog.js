// Finestra "Copia su": sceglie i giorni su cui copiare il programma mostrato.
import { LitElement, css, html } from "lit";
import { DAYS } from "../const.js";
import { t } from "../i18n.js";

export class DomoCopyDialog extends LitElement {
  static properties = {
    hass: { attribute: false },
    day: { type: String },
    _selected: { state: true },
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
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
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
      flex: 0 0 calc((100% - 30px) / 4);
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
      gap: 12px;
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

  constructor() {
    super();
    this._selected = new Set();
  }

  _toggle(day) {
    const next = new Set(this._selected);
    if (next.has(day)) next.delete(day);
    else next.add(day);
    this._selected = next;
  }

  _fire(name, detail) {
    this.dispatchEvent(new CustomEvent(name, { detail }));
  }

  render() {
    return html`<div class="panel">
      <div class="title">${t(this.hass, "copyTitle").replace("{day}", t(this.hass, this.day))}</div>
      <div class="chips">
        ${DAYS.filter((d) => d !== this.day).map(
          (d) => html`<button
            class="chip ${this._selected.has(d) ? "on" : ""}"
            @click=${() => this._toggle(d)}
          >
            ${t(this.hass, d)}
          </button>`
        )}
      </div>
      <div class="btns">
        <button class="no" @click=${() => this._fire("cancel")}>${t(this.hass, "cancel")}</button>
        <button class="ok" @click=${() => this._fire("apply", [...this._selected])}>
          ${t(this.hass, "apply")}
        </button>
      </div>
    </div>`;
  }
}

