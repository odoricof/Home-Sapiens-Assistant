// Replica della card "thermostat" nativa di Home Assistant (hui-thermostat-card.ts).
// Il quadrante circolare è lo stesso componente nativo usato dalla card ufficiale.
// Aggiunte: ghiera gialla con Jolly attivo e, dai tre puntini, la vista estesa
// con modalità Jolly e programmazione cronotermostato (src/dialog).

import { LitElement, html, nothing } from "lit";
import { styleMap } from "lit/directives/style-map.js";

import {
  CARD_TYPE,
  DEFAULT_STEP_MINUTES,
  EDITOR_TYPE,
  MDI_DOTS_VERTICAL,
  STEP_MINUTES,
  SUPPORTED_DOMAINS,
} from "./const.js";
import {
  applyJollyRing,
  applyThemeOnElement,
  computeDomain,
  computeName,
  ensureHaElements,
  entityNotFoundText,
  fireEvent,
  placeStatusIcons,
  stateColorCss,
} from "./ha-helpers.js";
import { isJolly } from "./hvac.js";
import { cardStyles } from "./styles.js";
import "./dialog/more-info-dialog.js";
import { statusFlags } from "./status-icons.js";
import "./status-icons.js";
import "./thermostat-card-editor.js";

export class DomoThermostatCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
    _featureContext: { state: true },
    _controlMaxWidth: { state: true },
    _ready: { state: true },
    _dialogOpen: { state: true },
  };

  static styles = cardStyles;

  static getConfigElement() {
    return document.createElement(EDITOR_TYPE);
  }

  static getStubConfig(hass, entities, entitiesFallback) {
    const pool = [...(entities || []), ...(entitiesFallback || [])];
    const found = pool.find((id) => id.startsWith("climate."));
    const fallback = Object.keys(hass?.states || {}).find((id) =>
      id.startsWith("climate.")
    );
    return { type: `custom:${CARD_TYPE}`, entity: found || fallback || "" };
  }

  constructor() {
    super();
    this._featureContext = {};
    this._ready = false;
    this._dialogOpen = false;
    this._resizeObserver = new ResizeObserver(() => this._measure());
  }

  getCardSize() {
    return 7;
  }

  setConfig(config) {
    if (
      !config ||
      !config.entity ||
      !SUPPORTED_DOMAINS.includes(config.entity.split(".")[0])
    ) {
      throw new Error(
        "Specify an entity from within the climate or water_heater domain"
      );
    }
    const step = Number(config.step_minutes);
    this._config = {
      ...config,
      step_minutes: STEP_MINUTES.includes(step) ? step : DEFAULT_STEP_MINUTES,
    };
    this._featureContext = { entity_id: config.entity };
  }

  getGridOptions() {
    const columns = 12;
    let rows = 5;
    let min_rows = 2;
    const min_columns = 6;
    if (this._config?.features?.length) {
      const featureHeight = Math.ceil((this._config.features.length * 2) / 3);
      rows += featureHeight;
      min_rows += featureHeight;
    }
    return { columns, rows, min_columns, min_rows };
  }

  connectedCallback() {
    super.connectedCallback();
    this._resizeObserver.observe(this);
    if (this._config) {
      ensureHaElements(this._config.entity).then(() => {
        this._ready = true;
      });
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._resizeObserver.disconnect();
    this._dialogOpen = false;
  }

  // Equivalente del ResizeController nativo: limita la larghezza del quadrante
  // all'altezza disponibile nel contenitore.
  _measure() {
    const container = this.shadowRoot?.querySelector(".container");
    const height = container?.clientHeight;
    this._controlMaxWidth = height ? `${height}px` : undefined;
    this._placeOverlays();
  }

  // Ghiera gialla con Jolly attivo e icone di stato dentro la ghiera.
  _placeOverlays() {
    const container = this.shadowRoot?.querySelector(".container");
    const control = container?.querySelector("ha-state-control-climate-temperature");
    if (!control) return;
    const st = this.hass?.states[this._config.entity];
    const apply = () => applyJollyRing(control, !!st && isJolly(st));
    apply();
    control.updateComplete?.then(apply);
    placeStatusIcons(container, control, container.querySelector(".status"));
  }

  // Tre puntini: per i termostati si apre la vista estesa; per lo scaldabagno la finestra standard.
  _handleMoreInfo() {
    if (computeDomain(this._config.entity) === "climate") {
      this._dialogOpen = true;
    } else {
      fireEvent(this, "hass-more-info", { entityId: this._config.entity });
    }
  }

  updated(changedProps) {
    super.updated(changedProps);
    if (!this._config || !this.hass) return;

    if (changedProps.has("_ready") || changedProps.has("_config")) {
      this._measure();
    }
    if (changedProps.has("hass")) this._placeOverlays();
    if (!changedProps.has("hass") && !changedProps.has("_config")) return;

    const oldHass = changedProps.get("hass");
    const oldConfig = changedProps.get("_config");
    if (
      !oldHass ||
      !oldConfig ||
      oldHass.themes !== this.hass.themes ||
      oldConfig.theme !== this._config.theme
    ) {
      applyThemeOnElement(this, this.hass.themes, this._config.theme);
    }
  }

  render() {
    if (!this.hass || !this._config) return nothing;

    const stateObj = this.hass.states[this._config.entity];
    if (!stateObj) {
      return html`<hui-warning>
        ${entityNotFoundText(this.hass, this._config.entity)}
      </hui-warning>`;
    }

    if (!this._ready) {
      ensureHaElements(this._config.entity).then(() => {
        this._ready = true;
      });
    }

    const domain = computeDomain(stateObj.entity_id);
    const name = computeName(this.hass, stateObj, this._config.name);
    const color = stateColorCss(stateObj);
    const maxWidth = this._controlMaxWidth;

    const flags = domain === "climate" ? statusFlags(stateObj) : {};

    return html`
      <ha-card>
        <p class="title">${name}</p>
        <div class="container">
          ${domain === "water_heater"
            ? html`<ha-state-control-water_heater-temperature
                style=${styleMap({ maxWidth })}
                prevent-interaction-on-scroll
                show-current
                .stateObj=${stateObj}
              ></ha-state-control-water_heater-temperature>`
            : html`<ha-state-control-climate-temperature
                style=${styleMap({ maxWidth })}
                prevent-interaction-on-scroll
                .hass=${this.hass}
                .showCurrentAsPrimary=${this._config.show_current_as_primary}
                show-secondary
                .stateObj=${stateObj}
              ></ha-state-control-climate-temperature>`}
          ${domain === "climate"
            ? html`<domo-status-icons
                class="floating status"
                ?window-open=${flags.windowOpen}
                ?absent=${flags.absent}
              ></domo-status-icons>`
            : nothing}
        </div>
        <ha-icon-button
          class="more-info"
          .label=${this.hass.localize("ui.panel.lovelace.cards.show_more_info")}
          .path=${MDI_DOTS_VERTICAL}
          @click=${this._handleMoreInfo}
          tabindex="0"
        ></ha-icon-button>
        ${this._config.features?.length
          ? html`<hui-card-features
              style=${styleMap({ "--feature-color": color })}
              .hass=${this.hass}
              .context=${this._featureContext}
              .features=${this._config.features}
            ></hui-card-features>`
          : nothing}
        ${this._dialogOpen
          ? html`<domo-thermostat-dialog
              .hass=${this.hass}
              entity-id=${this._config.entity}
              step-minutes=${this._config.step_minutes}
              @closed=${() => {
                this._dialogOpen = false;
              }}
            ></domo-thermostat-dialog>`
          : nothing}
      </ha-card>
    `;
  }
}
