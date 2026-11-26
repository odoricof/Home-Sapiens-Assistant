# Card per le dashboard

Ogni cartella dentro `src/` è una **famiglia di card** e diventa un file a sé:

| Cartella | File prodotto |
| --- | --- |
| `src/thermostat/` | `custom_components/domo/www/domo-thermostat-card.js` |
| `src/security/` (esempio) | `custom_components/domo/www/domo-security-card.js` |

## Aggiungere una nuova famiglia

1. Crea `src/<famiglia>/` con un `index.js` che registra le card (vedi `src/thermostat/index.js`).
2. Esegui `npm install` (la prima volta) e `npm run build`.
3. Alza la versione in `custom_components/domo/manifest.json` al rilascio.

L'integrazione carica da sola tutti i file `domo-*-card.js` della cartella `www`: non serve modificare il codice Python.

## Pezzi condivisi tra famiglie

Ogni famiglia è indipendente: se una nuova famiglia ha bisogno di un pezzo già fatto (per esempio le icone di avviso o i pulsanti), si **copia** nella sua cartella invece di condividerlo.

Regola importante: due famiglie vengono caricate nella stessa pagina, quindi i nomi dei componenti non possono ripetersi. Quando copi un pezzo, cambia il suo nome aggiungendo il nome della famiglia (per esempio `domo-status-icons` diventa `domo-security-status-icons`). Se due famiglie usassero lo stesso nome, vincerebbe quello caricato per primo e l'altra famiglia userebbe un componente non suo.
