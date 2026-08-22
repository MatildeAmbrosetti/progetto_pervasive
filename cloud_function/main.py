import functions_framework
from google.cloud import firestore
import os
import datetime

# Inizializza il client Firestore (si collega automaticamente al DB del tuo progetto)
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GCP_PROJECT')
DATABASE_ID = os.environ.get('FIRESTORE_DATABASE', 'dati')

# Inizializza il client
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)
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
        oggi_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')

        # 3. Scrivi il dato su Firestore nella collezione "letture_sensore"
        # .add() genera automaticamente un ID univoco per ogni lettura
        db.collection('eventi').add(request_json)

        if request_json.get('tipo') == 'Ricarica':
            db.collection('riassunti_giornalieri').document(oggi_str).set({"pasto": True, "totale": firestore.Increment(request_json.get("grammi_delta")),"ultimo_aggiornamento": firestore.SERVER_TIMESTAMP,"ultimo_evento":"Ricarica"}, merge=True)
        elif request_json.get('tipo') == 'Pasto':
            db.collection('riassunti_giornalieri').document(oggi_str).set({ "totale_mangiato":firestore.Increment(-request_json.get("grammi_delta")),"ultimo_aggiornamento": firestore.SERVER_TIMESTAMP,"ultimo_evento":"Pasto"}, merge=True)
        return ('Dato salvato con successo!', 200, headers)
    except Exception as e:
        print(f"Errore durante il salvataggio: {e}")
        return (f"Errore interno: {e}", 500, headers)
