import machine
import time
import network
import socket
import json
import requests
import sys

def carica_configurazione():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print("Errore nel caricamento della configurazione.")
        log_errore(e)
        time.sleep(2)
        return None
        


# --- CONFIGURAZIONE HARDWARE ---
led_di_stato = machine.Pin(2, machine.Pin.OUT)
#dati
dout = machine.Pin(13, machine.Pin.IN)
#clock
pdsck = machine.Pin(12, machine.Pin.OUT, value=0)

SCALE = 1 
offset = 0
#storico_log = []


def avvia_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep(0.5)
    wlan.active(True)
    
    if not wlan.isconnected():
        #web_print(f"Connessione a {ssid}...")
        wlan.connect(ssid, password)
        tentativi = 0
        while not wlan.isconnected() and tentativi < 20:
            led_di_stato.value(not led_di_stato.value())
            time.sleep(0.5)
            tentativi += 1
            
    if wlan.isconnected():
        led_di_stato.value(1)
        ip = wlan.ifconfig()[0]
        #web_print(f"Connesso! IP: {ip}")
        
        return ip
    return None

# --- LOGICA BILANCIA (Funzioni HX711 già testate) ---
def get_raw():
    timeout = 0
    # Attesa che il sensore sia pronto
    while dout.value() and timeout < 100:
        time.sleep_ms(1)
        timeout += 1
    
    # MODIFICA 1: Se il sensore va in timeout, esce subito ed evita il blocco
    if timeout >= 100:
        return 0

    raw = 0
    # MODIFICA 2: Rimosso machine.disable_irq() che causava il Watchdog Panic
    for _ in range(24):
        pdsck.value(1)
        pdsck.value(0)
        raw = (raw << 1) | dout.value()
        
    pdsck.value(1)
    pdsck.value(0)
    
    if raw & 0x800000: 
        raw -= 0x1000000
    return raw

def get_clean_value(samples=15):
    vals = [get_raw() for _ in range(samples)]
    vals.sort()
    trimmed = vals[2:-2]
    return sum(trimmed) / len(trimmed) if trimmed else 0

def calibrate(known_weight_grams):
    global SCALE, offset
    led_di_stato.value(0)
    print("--- TARA (Svuota piatto) ---")
    time.sleep(3)
    offset = get_clean_value(40)
    led_di_stato.value(1)
    print("--- CALIBRAZIONE (Metti peso) ---")
    time.sleep(5)
    valore_con_peso = get_clean_value(40)
    SCALE = (valore_con_peso - offset) / known_weight_grams if (valore_con_peso - offset) != 0 else 1.0
    print("Calibrazione OK.")
    led_di_stato.value(0)
    time.sleep(2)
    led_di_stato.value(1)
    time.sleep(2)
    led_di_stato.value(0)
    time.sleep(2)
    led_di_stato.value(1)
    time.sleep(5)

def log_errore(e):
    print("!!! ERRORE RILEVATO !!!")
    try:
        with open("log_errori.txt", "a") as f:
            f.write(f"\n[{time.ticks_ms()}] Errore:\n")
            sys.print_exception(e, f)
    except:
        pass
