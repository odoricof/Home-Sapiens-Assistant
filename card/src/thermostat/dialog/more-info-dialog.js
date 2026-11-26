// Vista estesa (si apre dai tre puntini): riproduce la finestra "more info" del termostato
// con il quadrante nativo, i menu Modalità / Ventilatore e, al posto di "Preimpostato",
// il pulsante "Programmazione Cronotermostato" che apre il quadrante del programma.
import { LitElement, css, html, nothing } from "lit";
import { DAYS, FAN_ICONS } from "../const.js";
import { applyJollyRing, computeName, fireEvent, placeStatusIcons } from "../ha-helpers.js";
import { currentMode, isJolly, isSummer, modeOptions, modeService } from "../hvac.js";
import { fanLabel, t } from "../i18n.js";
import { isValidProfile } from "../program/geometry.js";
import "../features/feature-button.js";
import "../features/feature-select.js";
import { statusFlags } from "../status-icons.js";
import "../status-icons.js";
import "../program/copy-dialog.js";
import "../program/program-dial.js";
import "../program/hour-zoom.js";
import "../program/temp-fields.js";
import { TEMP_KEYS, clampTemp, findTempEntities, limitsOf, readTemps, writeOrder } from "../program/temps.js";

// La ventola si mostra solo con Auto, Jolly o Manuale (riscaldamento/raffrescamento), non da spento.
const FAN_MODES = ["auto", "jolly", "heat", "cool"];

const cap = (s) => String(s).charAt(0).toUpperCase() + String(s).slice(1).replace(/_/g, " ");

// Rapporto tra il bordo esterno della ghiera e quello del quadrante crono, calcolato dai sorgenti:
// - ghiera nativa di Home Assistant: raggio 145 + mezzo spessore 12 = 157 su 160 -> 0,98125 della larghezza;
// - quadrante crono: cerchio esterno a 472 + mezza linea 0,6 su 540 -> 0,87519 della sua misura.
const DIAL_SCALE = 0.98125 / 0.87519; // = 1,121

export class DomoThermostatDialog extends LitElement {
  static properties = {
    hass: { attribute: false },
    entityId: { type: String, attribute: "entity-id" },
    stepMinutes: { type: Number, attribute: "step-minutes" },
    _program: { state: true },
    _zoom: { state: true },
    _zoomHour: { state: true },
    _temps: { state: true },
    _day: { state: true },
    _drafts: { state: true },
    _copyOpen: { state: true },
    _dayOpen: { state: true },
    _saving: { state: true },
  };

  static styles = css`
    :host {
      display: contents;
      --feature-height: 48px;
      --feature-border-radius: 12px;
    }
    dialog {
      width: min(580px, 100vw);
      max-width: 100vw;
      max-height: 100vh;
      margin: auto;
      padding: 0;
      border: 0;
      overflow: auto;
      color: var(--primary-text-color);
      background: var(--ha-dialog-surface-background, var(--mdc-theme-surface, var(--card-background-color, #fff)));
      border-radius: var(--ha-dialog-border-radius, 28px);
      box-shadow: var(--ha-dialog-box-shadow, 0 8px 32px rgba(0, 0, 0, 0.4));
      font-family: var(--ha-font-family-body, Roboto, Noto, sans-serif);
    }
    dialog::backdrop {
      background: var(--ha-dialog-scrim-color, rgba(0, 0, 0, 0.32));
      backdrop-filter: var(--dialog-backdrop-filter, none);
    }
    .surface {
      position: relative;
      display: flex;
      flex-direction: column;
      border-radius: inherit;
      overflow: hidden;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 12px 12px 0 12px;
      min-height: 64px;
      box-sizing: border-box;
    }
    .titles {
      flex: 1;
      min-width: 0;
      margin-inline-start: 12px;
      line-height: 1.2;
    }
    .area {
      font-size: var(--ha-font-size-m, 14px);
      color: var(--secondary-text-color);
    }
    .name {
      font-size: var(--ha-font-size-xl, 20px);
      font-weight: var(--ha-font-weight-medium, 500);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    ha-icon-button {
      --mdc-icon-button-size: 48px;
      color: var(--secondary-text-color);
    }
    ha-icon-button.close {
      color: var(--primary-text-color);
    }
    .top {
      display: flex;
      align-items: center;
      justify-content: center;
      margin-top: 24px;
      height: calc((var(--ha-font-size-l, 16px) + var(--ha-font-size-xl, 20px)) * 1.25);
    }
    .stats {
      display: flex;
      justify-content: center;
      gap: 48px;
      text-align: center;
      line-height: 1.25;
    }
    .stats .l {
      font-size: var(--ha-font-size-l, 16px);
      color: var(--secondary-text-color);
    }
    .stats .v {
      font-size: var(--ha-font-size-xl, 20px);
      font-weight: var(--ha-font-weight-medium, 500);
    }
    .dial-area {
      position: relative;
      display: flex;
      justify-content: center;
      margin-top: 8px;
    }
    .control {
      display: block;
      width: 100%;
      max-width: 344px;
      padding: 8px;
      box-sizing: border-box;
    }
    .control.hidden {
      visibility: hidden;
    }
    .dial-area > .program {
      position: absolute;
      display: flex;
      align-items: center;
      justify-content: center;
      box-sizing: border-box;
    }
    /* Il quadrante può essere più grande del riquadro: niente restringimento automatico. */
    .dial-area > .program > * {
      flex: none;
    }
    .chips-area {
      position: relative;
      padding: 8px 24px 24px 24px;
    }
    .chips {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: 1fr;
      justify-content: center;
      gap: 12px;
      width: max-content;
      max-width: 100%;
      margin: 0 auto;
    }
    .chips > * {
      width: auto;
      min-width: 0;
    }
    .dial-area > .status {
      position: absolute;
      padding: 0;
    }
    .chips-area.program .chips {
      visibility: hidden;
    }
    .save-slot {
      position: absolute;
      inset: 8px 24px 24px 24px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .save-slot {
      gap: 12px;
    }
    .save-slot domo-feature-button.lens {
      width: var(--feature-height, 48px);
      min-width: var(--feature-height, 48px);
    }
  `;

