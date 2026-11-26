// Stili copiati dalla card nativa (hui-thermostat-card.ts).
// Le variabili --ha-* hanno un valore di riserva per versioni di HA che non le definiscono.
import { css } from "lit";

export const cardStyles = css`
  :host {
    position: relative;
    display: block;
    height: 100%;
  }
  ha-card {
    position: relative;
    height: 100%;
    width: 100%;
    padding: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
  }

  .title {
    width: 100%;
    font-size: var(--ha-font-size-l, 16px);
    line-height: var(--ha-line-height-expanded, 1.5);
    padding: 8px 30px 8px 30px;
    margin: 0;
    text-align: center;
    box-sizing: border-box;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: none;
  }

  .container {
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    max-width: 100%;
    box-sizing: border-box;
    flex: 1;
  }

  .container:before {
    content: "";
    display: block;
    padding-top: 100%;
  }

  .container > * {
    padding: 8px;
  }

  .container > .status {
    position: absolute;
    padding: 0;
  }

  .more-info {
    position: absolute;
    cursor: pointer;
    top: 0;
    right: 0;
    inset-inline-end: 0px;
    inset-inline-start: initial;
    border-radius: var(--ha-border-radius-pill, 9999px);
    color: var(--secondary-text-color);
    direction: var(--direction);
  }

  hui-card-features {
    width: 100%;
    flex: none;
    padding: 0 12px 12px 12px;
  }
`;