# --- AVVIO ---
print("Avvio dello script in corso...")
conf = carica_configurazione()
if conf:
    print("Configurazione caricata correttamente.")
    ip_address = avvia_wifi(conf['wifi_ssid'], conf['wifi_password'])
    evento_tag=False
    evento=False
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', 80))
    server.listen(5)
    server.setblocking(False)

    calibrate(conf['known_weight'])
    # --- PARAMETRI DI CAMPIONAMENTO ---
    SOGLIA_MOVIMENTO = 5.0      # Grammi di variazione per rilevare attività
    SOGLIA_EVENTO = 10.0        # Grammi minimi per considerare Pasto/Ricarica
    TEMPO_STABILITA_MS = 3000   # Tempo in ms in cui il peso deve stare fermo per validare
    evento = {"tipo": "utente", "utente":conf['utente'],"password": conf['password']}
    try:
        headers = {"Content-Type": "application/json", "X-API-Key": conf['api_key']}
        risposta = requests.post(conf['server_url'], json=evento, headers=headers)
        risposta.close()
    except Exception as e:
        print(f"Errore invio: {e}")
        log_errore(e)
        pass
    peso_stabile = 0.0
    peso_istantaneo=0.0
    stato_bilancia = "STAZIONARIO"
    inizio_stabilizzazione = time.ticks_ms()
    ultimo_campione_time = time.ticks_ms()
    lettura_precedente_temp=0.0
    while True:
        ora = time.ticks_ms()
        
        # Campionamento frequente ogni 300ms
        if time.ticks_diff(ora, ultimo_campione_time) >= 300:
            ultimo_campione_time = ora
            
            # Lettura rapida
            peso_istantaneo = ((get_clean_value() - offset) / SCALE) - 249
            print("peso_istantaneo:", peso_istantaneo)
            
            # 1. Rilevamento rimozione ciotola
            if peso_istantaneo < -30:
                if stato_bilancia != "CIOTOLA_RIMOSSA":
                    print("Ciotola rimossa")
                    stato_bilancia = "CIOTOLA_RIMOSSA"
                continue
                
            # 2. Riposizionamento ciotola
            elif stato_bilancia == "CIOTOLA_RIMOSSA" and peso_istantaneo >= -10:
                # NON salviamo subito il peso qui per evitare di catturare il valore parziale della mano.
                # Mandiamo la bilancia in IN_ATTIVITÀ per farla stabilizzare correttamente.
                print("Ciotola riposizionata: in attesa di stabilizzazione...")
                stato_bilancia = "IN_ATTIVITÀ"
                inizio_stabilizzazione = ora
                lettura_precedente_temp = peso_istantaneo
                continue

            # 3. Controllo variazione rispetto al peso stabile memorizzato
            delta_istantaneo = peso_istantaneo - peso_stabile
            
            if stato_bilancia == "STAZIONARIO":
                if abs(delta_istantaneo) > SOGLIA_MOVIMENTO:
                    print("Attività rilevata (cane alla ciotola o ricarica)...")
                    stato_bilancia = "IN_ATTIVITÀ"
                    inizio_stabilizzazione = ora
                    
            elif stato_bilancia == "IN_ATTIVITÀ":
                # Verifichiamo se il peso si sta ri-stabilizzando
                if abs(peso_istantaneo - lettura_precedente_temp) < 2.0:
                    if time.ticks_diff(ora, inizio_stabilizzazione) > TEMPO_STABILITA_MS:
                        # Peso stabilizzato! Calcoliamo l'evento
                        delta_totale = peso_istantaneo - peso_stabile
                        
                        evento = None
                        if delta_totale < -SOGLIA_EVENTO:
                            print("pasto")
                            evento = {"tipo": "Pasto", "grammi_delta": round(abs(delta_totale))}
                        elif delta_totale > SOGLIA_EVENTO:
                            print("ricarica")
                            evento = {"tipo": "Ricarica", "grammi_delta": round(delta_totale)}
                        
                        if evento:
                            print(f"Evento registrato: {evento}")
                            try:
                                headers = {"Content-Type": "application/json", "X-API-Key": conf['api_key']}
                                risposta = requests.post(conf['server_url'], json=evento, headers=headers)
                                risposta.close()
                            except Exception as e:
                                print(f"Errore invio: {e}")
                                log_errore(e)
                                pass
                                
                        # Aggiorniamo il nuovo punto zero/stabile
                        peso_stabile = peso_istantaneo
                        stato_bilancia = "STAZIONARIO"
                else:
                    # Se il peso varia ancora (es. la mano sta ancora muovendo la ciotola), si resetta il timer
                    inizio_stabilizzazione = ora
                    
            lettura_precedente_temp = peso_istantaneo
            
        time.sleep_ms(50) # Piccola pausa per risparmiare CPU
