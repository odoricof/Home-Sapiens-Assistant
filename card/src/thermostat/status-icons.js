// Icone rosse "finestra aperta" e "persona assente": compaiono solo se l'evento è vero.
import { LitElement, css, html, nothing } from "lit";

// Dati letti dagli attributi del termostato (window_open, occupied).
export const statusFlags = (stateObj) => ({
  windowOpen: stateObj?.attributes?.window_open === true,
  absent: stateObj?.attributes?.occupied === false,
});

export class DomoStatusIcons extends LitElement {
  static properties = {
    windowOpen: { type: Boolean, attribute: "window-open" },
    absent: { type: Boolean },
  };

  static styles = css`
    :host {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      color: var(--error-color, #db4437);
      pointer-events: none;
    }
    :host(.floating) {
      position: absolute;
      transform: translate(-50%, -50%);
    }
    :host([hidden]) {
      display: none;
    }
    ha-icon {
      --mdc-icon-size: 24px;
      display: flex;
    }
  `;

  render() {
    this.hidden = !this.windowOpen && !this.absent;
    return html`
      ${this.windowOpen ? html`<ha-icon icon="mdi:window-open-variant"></ha-icon>` : nothing}
      ${this.absent ? html`<ha-icon icon="mdi:motion-sensor-off"></ha-icon>` : nothing}
    `;
  }
}

