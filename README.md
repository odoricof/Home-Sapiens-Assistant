# Camedomotic

## Italiano

Integrazione custom di Home Assistant per interfacciarsi con la webpage Home Sapiens esposta da ETI/DOMO, con supporto delle centrali antifurto.  


### Funzionalità

- In fase di sviluppo: luci, ingressi digitali, relè, coperture, sensori energia, termostati, scenari.  
- Gestione totale della centrale antifurto Proxinet 36.  
- servizio RTC per sincronizzazione giornaliera dell'orologio della centrale.  
- Logger eventi centrale predisposto per esportazione in CSV.


### Installazione

Copia la cartella `domo` nella directory `custom_components/` di Home Assistant, poi riavvia HA.  
Puoi anche installarla tramite HACS dal repository: https://github.com/odoricof/Home-Sapiens-Assistant

### Configurazione

Inserire in UI i seguenti dati:  
- host: Indirizzo IP di ETI/Domo  
- nome utente: lo stesso che usi per accedere alla pagina web Homesapiens  
- password: la stessa che usi per accedere alla pagina web Homesapiens  

In "Configura", immettere l'indirizzo IP della centrale Proxinet per attivare il servizio RTC

### Licenza

Consultare il file LICENSE.

---

## English

Custom Home Assistant integration to interface with the Home Sapiens webpage exposed by ETI/DOMO, with support for burglar alarm control panels.  


### Features

- Work in progress: Lights, digital inputs, relays, covers, energy sensors, thermostats, scenarios.  
- Full management of the Proxinet 36 alarm panel.  
- RTC service for daily synchronization of the alarm panel clock.  
- Central event logger ready for CSV export.

### Installation

Copy the `domo` folder to your Home Assistant `custom_components/` directory, then restart HA.  
You can also install it via HACS from the repository: https://github.com/odoricof/Home-Sapiens-Assistant

### Configuration

In the UI, enter the following data:  
- Host: IP address of ETI/Domo  
- Username: same used to log into the Homesapiens web page  
- Password: same used to log into the Homesapiens web page  

In “Configure”, enter the IP address of the Proxinet alarm panel.

### License

See the LICENSE file.

