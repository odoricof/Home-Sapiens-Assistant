// Card "minimal": replica della tile card nativa con la funzione "modalità del termostato"
// (pulsanti con sola icona), più il pulsante Jolly dopo Automatico e le icone rosse
// di finestra aperta / persona assente. Toccando la card si apre la vista estesa.

import { LitElement, css, html, nothing } from "lit";

import { DEFAULT_STEP_MINUTES, JOLLY_COLOR, HVAC_ICONS, MINIMAL_EDITOR_TYPE, MINIMAL_TYPE, STEP_MINUTES } from "./const.js";
import {
  ACTION_BADGE_ICONS,
  actionColor,
  applyThemeOnElement,
  computeName,
  ensureHaElements,
  entityNotFoundText,
} from "./ha-helpers.js";
import { currentMode, isJolly, modeService, supportsJolly } from "./hvac.js";
import { statusFlags } from "./status-icons.js";
import "./status-icons.js";
import "./dialog/more-info-dialog.js";
import "./minimal-card-editor.js";

// Ordine dei pulsanti come nella card nativa (da spento ad automatico); Jolly per ultimo.
const MODE_ORDER = ["off", "fan_only", "dry", "cool", "heat", "heat_cool", "auto"];

// Colori fissi per modalità: automatico verde, Jolly giallo, riscaldamento arancio,
// raffrescamento blu, spento grigio.
const MODE_COLORS = {
  auto: "var(--state-climate-auto-color, #4caf50)",
  heat_cool: "var(--state-climate-heat_cool-color, #4caf50)",
  heat: "var(--state-climate-heat-color, #ff8100)",
  cool: "var(--state-climate-cool-color, #2b9af9)",
  dry: "var(--state-climate-dry-color, #efbd07)",
  fan_only: "var(--state-climate-fan_only-color, #8ac24a)",
  off: "var(--state-climate-off-color, var(--state-inactive-color, #9e9e9e))",
};

const modeColor = (mode) =>
  mode === "jolly"
    ? JOLLY_COLOR
    : MODE_COLORS[mode] || "var(--state-climate-active-color, var(--state-active-color))";

// Il badge si mostra solo se il termostato è raggiungibile.
const unavailableOrNone = (st) => st.state === "unavailable" || st.state === "unknown";

