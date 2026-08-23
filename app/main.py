from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
from google.cloud import firestore
from datetime import datetime
from secret import usersdb, secret_key
import os

class User(UserMixin):
    def __init__(self, username):
        super().__init__()
        self.id = username
        self.username = username
        self.par = {}

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key
login = LoginManager(app)
login.login_view = '/static/login.html'
# Inizializzazione del client Firestore
# Calcola il percorso esatto della cartella corrente in cui risiede main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credential.json')

# Collega Firestore usando il percorso assoluto
db = firestore.Client.from_service_account_json(CREDENTIALS_PATH,database='dati')
@login.user_loader
def load_user(username):
    if username in usersdb:
        return User(username)
    return None

@app.route('/api/dati-giorno', methods=['GET'])
@login_required
def get_dati_giorno():
    date_str = request.args.get('date')  # es. "2026-10-15"
    if not date_str:
        return jsonify({'error': 'Data non fornita'}), 400

    doc_ref = db.collection('riassunti_giornalieri').document(date_str)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        return jsonify({
            'success': True,
            'pasto': data.get('pasto', False),
            'totale': data.get('totale', 0),
            'totale_mangiato': data.get('totale_mangiato', 0),
            'ultimo_aggiornamento': data.get('ultimo_aggiornamento', ''),
            'ultimo_evento':data.get( 'ultimo_evento',' ')
        })
    else:
        return jsonify({
            'success': False,
            'pasto': False,
            'totale': 0,
            'totale_mangiato': 0,
            'ultimo_aggiornamento': '--:--',
            'ultimo_evento':" "
        })

@app.route('/login', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    username = request.form.get('u')
    password = request.form.get('p')
    
    if username in usersdb and password == usersdb[username]:
        login_user(User(username), remember=True)
        next_page = request.args.get('next') or url_for('index')
        return redirect(next_page)
        
    return redirect('/static/login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
@login_required
def index():
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('index.html', today=today)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

