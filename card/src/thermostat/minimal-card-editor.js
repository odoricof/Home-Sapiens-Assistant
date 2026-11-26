// Editor della card minimal: stessi campi, più l'interruttore per il pulsante Jolly.
import { MINIMAL_EDITOR_TYPE } from "./const.js";
import { DomoThermostatCardEditor } from "./thermostat-card-editor.js";

export class DomoMinimalCardEditor extends DomoThermostatCardEditor {
  get schema() {
    return [
      { name: "entity", required: true, selector: { entity: { domain: ["climate"] } } },
      { name: "name", selector: { text: {} } },
      { name: "theme", selector: { theme: {} } },
      { name: "show_jolly", selector: { boolean: {} } },
    ];
  }

  // show_jolly è attivo se non indicato: l'editor lo mostra acceso di default.
  setConfig(config) {
    super.setConfig({ show_jolly: true, ...config });
  }
}

