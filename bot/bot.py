from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from secret import token, db_nome
from google.cloud import firestore
import os
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credential.json')

# Collega Firestore usando il percorso assoluto
db = firestore.Client.from_service_account_json(CREDENTIALS_PATH,database=db_nome)
date_str = datetime.datetime.now().strftime("%Y-%m-%d")

async def rispondi_pasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Risponde a qualsiasi frase contenente "pasto" (case-insensitive)
    doc = db.collection('riassunti_giornalieri').document(date_str).get()
    if doc.exists:
        data = doc.to_dict()
        totale = data.get("totale_mangiato", 0)
        return await update.message.reply_text(f"Rey ha mangiato per ora {totale} grammi")
    else:
        return await update.message.reply_text(f"Rey non ha mangiato")
     
async def rispondi_dare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = db.collection('riassunti_giornalieri').document(date_str).get()
    if doc.exists:
        await update.message.reply_text("Hai dato da mangiare a Rey")
    else:
        return await update.message.reply_text(f"non hai dato da mangiare a Rey")
    
async def start(update, context):
    testo_benvenuto = (
        f"Ciao {update.effective_user.first_name}! Benvenuto.\n\n"
        "Ecco le regole del bot:\n"
        "1. Scrivi un messaggio con scritto 'mangiato' per sapere quanto ha mangiato Rey oggi .\n"
        "2. Scrivi un messaggio con scritto 'dato' se vuoi sapere se hai dato da mangiare a Rey oggi ."
    )
    await update.message.reply_text(testo_benvenuto)


    
print('starting')

app = ApplicationBuilder().token(token).build()


# Nell'inizializzazione degli handler:
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex(r'(?i)mangiato'), rispondi_pasto))
app.add_handler(MessageHandler(filters.Regex(r'(?i)dato'), rispondi_dare))
app.add_handler(MessageHandler(filters.Regex(r'(?i)aggiornamento'), rispondi_dare))
app.run_polling()