  constructor() {
    super();
    this.stepMinutes = 60;
    this._program = false;
    this._zoom = false;
    this._zoomHour = 0;
    this._temps = {};
    this._day = null;
    this._drafts = {};
    this._copyOpen = false;
    this._dayOpen = false;
    this._saving = false;
    this._resizeObserver = new ResizeObserver(() => this._placeProgramDial());
  }

  get _stateObj() {
    return this.hass?.states[this.entityId];
  }

  firstUpdated() {
    this.renderRoot.querySelector("dialog").showModal();
    this._resizeObserver.observe(this.renderRoot.querySelector("dialog"));
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._resizeObserver.disconnect();
  }

  updated(changed) {
    if (changed.has("_program") || changed.has("_zoom") || changed.has("hass") || changed.has("_day")) {
      this._placeProgramDial();
    }
  }

  // ---- posizione del quadrante del programma: stessa del controllo nativo ----
  _placeProgramDial() {
    const area = this.renderRoot?.querySelector(".dial-area");
    const control = area?.querySelector(".control");
    if (!control) return;
    const st = this._stateObj;
    const apply = () => applyJollyRing(control, !!st && isJolly(st));
    apply();
    control.updateComplete?.then(apply);
    placeStatusIcons(area, control, area.querySelector(".status"));
    const overlay = area.querySelector(".program");
    if (!overlay) return;
    const a = area.getBoundingClientRect();
    const r = control.getBoundingClientRect();
    overlay.style.left = `${r.left - a.left}px`;
    overlay.style.top = `${r.top - a.top}px`;
    overlay.style.width = `${r.width}px`;
    overlay.style.height = `${r.height}px`;
    const size = Math.max(0, Math.min(r.width, r.height) - 16);
    const child = overlay.firstElementChild;
    // Il quadrante crono è ingrandito (DIAL_SCALE) perché il suo bordo esterno coincida con
    // quello della ghiera del termostato; lo zoom orario resta della misura di prima.
    const scale = child?.localName === "domo-program-dial" ? DIAL_SCALE : 1;
    child?.style.setProperty("--dial-size", `${size * scale}px`);
  }

  // ---- azioni ----
  _close() {
    this.renderRoot.querySelector("dialog")?.close();
  }

  _onClosed() {
    this.dispatchEvent(new CustomEvent("closed"));
  }

  _backdrop(ev) {
    if (ev.target === ev.currentTarget) this._close();
  }

  // Storico, impostazioni e menu: si passa alla finestra standard di Home Assistant.
  _native(view) {
    this._close();
    fireEvent(this, "hass-more-info", { entityId: this.entityId, ...(view ? { view } : {}) });
  }

  // Tre puntini: apre la pagina "informazioni sul dispositivo" (se il dispositivo non c'è,
  // ripiega sulla finestra standard).
  _deviceInfo() {
    const deviceId = this.hass.entities?.[this.entityId]?.device_id;
    if (!deviceId) {
      this._native();
      return;
    }
    this._close();
    history.pushState(null, "", `/config/devices/device/${deviceId}`);
    fireEvent(window, "location-changed", { replace: false });
  }

