// Editor grafico (UI) delle card, basato su ha-form come l'editor nativo.
// La card minimal ne usa una variante con un campo in più (src/minimal-card-editor.js).

import { LitElement, html, nothing } from "lit";
import { EDITOR_TYPE, SUPPORTED_DOMAINS } from "./const.js";
import { fireEvent } from "./ha-helpers.js";
import { t } from "./i18n.js";

export class DomoThermostatCardEditor extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
  };

  // Campi mostrati nell'editor (le varianti li sovrascrivono).
  get schema() {
    return [
      { name: "entity", required: true, selector: { entity: { domain: SUPPORTED_DOMAINS } } },
      { name: "name", selector: { text: {} } },
      { name: "theme", selector: { theme: {} } },
      { name: "show_current_as_primary", selector: { boolean: {} } },
    ];
  }

  setConfig(config) {
    this._config = config;
  }

  _computeLabel = (schema) => {
    if (schema.name === "show_current_as_primary") {
      return this.hass.localize(
        "ui.panel.lovelace.editor.card.thermostat.show_current_as_primary"
      );
    }
    if (schema.name === "show_jolly") return t(this.hass, "showJolly");
    return (
      this.hass.localize(`ui.panel.lovelace.editor.card.generic.${schema.name}`) ||
      schema.name
    );
  };

  _valueChanged(ev) {
    fireEvent(this, "config-changed", { config: ev.detail.value });
  }

  render() {
    if (!this.hass || !this._config) return nothing;
    return html`
      <ha-form
        .hass=${this.hass}
        .data=${this._config}
        .schema=${this.schema}
        .computeLabel=${this._computeLabel}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `;
  }
}

