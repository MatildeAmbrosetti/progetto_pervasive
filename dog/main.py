import machine
import time
import network
import socket
import json
import requests

def carica_configurazione():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except:
        print("Errore nel caricamento della configurazione.")
        return None
        
flag_calibrazione = False 
def gestore_irq(pin):
    global flag_calibrazione
    flag_calibrazione = True  # Segnala solo che il tasto è stato premuto

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
    while dout.value() and timeout < 500:
        time.sleep_ms(1)
        timeout += 1
    raw = 0
    state = machine.disable_irq()
    for _ in range(24):
        pdsck.value(1)
        time.sleep_us(1)
        pdsck.value(0)
        time.sleep_us(1)
        raw = (raw << 1) | dout.value()
    pdsck.value(1)
    time.sleep_us(1)
    pdsck.value(0)
    machine.enable_irq(state)
    if raw & 0x800000: raw -= 0x1000000
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
# --- AVVIO ---
print("Avvio dello script in corso...")
conf = carica_configurazione()
if conf:
    print("Configurazione caricata correttamente.")
    ip_address = avvia_wifi(conf['wifi_ssid'], conf['wifi_password'])
    evento=False
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', 80))
    server.listen(5)
    server.setblocking(False)

    calibrate(conf['known_weight'])

    peso_precedente = 0.0
    ultimo_agg = time.ticks_ms()
    grammi = 0.0
    while True:
        
        if time.ticks_diff(time.ticks_ms(), ultimo_agg) > 10000:
            
            print("Lettura peso...")
            grammi =( (get_clean_value(10) - offset) / SCALE )- 272
            print(f"Peso attuale: {grammi:.2f} grammi") 
            #if abs(grammi) < 2.0: grammi = 0.0
            #evento Ricarica
            if grammi<-100:
                print("ciotola rimossa")   
            elif grammi-10>peso_precedente:
                evento=True
                print(f"Ricarica: {grammi} grammi")
                evento = {"tipo": "Ricarica",
                #"grammi": grammi,
                "grammi_delta": grammi-peso_precedente

                }
            # Logica pasto
            elif peso_precedente-grammi > 10.0:
                evento=True
                print(f"Pasto: {peso_precedente-grammi} grammi")
                evento = {
                "tipo": "Pasto",
                #"grammi": grammi,
                "grammi_delta": peso_precedente-grammi
                }
            if grammi >= -10:
                peso_precedente = grammi
            peso_precedente = grammi
            ultimo_agg = time.ticks_ms()  
        if evento:
            try:
                #print(f"Invio evento al server: {evento}")
                # Definisci gli header con la chiave d'accesso letta dal config.json
                headers = {
                    "Content-Type": "application/json",
                    "X-API-Key": conf['api_key']
                }

                # Invia la chiamata HTTP POST includendo gli headers
                risposta = requests.post(conf['server_url'], json=evento, headers=headers)
                #print(f"Lettura {i+1} inviata! Risposta server: {risposta.status_code}")
                
                # Chiudi la connessione della risposta (consigliato su MicroPython per liberare memoria)
                risposta.close()

            except Exception as e:
                print(f"Errore durante l'invio: {e}")

            evento=False
                
# print("Simulazione completata.")