// Menu a tendina a riga intera (etichetta piccola + valore, icona e freccia),
// con elenco in un popup che non viene tagliato dalla card.
import { LitElement, css, html, nothing } from "lit";
import { featureRowStyles } from "./feature-styles.js";

export class DomoFeatureSelect extends LitElement {
  static properties = {
    label: { type: String },
    options: { attribute: false },
    value: { type: String },
    disabled: { type: Boolean },
    compact: { type: Boolean },
    caption: { type: String },
    iconOnly: { type: Boolean, attribute: "icon-only" },
  };

  static styles = [
    featureRowStyles,
    css`
      .arrow {
        margin-inline-start: auto;
      }
      .menu {
        position: fixed;
        inset: auto;
        margin: 0;
        padding: 6px;
        border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.4));
        border-radius: var(--feature-border-radius, 12px);
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
        box-shadow: var(--ha-card-box-shadow, 0 6px 24px rgba(0, 0, 0, 0.35));
        max-height: 60vh;
        overflow: auto;
      }
      .menu:popover-open {
        display: flex;
        flex-direction: column;
      }
      .opt {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        border-radius: 8px;
        background: none;
        color: var(--primary-text-color);
        font-size: var(--ha-font-size-m, 14px);
        text-align: start;
      }
      .opt:hover {
        background: rgba(var(--rgb-primary-text-color, 127, 127, 127), 0.06);
      }
      .opt.sel {
        color: var(--primary-color);
        background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.14);
      }
      .opt.sel ha-icon {
        color: var(--primary-color);
      }
    `,
  ];

  constructor() {
    super();
    this.options = [];
  }

  get _current() {
    return this.options.find((o) => o.value === this.value);
  }

  _open() {
    if (this.disabled) return;
    const row = this.renderRoot.querySelector(".row");
    const menu = this.renderRoot.querySelector(".menu");
    const r = row.getBoundingClientRect();
    menu.style.minWidth = `${r.width}px`;
    menu.style.left = `${r.left}px`;
    menu.showPopover();
    const h = menu.offsetHeight;
    const below = window.innerHeight - r.bottom;
    menu.style.top =
      below < h + 8 && r.top > h + 8 ? `${r.top - h - 4}px` : `${r.bottom + 4}px`;
  }

  _pick(value) {
    this.renderRoot.querySelector(".menu").hidePopover();
    if (value !== this.value) {
      this.dispatchEvent(new CustomEvent("selected", { detail: { value } }));
    }
  }

  render() {
    const current = this._current;
    const text = this.caption ?? current?.label ?? this.value ?? "";
    return html`
      <button
        class="row ${this.compact ? "center" : ""}"
        ?disabled=${this.disabled}
        aria-label=${this.label}
        @click=${this._open}
      >
        <ha-icon .icon=${current?.icon || "mdi:thermostat"}></ha-icon>
        ${this.iconOnly
          ? nothing
          : html`<span class="text">
              ${this.compact ? nothing : html`<span class="label">${this.label}</span>`}
              <span>${text}</span>
            </span>`}
        ${this.compact ? nothing : html`<ha-icon class="arrow" icon="mdi:menu-down"></ha-icon>`}
      </button>
      <div class="menu" popover="auto">
        ${this.options.map(
          (o) => html`<button
            class="opt ${o.value === this.value ? "sel" : ""}"
            @click=${() => this._pick(o.value)}
          >
            <ha-icon .icon=${o.icon}></ha-icon><span>${o.label}</span>
          </button>`
        )}
      </div>
    `;
  }
}

