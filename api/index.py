from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
from functools import wraps
import os
import sys
from dotenv import load_dotenv
import json
from datetime import datetime

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from document_processor import DocumentProcessor
from ai_processor import Summarizer
import database as db

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt'}
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'fallback-secret-key')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Variable pour stocker le nom du fichier courant
current_filename = None

doc_processor = DocumentProcessor()
ai_processor = Summarizer()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def login_required(f):
    """Décorateur pour vérifier que l'utilisateur est connecté"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Non autorisé. Veuillez vous connecter.', 'auth_required': True}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_current_user_id():
    """Récupère l'ID de l'utilisateur connecté"""
    return session.get('user_id')


# Route pour servir le logo N.svg
@app.route('/N.svg')
def serve_logo():
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'N.svg')
    return send_file(logo_path, mimetype='image/svg+xml')


# ==================== AUTHENTIFICATION ====================

@app.route('/auth/register', methods=['POST'])
def register():
    """Inscription d'un nouvel utilisateur"""
    try:
        data = request.get_json()
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Validations
        if not username or len(username) < 3:
            return jsonify({'error': 'Le nom d\'utilisateur doit contenir au moins 3 caractères', 'success': False}), 400
        
        if not email or '@' not in email:
            return jsonify({'error': 'Email invalide', 'success': False}), 400
        
        if not password or len(password) < 6:
            return jsonify({'error': 'Le mot de passe doit contenir au moins 6 caractères', 'success': False}), 400
        
        result = db.create_user(username, email, password)
        
        if result['success']:
            # Connecter automatiquement après inscription
            session['user_id'] = result['user_id']
            session['username'] = username
            return jsonify({
                'success': True,
                'message': 'Compte créé avec succès',
                'user': {'id': result['user_id'], 'username': username, 'email': email}
            })
        else:
            return jsonify({'success': False, 'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/auth/login', methods=['POST'])
def login():
    """Connexion d'un utilisateur"""
    try:
        data = request.get_json()
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email et mot de passe requis', 'success': False}), 400
        
        result = db.verify_user(email, password)
        
        if result['success']:
            session['user_id'] = result['user']['id']
            session['username'] = result['user']['username']
            return jsonify({
                'success': True,
                'message': 'Connexion réussie',
                'user': result['user']
            })
        else:
            return jsonify({'success': False, 'error': result['error']}), 401
            
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/auth/logout', methods=['POST'])
def logout():
    """Déconnexion de l'utilisateur"""
    session.clear()
    return jsonify({'success': True, 'message': 'Déconnexion réussie'})


@app.route('/auth/status')
def auth_status():
    """Vérifie le statut de connexion"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'username': session.get('username')
            }
        })
    return jsonify({'authenticated': False})


# ==================== PAGES ====================

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/history')
def history_page():
    return render_template('history.html')


@app.route('/statistics')
def statistics_page():
    return render_template('statistics.html')


@app.route('/documentation')
def documentation_page():
    return render_template('documentation.html')


# ==================== API DOCUMENTS ====================

@app.route('/upload', methods=['POST'])
def upload_file():
    global current_filename
    
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        current_filename = filename

        text = doc_processor.extract_text(filepath)

        # Nettoyer le fichier après extraction
        try:
            os.remove(filepath)
        except:
            pass

        if text:
            return jsonify({
                'text': text,
                'stats': doc_processor.get_stats(text),
                'filename': filename
            })
        else:
            return jsonify({'error': 'Impossible d\'extraire le texte du fichier'}), 400

    return jsonify({'error': 'Type de fichier non autorisé'}), 400


@app.route('/analyze', methods=['POST'])
def analyze_text():
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Aucun texte fourni'}), 400
    
    return jsonify({'stats': doc_processor.get_stats(text)})


@app.route('/summarize', methods=['POST'])
def summarize():
    global current_filename
    
    data = request.get_json()
    text = data.get('text', '')
    max_words = data.get('max_words', 150)
    style = data.get('style', 'standard')
    format_type = data.get('format', 'paragraphe')

    if not text:
        return jsonify({'error': 'Aucun texte fourni'}), 400

    summary = ai_processor.summarize(text, max_words, style, format_type)
    
    # Sauvegarder dans l'historique si l'utilisateur est connecté
    user_id = get_current_user_id()
    if user_id and summary:
        db.save_summary(
            user_id=user_id,
            original_text=text,
            summary=summary,
            filename=current_filename,
            max_words=max_words,
            style=style,
            format_type=format_type
        )
        current_filename = None

    return jsonify({'summary': summary})


@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    text = data.get('text', '')
    target_language = data.get('target_language', 'en')

    if not text:
        return jsonify({'error': 'Aucun texte fourni'}), 400

    translation = ai_processor.translate(text, target_language)
    return jsonify({'translation': translation})


@app.route('/keywords', methods=['POST'])
def extract_keywords():
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({'error': 'Aucun texte fourni'}), 400

    keywords = ai_processor.extract_keywords(text)
    return jsonify({'keywords': keywords})


@app.route('/titles', methods=['POST'])
def generate_titles():
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({'error': 'Aucun texte fourni'}), 400

    titles = ai_processor.generate_titles(text)
    return jsonify({'titles': titles})


@app.route('/wordcloud', methods=['POST'])
def get_wordcloud_data():
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({'error': 'Aucun texte fourni'}), 400

    wordcloud_data = doc_processor.get_word_frequencies(text)
    return jsonify({'wordcloud': wordcloud_data})


# ==================== API HISTORIQUE ====================

@app.route('/api/history')
@login_required
def get_history():
    """Récupère l'historique des résumés de l'utilisateur"""
    user_id = get_current_user_id()
    history = db.get_user_history(user_id)
    return jsonify({'history': history})


@app.route('/api/history/<summary_id>', methods=['DELETE'])
@login_required
def delete_summary(summary_id):
    """Supprime un résumé de l'historique"""
    user_id = get_current_user_id()
    result = db.delete_summary(user_id, summary_id)
    return jsonify(result)


@app.route('/api/statistics')
@login_required
def get_statistics():
    """Récupère les statistiques de l'utilisateur"""
    user_id = get_current_user_id()
    stats = db.get_user_statistics(user_id)
    return jsonify(stats)


# Handler pour Vercel
def handler(request):
    return app(request)


if __name__ == '__main__':
    app.run(debug=True)
