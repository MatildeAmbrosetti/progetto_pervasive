import functions_framework
from google.cloud import firestore
import os
import datetime
import asyncio
from secret import db_nome, token_key
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GCP_PROJECT')
DATABASE_ID = os.environ.get('FIRESTORE_DATABASE', db_nome)

# Inizializza il client
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)
#estrae la password dalla configurazione della cloud function 
API_SECRET_KEY = os.environ.get('API_SECRET_KEY')
TELEGRAM_TOKEN = token_key
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
_bot_initialized = False 
async def ensure_bot_initialized():
    global _bot_initialized
    if not _bot_initialized:
        await telegram_app.initialize()
        _bot_initialized = True
async def rispondi_pasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # La data viene calcolata durante l'esecuzione della richiesta
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    doc = db.collection('riassunti_giornalieri').document(date_str).get()
    
    if doc.exists:
        data = doc.to_dict()
        totale = data.get("totale_mangiato", 0)
        await update.message.reply_text(f"Rey ha mangiato per ora {totale} grammi")
    else:
        await update.message.reply_text("Rey non ha mangiato")

async def rispondi_dare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    doc = db.collection('riassunti_giornalieri').document(date_str).get()
    
    if doc.exists:
        await update.message.reply_text("Hai dato da mangiare a Rey")
    else:
        await update.message.reply_text("Non hai dato da mangiare a Rey")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo_benvenuto = (
        f"Ciao {update.effective_user.first_name}! Benvenuto.\n\n"
        "Ecco le regole del bot:\n"
        "1. Scrivi 'mangiato' per sapere quanto ha mangiato Rey oggi.\n"
        "2. Scrivi 'dato' per sapere se hai dato da mangiare a Rey oggi."
    )
    await update.message.reply_text(testo_benvenuto)
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.Regex(r'(?i)mangiato'), rispondi_pasto))
telegram_app.add_handler(MessageHandler(filters.Regex(r'(?i)dato'), rispondi_dare))
telegram_app.add_handler(MessageHandler(filters.Regex(r'(?i)aggiornamento'), rispondi_dare))

@functions_framework.http
def bot_webhook(request):
    if request.method == 'POST':
        request_json = request.get_json(silent=True)
        if not request_json:
            return ('Nessun payload JSON ricevuto', 400)


        async def process():
            await ensure_bot_initialized()
            update = Update.de_json(request_json, telegram_app.bot)
            await telegram_app.process_update(update)

        asyncio.run(process())
        return ('OK', 200)
    
    return ('Metodo non supportato', 405)