  _toast(err) {
    fireEvent(this, "hass-notification", { message: (err && err.message) || String(err) });
  }

  _call(domain, service, data) {
    return this.hass.callService(domain, service, data).catch((err) => this._toast(err));
  }

  _todayKey() {
    return DAYS[(new Date().getDay() + 6) % 7];
  }

  _openProgram() {
    const st = this._stateObj;
    this._day = st && isJolly(st) ? "jolly" : this._todayKey();
    this._drafts = {};
    this._copyOpen = false;
    this._dayOpen = false;
    this._zoom = false;
    this._temps = {};
    this._program = true;
  }

  // Lente: spicchio ingrandito dell'ora attuale (le modifiche restano in bozza fino a Salva).
  _openZoom() {
    this._zoomHour = new Date().getHours();
    this._zoom = true;
  }

  // Bozza dei valori T1/T2/T3 (stessa regola di number.py: T1 < T2 < T3).
  _tempEntities() {
    return findTempEntities(this.hass, this.entityId);
  }

  _tempValues(entities) {
    const saved = readTemps(this.hass, entities);
    const out = {};
    TEMP_KEYS.forEach((k) => {
      out[k] = this._temps[k] ?? saved[k];
    });
    return out;
  }

  _tempChanged(ev) {
    const entities = this._tempEntities();
    if (!entities) return;
    const { key, value } = ev.detail;
    const next = clampTemp(key, value, this._tempValues(entities), limitsOf(this.hass, entities[key]));
    this._temps = { ...this._temps, [key]: next };
  }

  _profileOf(day) {
    const p = this._drafts[day] ?? this._stateObj?.attributes.profile_by_day?.[day];
    return isValidProfile(p) ? p : null;
  }

  _applyCopy(ev) {
    const src = this._profileOf(this._day);
    this._copyOpen = false;
    this._dayOpen = false;
    if (!src) return;
    const next = { ...this._drafts };
    ev.detail.forEach((day) => {
      next[day] = src;
    });
    this._drafts = next;
  }

  // Stagione per i colori del programma: "summer" (azzurro) o "winter" (arancione).
  _season() {
    return this._stateObj && isSummer(this._stateObj) ? "summer" : "winter";
  }

  // Ci sono modifiche non salvate? (giorni cambiati o temperature T1/T2/T3 diverse da quelle attuali)
  _isDirty() {
    const saved = this._stateObj?.attributes.profile_by_day || {};
    if (Object.entries(this._drafts).some(([day, profile]) => profile !== saved[day])) return true;
    const entities = this._tempEntities();
    if (!entities) return false;
    const current = readTemps(this.hass, entities);
    return Object.entries(this._temps).some(([key, value]) => value !== current[key]);
  }

  // Chiude la vista del programma scartando le bozze.
  _closeProgram() {
    this._drafts = {};
    this._temps = {};
    this._copyOpen = false;
    this._dayOpen = false;
    this._zoom = false;
    this._program = false;
  }

  // Salva davvero: scrive nel termostato ogni giorno modificato, poi torna alla vista normale.
  async _save() {
    if (this._saving) return;
    this._saving = true;
    const saved = this._stateObj?.attributes.profile_by_day || {};
    for (const [day, profile] of Object.entries(this._drafts)) {
      if (profile === saved[day]) continue;
      try {
        await this.hass.callService("domo", "set_thermal_profile", {
          entity_id: this.entityId,
          day,
          profile,
        });
      } catch (err) {
        this._toast(err);
        this._saving = false;
        return; // resta in modifica: i giorni non salvati non vanno persi
      }
      const { [day]: _done, ...rest } = this._drafts;
      this._drafts = rest;
    }
    this._drafts = {};
    const entities = this._tempEntities();
    if (entities && Object.keys(this._temps).length) {
      const saved = readTemps(this.hass, entities);
      for (const key of writeOrder(this._temps, saved)) {
        if (this._temps[key] === saved[key]) continue;
        try {
          await this.hass.callService("number", "set_value", {
            entity_id: entities[key],
            value: this._temps[key],
          });
        } catch (err) {
          this._toast(err);
          this._saving = false;
          return;
        }
      }
    }
    this._temps = {};
    this._copyOpen = false;
    this._dayOpen = false;
    this._zoom = false;
    this._program = false;
    this._saving = false;
  }

  // ---- pezzi della vista ----
  _areaName() {
    const h = this.hass;
    const ent = h.entities?.[this.entityId];
    if (!ent) return null;
    const aid = ent.area_id || (ent.device_id && h.devices?.[ent.device_id]?.area_id);
    return (aid && h.areas?.[aid]?.name) || null;
  }

