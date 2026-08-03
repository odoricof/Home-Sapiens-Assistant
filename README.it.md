### 🌐 Lingua / Language
- [Italiano](README.it.md) | [English](README.md)

---

[![Current release](https://img.shields.io/github/release/odoricof/Home-Sapiens-Assistant.svg?style=plastic&label=Current%20release)](https://github.com/odoricof/Home-Sapiens-Assistant/releases)
[![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=plastic)](https://github.com/odoricof/Home-Sapiens-Assistant)  
[![downloads](https://img.shields.io/github/downloads/odoricof/Home-Sapiens-Assistant/total?style=plastic&label=Total%20downloads)](https://github.com/odoricof/Home-Sapiens-Assistant/releases)
[![Buy me a beer 🍺🍺🍺](https://img.shields.io/badge/PayPal-Buy%20me%20a%20beer%20🍺🍺🍺-blue?style=plastic&logo=paypal)](https://paypal.me/odoricof)

<img src="https://raw.githubusercontent.com/odoricof/Home-Sapiens-Assistant/main/custom_components/domo/brand/logo@2x.png" width="96" alt="">

# Home Sapiens Assistant
---
**Integrazione personalizzata** per **Home Assistant** per interfacciarsi con **Bpt Home Automation / CAME Domotic 3.0** (sistemi basati su server ETI/DOMO) tramite l'interfaccia web di Home Sapiens.

---

## Funzionalità

Questa integrazione consente a Home Assistant di monitorare e controllare un sistema Bpt Home Automation / CAME Domotic.

Attualmente supportati:

- Attivazioni
- Ingressi analogici
- Climatizzazione
   - Ventilconvettori (fan coils)
   - Gestione profili termici
   - Replica integrale di tutte le funzioni esposte in lettura e scrittura
- Ingressi digitali
- Irrigazione
   - Replica integrale di tutte le funzioni esposte in lettura e scrittura
- Contatori energetici
- Centrale d'allarme intrusioni
   - Aree
   - Ingressi
   - Uscite
   - Scenari
   - Notifiche di trigger e allarmi
   - Silenziamento sirene
   - Cancellazione memoria eventi
- Luci
- Aperture
- Scenari
- Programmazione oraria
- TVCC

Servizi aggiuntivi:

- Notifiche di stato offline/online del server ETI/DOMO
- Log settimanale degli eventi di sicurezza
- Backup locale e ripristino di tutti i profili termici ti tutti i termostati per entrambe le stagioni
---

## Come funziona

L'integrazione comunica con il sistema replicando le stesse richieste HTTP utilizzate dall'interfaccia web ufficiale **Home Sapiens** esposta da ETI/DOMO.

Non essendo fornita un'API diretta dal produttore, l'integrazione interagisce con il sistema tramite le comunicazioni web osservate.

---

## Installazione

### HACS (consigliato)

1. Apri HACS in Home Assistant  
2. Vai su **Integrazioni**  
3. Cerca **Home Sapiens Assistant** e installa  
4. Riavvia Home Assistant  

---

### Installazione manuale

1. Scarica questo repository  
2. Copia la cartella: `custom_components/domo/` nella directory di Home Assistant
3. Riavvia Home Assistant  

---

## Configurazione

Dopo l'installazione:

1. Vai su **Impostazioni → Dispositivi e Servizi**
2. Clicca **Aggiungi integrazione**
3. Cerca **Home Sapiens Assistant**
4. Inserisci:
   - Indirizzo IP del server ETI/DOMO
   - Credenziali di accesso alla pagina web di Home Sapiens

---

## Nota sulla visualizzazione degli scenari nel pannello allarme di Home Assistant

Per garantire una visualizzazione corretta e coerente degli scenari all'interno del pannello allarme di Home Assistant, deve essere soddisfatta la seguente condizione:

> **Ogni scenario programmato sulla centrale d'allarme deve includere almeno un'area che lo differenzi dagli altri.**  
> Questa differenziazione consente al sistema di riconoscere e visualizzare correttamente lo stato attuale del sistema di sicurezza.

### Esempio pratico

#### Aree definite:
- **Area Giorno**
- **Area Notte**
- **Area Perimetro**

#### Scenari e aree associate:

| Scenario               | Aree associate                       |
|------------------------|--------------------------------------|
| **"Inserito assente"** | Area Giorno + Area Notte + Area Perimetro |
| **"Inserito casa"**    | Area Perimetro                       |
| **"Inserito notte"**   | Area Giorno + Area Perimetro         |

In questo esempio, ogni scenario presenta una combinazione unica di aree, consentendo al pannello di Home Assistant di distinguerli correttamente e aggiornare l'interfaccia utente di conseguenza.

> **Importante:** Quando configuri la tua centrale d'allarme, assicurati che ogni scenario abbia un **insieme di aree distinto** da tutti gli altri.

---

## Requisiti

- Un sistema funzionante **Bpt Home Sapiens Domotic / CameDomotic 3.0**
- Accesso all'**interfaccia web di Home Sapiens**
- Connettività di rete tra Home Assistant e il server ETI/DOMO

---

## Disclaimer

Questo è un **progetto indipendente** sviluppato da [@odoricof](https://github.com/odoricof).

- Non affiliato né approvato dal produttore di ETI/DOMO.
- Utilizza dati ricavati da comunicazioni HTTP osservabili pubblicamente dall'interfaccia web
- La compatibilità con tutte le versioni del firmware non è garantita

**Utilizzo a proprio rischio.**  
Per la configurazione ufficiale e la gestione del sistema, fare sempre riferimento agli strumenti del produttore.

---

## Licenza

Questo progetto è rilasciato sotto la **Licenza MIT**:  
https://opensource.org/licenses/MIT

---

## Stato del progetto

Sviluppo attivo.  
Funzionalità e compatibilità possono evolvere nel tempo.

---

## Contributi

Contributi, segnalazioni di problemi e suggerimenti sono benvenuti:

https://github.com/odoricof/Home-Sapiens-Assistant/issues
