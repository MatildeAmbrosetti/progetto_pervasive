import machine
import time
import network
import socket
import json

# --- CONFIGURAZIONE HARDWARE ---
led_di_stato = machine.Pin(2, machine.Pin.OUT)
dout = machine.Pin(13, machine.Pin.IN)
pdsck = machine.Pin(12, machine.Pin.OUT, value=0)

SCALE = -458.9700  
offset = 0
storico_log = []

def carica_configurazione():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except:
        return None

def web_print(messaggio):
    print(messaggio)
    riga = f"<div>[{time.ticks_ms() // 1000}s] {messaggio}</div>"
    storico_log.append(riga)
    if len(storico_log) > 15: storico_log.pop(0)

def avvia_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep(0.5)
    wlan.active(True)
    
    if not wlan.isconnected():
        web_print(f"Connessione a {ssid}...")
        wlan.connect(ssid, password)
        tentativi = 0
        while not wlan.isconnected() and tentativi < 20:
            led_di_stato.value(not led_di_stato.value())
            time.sleep(0.5)
            tentativi += 1
            
    if wlan.isconnected():
        led_di_stato.value(1)
        ip = wlan.ifconfig()[0]
        web_print(f"Connesso! IP: {ip}")
        
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
    web_print("--- TARA (Svuota piatto) ---")
    time.sleep(3)
    offset = get_clean_value(40)
    web_print("--- CALIBRAZIONE (Metti peso) ---")
    time.sleep(5)
    valore_con_peso = get_clean_value(40)
    SCALE = (valore_con_peso - offset) / known_weight_grams if (valore_con_peso - offset) != 0 else 1.0
    web_print("Calibrazione OK.")

# --- AVVIO ---
conf = carica_configurazione()
if conf:
    ip_address = avvia_wifi(conf['wifi_ssid'], conf['wifi_password'])
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', 80))
    server.listen(5)
    server.setblocking(False)

    #calibrate(conf['known_weight'])

    peso_precedente = 0.0
    #in_pasto = False
    ultimo_agg = time.ticks_ms()
    grammi = 0.0
    while True:
        if time.ticks_diff(time.ticks_ms(), ultimo_agg) > 500:
            #grammi = (get_clean_value(10) - offset) / SCALE
            #if abs(grammi) < 2.0: grammi = 0.0
            grammi +=1.0
            riga_peso = f"<div><strong>Peso: {grammi:.1f} g</strong></div>"
            
            # Logica pasto
            diff = peso_precedente - grammi
            #if diff > 10.0 and not in_pasto:
            #    web_print("<span style='color:red;'>[EVENTO] Inizio pasto!</span>")
            #    in_pasto = True
            #elif in_pasto and abs(diff) < 2.0:
             #   web_print(f"<span style='color:green;'>[EVENTO] Fine pasto.</span>")
             #   in_pasto = False
            
            peso_precedente = grammi
            ultimo_agg = time.ticks_ms()

        try:
            conn, addr = server.accept()
            html = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
            html += '<html><head><meta http-equiv="refresh" content="2"></head>'
            html += '<body style="background:#000;color:#0f0;font-family:monospace;">'
            html += '<h2>Live Dog Tracker</h2><div style="border:1px solid #555;padding:10px;">'
            for r in storico_log: html += r
            html += "<br>" + riga_peso + "</div></body></html>"
            conn.sendall(html.encode('utf-8'))
            conn.close()
        except: pass
        time.sleep_ms(50)