  _statsHtml(st) {
    const a = st.attributes;
    const unit = this.hass.config?.unit_system?.temperature || "°C";
    const fmt = (v, d) =>
      Number(v).toLocaleString(this.hass.language || "it", {
        minimumFractionDigits: d,
        maximumFractionDigits: d,
      });
    const temp = a.current_temperature;
    const hum = a.current_humidity;
    return html`<div class="stats">
      <div>
        <div class="l">${this.hass.formatEntityAttributeName?.(st, "current_temperature") || t(this.hass, "curTemp")}</div>
        <div class="v">${temp != null ? `${fmt(temp, 1)} ${unit}` : "--"}</div>
      </div>
      ${hum != null
        ? html`<div>
            <div class="l">${this.hass.formatEntityAttributeName?.(st, "current_humidity") || t(this.hass, "curHum")}</div>
            <div class="v">${Math.round(hum)}%</div>
          </div>`
        : nothing}
    </div>`;
  }

  _listSelect(st, attr, services, iconFor, labelKey, serviceKey, flags = {}) {
    const values = st.attributes[`${attr}s`] || [];
    if (!values.length) return nothing;
    const options = values.map((value) => ({
      value,
      label:
        (attr === "fan_mode" && fanLabel(this.hass, value)) ||
        this.hass.formatEntityAttributeValue?.(st, attr, value) ||
        cap(value),
      icon: iconFor(value),
    }));
    return html`<domo-feature-select
      ?compact=${flags.compact}
      ?icon-only=${flags.iconOnly}
      .caption=${flags.caption}
      .label=${this.hass.localize(labelKey)}
      .options=${options}
      .value=${st.attributes[attr]}
      ?disabled=${st.state === "unavailable"}
      @selected=${(ev) =>
        this._call("climate", services, {
          entity_id: this.entityId,
          [serviceKey]: ev.detail.value,
        })}
    ></domo-feature-select>`;
  }

  _programDial() {
    const profile = this._profileOf(this._day);
    const change = (ev) => {
      this._drafts = { ...this._drafts, [this._day]: ev.detail.profile };
    };
    if (this._zoom) {
      return html`<div class="program">
        <domo-hour-zoom
          season=${this._season()}
          .profile=${profile || ""}
          .hour=${this._zoomHour}
          day-label=${t(this.hass, this._day)}
          hour-label=${t(this.hass, "hour")}
          @profile-change=${change}
          @hour-change=${(ev) => {
            this._zoomHour = ev.detail.hour;
          }}
        ></domo-hour-zoom>
      </div>`;
    }
    return html`<div class="program">
      <domo-program-dial
        season=${this._season()}
        .profile=${profile || ""}
        .highlightHour=${this._day === this._todayKey() ? new Date().getHours() : -1}
        step-minutes=${this.stepMinutes}
        day-label=${t(this.hass, this._day)}
        .warning=${profile ? "" : t(this.hass, "missing")}
        ?locked=${!profile}
        @profile-change=${(ev) => {
          this._drafts = { ...this._drafts, [this._day]: ev.detail.profile };
        }}
        @day-open=${() => {
          this._dayOpen = true;
        }}
      ></domo-program-dial>
    </div>`;
  }

