// Pulsante a riga intera, con icona e testo su una o più righe.
// Usato per "Programmazione Cronotermostato" e per "Salva".
import { LitElement, css, html, nothing } from "lit";
import { featureRowStyles } from "./feature-styles.js";

export class DomoFeatureButton extends LitElement {
  static properties = {
    icon: { type: String },
    lines: { attribute: false },
    center: { type: Boolean },
    disabled: { type: Boolean, reflect: true },
    labelFirst: { type: Boolean, attribute: "label-first" },
  };

  static styles = [
    featureRowStyles,
    css`
      :host([disabled]) {
        opacity: 0.4;
        pointer-events: none;
      }
    `,
  ];

  constructor() {
    super();
    this.lines = [];
    this.center = false;
  }

  render() {
    return html`<button class="row ${this.center ? "center" : ""}">
      ${this.icon ? html`<ha-icon .icon=${this.icon}></ha-icon>` : nothing}
      ${this.lines.length
        ? html`<span class="text" style=${this.center ? "flex:none" : ""}>
            ${this.lines.map(
              (line, i) =>
                html`<span class=${this.labelFirst && i === 0 ? "label" : ""}>${line}</span>`
            )}
          </span>`
        : nothing}
    </button>`;
  }
}

