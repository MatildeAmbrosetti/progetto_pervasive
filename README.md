Guida alla Configurazione e al Funzionamento
1. Questo progetto è stato sviluppato utilizzando MicroPico. 
  Rinomina il file config_EXAMPLE.json in config.json.
  Apri config.json e inserisci i parametri richiesti.
Nota: I valori relativi ai pesi per la calibrazione devono essere espressi in grammi.

2. Mappatura dei Pin (ESP32)
   Il sistema utilizza la seguente configurazione hardware di default:
     LED di Stato Pin 2
   HX711 DOUTP in Pin 13
   HX711 PD_SCKPin Pin 12
   Una volta completata la configurazione, carica l'intera cartella dog sull'ESP32 come progetto principale.
   
3. Ciclo di Funzionamento e Stato del LED
   Tramite il LED di stato è possibile capire in che stato si trova il controllore:
   LED Lampeggiante: Connessione alla rete Wi-Fi in corso.
   LED Spento: Esecuzione automatica della tara.
   LED Fisso per la prima volta : Inizio della calibrazione (posizionare il peso campione fisso sulla bilancia).
   3 Lampeggi veloci: Calibrazione completata con successo.
   LED Sempre Acceso: Sistema operativo; la bilancia è pronta e inizia a pesare il cibo in tempo reale.

4. Architettura Cloud e Invio Dati (Firestore)
   L'invio dei dati al database avviene tramite una Google Cloud Function (sviluppata in Python e distribuita su Cloud Run), indipendente dal server Flask.
   Database: I dati vengono salvati nel database dati su Firestore.
   Autenticazione e Sicurezza:Il microcontrollore invia nell'header della richiesta HTTP una chiave di autenticazione, insieme alle credenziali (username e password).La Cloud Function verifica che la chiave nell'header corrisponda a una variabile d'ambiente configurata al momento della creazione.Questo meccanismo garantisce che solo i dispositivi autorizzati possano scrivere su Firestore.