  render() {
    const st = this._stateObj;
    if (!this.hass || !st) return html`<dialog @close=${this._onClosed}></dialog>`;

    const flags = statusFlags(st);
    const area = this._areaName();
    const name = computeName(this.hass, st, undefined);

    return html`
      <dialog @close=${this._onClosed} @click=${this._backdrop}>
        <div class="surface">
          <div class="header">
            <ha-icon-button class="close" .label=${t(this.hass, "close")} @click=${this._close}>
              <ha-icon icon="mdi:close"></ha-icon>
            </ha-icon-button>
            <div class="titles">
              ${area ? html`<div class="area">${area}</div>` : nothing}
              <div class="name">${name}</div>
            </div>
            <ha-icon-button .label=${t(this.hass, "history")} @click=${() => this._native("history")}>
              <ha-icon icon="mdi:chart-box-outline"></ha-icon>
            </ha-icon-button>
            <ha-icon-button .label=${t(this.hass, "settings")} @click=${() => this._native("settings")}>
              <ha-icon icon="mdi:cog-outline"></ha-icon>
            </ha-icon-button>
            <ha-icon-button .label=${t(this.hass, "more")} @click=${this._deviceInfo}>
              <ha-icon icon="mdi:dots-vertical"></ha-icon>
            </ha-icon-button>
          </div>

          <div class="top">
            ${this._program && this._tempEntities()
              ? html`<domo-temp-fields
                  season=${this._season()}
                  .language=${this.hass.language}
                  .values=${this._tempValues(this._tempEntities())}
                  ?disabled=${this._saving}
                  @temp-change=${this._tempChanged}
                ></domo-temp-fields>`
              : this._statsHtml(st)}
          </div>

          <div class="dial-area">
            <ha-state-control-climate-temperature
              class="control ${this._program ? "hidden" : ""}"
              prevent-interaction-on-scroll
              .hass=${this.hass}
              .stateObj=${st}
            ></ha-state-control-climate-temperature>
            ${this._program
              ? this._programDial()
              : html`<domo-status-icons
                  class="floating status"
                  ?window-open=${flags.windowOpen}
                  ?absent=${flags.absent}
                ></domo-status-icons>`}
          </div>

          <div class="chips-area ${this._program ? "program" : ""}">
            <div class="chips">
              <domo-feature-select
                compact
                .label=${this.hass.localize("ui.card.climate.operation")}
                .options=${modeOptions(this.hass, st, undefined, true)}
                .value=${currentMode(st)}
                ?disabled=${st.state === "unavailable"}
                @selected=${(ev) => this._call(...modeService(this.entityId, ev.detail.value))}
              ></domo-feature-select>
              <domo-feature-button
                center
                icon="mdi:clock-outline"
                .lines=${[t(this.hass, "program")]}
                @click=${this._openProgram}
              ></domo-feature-button>
              ${FAN_MODES.includes(currentMode(st))
                ? this._listSelect(st, "fan_mode", "set_fan_mode",
                    (v) => FAN_ICONS[v] || "mdi:fan",
                    "ui.card.climate.fan_mode", "fan_mode", { compact: true, caption: t(this.hass, "fan") })
                : nothing}
              ${this._listSelect(st, "swing_mode", "set_swing_mode",
                () => "mdi:arrow-oscillating",
                "ui.card.climate.swing_mode", "swing_mode", { compact: true })}
            </div>
            ${this._program
              ? html`<div class="save-slot">
                  ${this._zoom
                    ? html`<domo-feature-button
                        class="lens"
                        center
                        icon="mdi:magnify-minus-outline"
                        aria-label=${t(this.hass, "close")}
                        .lines=${[]}
                        @click=${() => {
                          this._zoom = false;
                        }}
                      ></domo-feature-button>`
                    : html`<domo-feature-button
                          class="lens"
                          center
                          icon="mdi:magnify-plus-outline"
                          aria-label=${t(this.hass, "zoomIn")}
                          .lines=${[]}
                          @click=${this._openZoom}
                        ></domo-feature-button>
                        <domo-feature-button
                          class="lens"
                          center
                          icon="mdi:content-copy"
                          aria-label=${t(this.hass, "copy")}
                          ?disabled=${!this._profileOf(this._day)}
                          .lines=${[]}
                          @click=${() => {
                            this._copyOpen = true;
                          }}
                        ></domo-feature-button>
                        ${this._isDirty()
                          ? html`<domo-feature-button
                                class="lens"
                                center
                                icon="mdi:check"
                                aria-label=${t(this.hass, "saveClose")}
                                .lines=${[]}
                                @click=${this._save}
                              ></domo-feature-button>
                              <domo-feature-button
                                class="lens"
                                center
                                icon="mdi:close"
                                aria-label=${t(this.hass, "closeNoSave")}
                                .lines=${[]}
                                @click=${this._closeProgram}
                              ></domo-feature-button>`
                          : html`<domo-feature-button
                              class="lens"
                              center
                              icon="mdi:close"
                              aria-label=${t(this.hass, "close")}
                              .lines=${[]}
                              @click=${this._closeProgram}
                            ></domo-feature-button>`}`}
                </div>`
              : nothing}
          </div>

          ${this._program && !this._zoom && this._dayOpen
            ? html`<domo-day-dialog
                .hass=${this.hass}
                .day=${this._day}
                @cancel=${() => (this._dayOpen = false)}
                @select=${(ev) => {
                  this._day = ev.detail;
                  this._dayOpen = false;
                }}
              ></domo-day-dialog>`
            : nothing}
          ${this._program && !this._zoom && this._copyOpen
            ? html`<domo-copy-dialog
                .hass=${this.hass}
                .day=${this._day}
                @cancel=${() => (this._copyOpen = false)}
                @apply=${this._applyCopy}
              ></domo-copy-dialog>`
            : nothing}
        </div>
      </dialog>
    `;
  }
}

