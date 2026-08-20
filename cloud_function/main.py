import functions_framework
from google.cloud import firestore
import os

# Inizializza il client Firestore (si collega automaticamente al DB del tuo progetto)
db = firestore.Client(database='dati')
#estrae la password dalla configurazione della cloud function 
API_SECRET_KEY = os.environ.get('API_SECRET_KEY')

@functions_framework.http
def ricevi_dati_sensore(request):
    # Gestione del CORS per permettere al sito web (o a Colab) di chiamarla senza blocchi
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Imposta gli header CORS per la risposta effettiva
    headers = {'Access-Control-Allow-Origin': '*'}

    #controllo che l'api passata dal sensore sia corretta 
    client_api_key = request.headers.get('X-API-Key')
    if not client_api_key or client_api_key != API_SECRET_KEY:
        return ('Non autorizzato', 401, headers)
    
    # 1. Recupera il JSON inviato dal sensore
    request_json = request.get_json(silent=True)
    
    if not request_json:
        return ('Errore: Nessun dato JSON ricevuto', 400, headers)

#caricamento su Firestore del dato ricevuto dal sensore, con timestamp del server per sicurezza
    try:
        # 2. (Opzionale) Aggiungiamo un timestamp del server per sicurezza

        request_json['ricevuto_il'] = firestore.SERVER_TIMESTAMP

        # 3. Scrivi il dato su Firestore nella collezione "letture_sensore"
        # .add() genera automaticamente un ID univoco per ogni lettura
        db.collection('eventi').add(request_json)
        
        return ('Dato salvato con successo!', 200, headers)

    except Exception as e:
        print(f"Errore durante il salvataggio: {e}")
        return (f"Errore interno: {e}", 500, headers)