export class DomoMinimalCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
    _dialogOpen: { state: true },
  };

  static styles = css`
    :host {
      display: block;
    }
    ha-card {
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      height: 100%;
      overflow: hidden;
    }
    .background {
      position: absolute;
      inset: 0;
      cursor: pointer;
      transition: background-color 180ms ease-in-out;
    }
    .background:active {
      background: rgba(var(--rgb-primary-text-color, 127, 127, 127), 0.06);
    }
    .container {
      position: relative;
      display: flex;
      flex-direction: column;
      flex: 1;
      pointer-events: none;
    }
    .content {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px;
      min-width: 0;
      box-sizing: border-box;
    }
    .icon {
      position: relative;
      flex: none;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
    }
    .icon ha-state-icon {
      position: relative;
      --mdc-icon-size: 24px;
      color: var(--tile-color);
      --icon-primary-color: var(--tile-color);
      transition: color 180ms ease-in-out;
    }
    .badge {
      position: absolute;
      top: -3px;
      right: -3px;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background-color: var(--badge-color);
      color: var(--white-color, #fff);
      transition: background-color 180ms ease-in-out;
    }
    .badge ha-icon {
      --mdc-icon-size: 12px;
      display: flex;
    }
    .info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      justify-content: center;
      line-height: var(--ha-line-height-condensed, 1.2);
    }
    .primary,
    .secondary {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: var(--ha-font-size-m, 14px);
    }
    .primary {
      font-weight: var(--ha-font-weight-medium, 500);
      color: var(--primary-text-color);
    }
    .secondary {
      color: var(--secondary-text-color);
    }
    domo-status-icons {
      flex: none;
    }
    .features {
      padding: 0 12px 12px 12px;
      pointer-events: auto;
    }
    .modes {
      position: relative;
      display: flex;
      height: var(--feature-height, 42px);
      border-radius: var(--feature-border-radius, 12px);
      overflow: hidden;
    }
    .modes::before {
      content: "";
      position: absolute;
      inset: 0;
      background: var(--disabled-color);
      opacity: 0.2;
    }
    .modes button {
      position: relative;
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 0;
      padding: 0;
      background: none;
      color: var(--secondary-text-color);
      cursor: pointer;
      border-radius: var(--feature-border-radius, 12px);
      -webkit-tap-highlight-color: transparent;
    }
    .modes button[disabled] {
      cursor: default;
      opacity: 0.5;
    }
    .modes button.sel {
      background: var(--btn-color);
      color: var(--white-color, #fff);
    }
    .modes ha-icon {
      --mdc-icon-size: 24px;
      display: flex;
    }
  `;

  constructor() {
    super();
    this._dialogOpen = false;
  }

  static getConfigElement() {
    return document.createElement(MINIMAL_EDITOR_TYPE);
  }

  static getStubConfig(hass, entities, entitiesFallback) {
    const pool = [...(entities || []), ...(entitiesFallback || [])];
    const found =
      pool.find((id) => id.startsWith("climate.")) ||
      Object.keys(hass?.states || {}).find((id) => id.startsWith("climate."));
    return { type: `custom:${MINIMAL_TYPE}`, entity: found || "" };
  }

  setConfig(config) {
    if (!config || !config.entity || !config.entity.startsWith("climate.")) {
      throw new Error("Specify an entity from within the climate domain");
    }
    const step = Number(config.step_minutes);
    this._config = {
      ...config,
      show_jolly: config.show_jolly !== false,
      step_minutes: STEP_MINUTES.includes(step) ? step : DEFAULT_STEP_MINUTES,
    };
  }

  getCardSize() {
    return 2;
  }

  getGridOptions() {
    return { columns: 6, rows: 2, min_columns: 3, min_rows: 2 };
  }

  connectedCallback() {
    super.connectedCallback();
    if (this._config) ensureHaElements(this._config.entity);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._dialogOpen = false;
  }

  updated(changed) {
    if (!this._config || !this.hass) return;
    if (changed.has("hass") || changed.has("_config")) {
      const old = changed.get("hass");
      const oldCfg = changed.get("_config");
      if (!old || !oldCfg || old.themes !== this.hass.themes || oldCfg.theme !== this._config.theme) {
        applyThemeOnElement(this, this.hass.themes, this._config.theme);
      }
    }
  }

  _modes(st) {
    const rank = (m) => {
      const i = MODE_ORDER.indexOf(m);
      return i === -1 ? -1 : i;
    };
    const modes = [...(st.attributes.hvac_modes || [])].sort((a, b) => rank(a) - rank(b));
    if (this._config.show_jolly && supportsJolly(st)) modes.push("jolly");
    return modes;
  }

  _pick(mode) {
    this.hass.callService(...modeService(this._config.entity, mode)).catch((err) => {
      this.dispatchEvent(
        new CustomEvent("hass-notification", {
          detail: { message: (err && err.message) || String(err) },
          bubbles: true,
          composed: true,
        })
      );
    });
  }

  _secondary(st) {
    const h = this.hass;
    const action = st.attributes.hvac_action
      ? h.formatEntityAttributeValue?.(st, "hvac_action")
      : null;
    const state = action || h.formatEntityState?.(st) || st.state;
    const temp =
      st.attributes.current_temperature != null
        ? h.formatEntityAttributeValue?.(st, "current_temperature")
        : null;
    return [state, temp].filter(Boolean).join(" · ");
  }

  render() {
    if (!this.hass || !this._config) return nothing;
    const st = this.hass.states[this._config.entity];
    if (!st) {
      return html`<hui-warning>${entityNotFoundText(this.hass, this._config.entity)}</hui-warning>`;
    }
    const flags = statusFlags(st);
    const action = st.attributes.hvac_action;
    const badgeIcon = unavailableOrNone(st) ? null : ACTION_BADGE_ICONS[action];
    const current = currentMode(st);
    const unavailable = st.state === "unavailable";
    // L'icona ha il colore della modalità impostata (Jolly giallo).
    const color = unavailable
      ? "var(--state-unavailable-color)"
      : modeColor(current);

    return html`
      <ha-card style="--tile-color: ${color}">
        <div
          class="background"
          role="button"
          tabindex="0"
          @click=${() => (this._dialogOpen = true)}
          @keydown=${(ev) => {
            if (ev.key === "Enter" || ev.key === " ") this._dialogOpen = true;
          }}
        ></div>
        <div class="container">
          <div class="content">
            <div class="icon">
              <ha-state-icon .hass=${this.hass} .stateObj=${st}></ha-state-icon>
              ${badgeIcon
                ? html`<div class="badge" style="--badge-color: ${actionColor(action)}">
                    <ha-icon .icon=${badgeIcon}></ha-icon>
                  </div>`
                : nothing}
            </div>
            <div class="info">
              <span class="primary">${computeName(this.hass, st, this._config.name)}</span>
              <span class="secondary">${this._secondary(st)}</span>
            </div>
            <domo-status-icons
              ?window-open=${flags.windowOpen}
              ?absent=${flags.absent}
            ></domo-status-icons>
          </div>
          <div class="features">
            <div class="modes">
              ${this._modes(st).map(
                (mode) => html`<button
                  class=${mode === current ? "sel" : ""}
                  style="--btn-color: ${modeColor(mode)}"
                  ?disabled=${unavailable}
                  aria-label=${mode}
                  @click=${() => this._pick(mode)}
                >
                  <ha-icon .icon=${HVAC_ICONS[mode] || "mdi:thermostat"}></ha-icon>
                </button>`
              )}
            </div>
          </div>
        </div>
        ${this._dialogOpen
          ? html`<domo-thermostat-dialog
              .hass=${this.hass}
              entity-id=${this._config.entity}
              step-minutes=${this._config.step_minutes}
              @closed=${() => (this._dialogOpen = false)}
            ></domo-thermostat-dialog>`
          : nothing}
      </ha-card>
    `;
  }
}
