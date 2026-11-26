// Stile comune delle righe sotto il quadrante (menu a tendina e pulsanti).
// Altezza e raggio seguono le variabili del frontend (--feature-height, --feature-border-radius).
import { css } from "lit";

export const featureRowStyles = css`
  :host {
    display: block;
    width: 100%;
  }
  button {
    font: inherit;
    color: inherit;
    border: 0;
    padding: 0;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .row {
    position: relative;
    display: flex;
    align-items: center;
    gap: 12px;
    box-sizing: border-box;
    width: 100%;
    height: var(--feature-height, 42px);
    padding: 0 12px;
    border-radius: var(--feature-border-radius, 12px);
    background: none;
    overflow: hidden;
    text-align: start;
    color: var(--primary-text-color);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .row::before {
    content: "";
    position: absolute;
    inset: 0;
    background: var(--disabled-color);
    opacity: 0.2;
    transition: opacity 180ms ease-in-out;
  }
  .row:hover::before {
    opacity: 0.28;
  }
  .row:active::before {
    opacity: 0.36;
  }
  .row > * {
    position: relative;
  }
  .row.center {
    justify-content: center;
    text-align: center;
  }
  .row.center .text {
    align-items: center;
  }
  .row.center .text {
    flex: none;
  }
  ha-icon {
    --mdc-icon-size: 24px;
    flex: none;
    color: var(--secondary-text-color);
  }
  .text {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
    flex: 1 1 auto;
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .text > span {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .label {
    font-size: var(--ha-font-size-s, 12px);
    font-weight: var(--ha-font-weight-normal, 400);
    color: var(--secondary-text-color);
  }
`;
