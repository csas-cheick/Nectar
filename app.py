from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
from functools import wraps
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from document_processor import DocumentProcessor
from ai_processor import Summarizer
import database as db

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
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
    return send_file('N.svg', mimetype='image/svg+xml')


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
        
        result = db.authenticate_user(email, password)
        
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
    """Déconnexion"""
    session.clear()
    return jsonify({'success': True, 'message': 'Déconnexion réussie'})


@app.route('/auth/me', methods=['GET'])
def get_current_user():
    """Récupère l'utilisateur actuellement connecté"""
    if 'user_id' in session:
        user = db.get_user_by_id(session['user_id'])
        if user:
            return jsonify({'success': True, 'user': user, 'logged_in': True})
    return jsonify({'success': True, 'user': None, 'logged_in': False})


# ==================== PAGES ====================

@app.route('/')
def index():
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
def documentation():
    return render_template('documentation.html')


# ==================== UPLOAD ====================

@app.route('/upload', methods=['POST'])
def upload_file():
    global current_filename
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Aucun fichier sélectionné'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Type de fichier non autorisé'}), 400
        
        filename = secure_filename(file.filename)
        current_filename = filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        text = doc_processor.extract_text(filepath)
        stats = doc_processor.get_text_stats(text)
        
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'text': text,
            'stats': stats,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== RÉSUMÉ ====================

@app.route('/summarize', methods=['POST'])
def summarize_text():
    global current_filename
    try:
        data = request.get_json()
        user_id = get_current_user_id()  # None si non connecté
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Texte manquant'}), 400
        
        text = data['text']
        target_words = data.get('target_words', 100)
        style = data.get('style', 'paragraph')
        filename = data.get('filename', current_filename or 'Sans titre')
        
        result = ai_processor.summarize(text, target_words, style)
        summary_stats = doc_processor.get_text_stats(result['summary'])
        
        # Sauvegarder dans la base de données SEULEMENT si connecté
        summary_id = None
        if user_id:
            summary_id = db.save_summary(
                user_id=user_id,
                filename=filename,
                original_text=text,
                summary=result['summary'],
                original_words=len(text.split()),
                summary_words=summary_stats['word_count'],
                target_words=target_words,
                style=style,
                method=result['method'],
                model=result['model']
            )
        
        return jsonify({
            'success': True,
            'summary': result['summary'],
            'summary_stats': summary_stats,
            'method': result['method'],
            'model': result['model'],
            'summary_id': summary_id,
            'saved': user_id is not None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== TRADUCTION ====================

@app.route('/translate', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        user_id = get_current_user_id()  # None si non connecté
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Texte manquant'}), 400
        
        text = data['text']
        target_language = data.get('target_language', 'en')
        
        result = ai_processor.translate(text, target_language)
        
        # Sauvegarder la traduction SEULEMENT si connecté
        if result.get('success') and user_id:
            db.save_translation(user_id, text, result['translation'], target_language)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== MOTS-CLÉS ====================

@app.route('/keywords', methods=['POST'])
def extract_keywords():
    try:
        data = request.get_json()
        user_id = get_current_user_id()  # None si non connecté
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Texte manquant'}), 400
        
        text = data['text']
        count = data.get('count', 10)
        
        result = ai_processor.extract_keywords(text, count)
        
        # Sauvegarder l'analyse SEULEMENT si connecté
        if result.get('success') and user_id:
            db.save_analysis(user_id, 'keywords', text, result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== SENTIMENT ====================

@app.route('/sentiment', methods=['POST'])
def analyze_sentiment():
    try:
        data = request.get_json()
        user_id = get_current_user_id()  # None si non connecté
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Texte manquant'}), 400
        
        text = data['text']
        result = ai_processor.analyze_sentiment(text)
        
        # Sauvegarder l'analyse SEULEMENT si connecté
        if result.get('success') and user_id:
            db.save_analysis(user_id, 'sentiment', text, result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== TITRES ====================

@app.route('/generate-title', methods=['POST'])
def generate_title():
    try:
        data = request.get_json()
        user_id = get_current_user_id()  # None si non connecté
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Texte manquant'}), 400
        
        text = data['text']
        count = data.get('count', 3)
        
        result = ai_processor.generate_title(text, count)
        
        # Sauvegarder l'analyse SEULEMENT si connecté
        if result.get('success') and user_id:
            db.save_analysis(user_id, 'titles', text, result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== Q&A ====================

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        user_id = get_current_user_id()  # None si non connecté
        
        if not data or 'text' not in data or 'question' not in data:
            return jsonify({'error': 'Texte ou question manquant'}), 400
        
        text = data['text']
        question = data['question']
        
        result = ai_processor.answer_question(text, question)
        
        # Sauvegarder la Q&A SEULEMENT si connecté
        if result.get('success') and user_id:
            db.save_qa(user_id, text, question, result['answer'])
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== RÉSUMÉ PAR SECTIONS ====================

@app.route('/summarize-sections', methods=['POST'])
def summarize_sections():
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Texte manquant'}), 400
        
        text = data['text']
        words_per_section = data.get('words_per_section', 50)
        
        result = ai_processor.summarize_by_sections(text, words_per_section)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== NUAGE DE MOTS ====================

@app.route('/wordcloud', methods=['POST'])
def get_wordcloud():
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Texte manquant'}), 400
        
        text = data['text']
        max_words = data.get('max_words', 50)
        
        result = ai_processor.get_word_cloud_data(text, max_words)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== STATISTIQUES AVANCÉES ====================

@app.route('/advanced-stats', methods=['POST'])
def get_advanced_stats():
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Texte manquant'}), 400
        
        text = data['text']
        result = ai_processor.get_advanced_stats(text)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== HISTORIQUE ====================

@app.route('/api/history', methods=['GET'])
def get_history():
    """Récupère l'historique des résumés de l'utilisateur"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'history': [], 'success': True})
        summaries = db.get_summaries(user_id, limit=20)
        print(f"Historique récupéré pour user {user_id}: {len(summaries)} résumés")
        return jsonify({'history': summaries, 'success': True})
    except Exception as e:
        print(f"Erreur get_history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/history/<summary_id>', methods=['GET'])
def get_history_item(summary_id):
    """Récupère un résumé spécifique"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'Non connecté', 'success': False}), 401
        summary = db.get_summary_by_id(summary_id, user_id)
        if summary:
            return jsonify({'summary': summary, 'success': True})
        return jsonify({'error': 'Résumé non trouvé', 'success': False}), 404
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/history/<summary_id>', methods=['DELETE'])
def delete_history_item(summary_id):
    """Supprime un résumé de l'historique"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'Non connecté', 'success': False}), 401
        if db.delete_summary(summary_id, user_id):
            return jsonify({'success': True})
        return jsonify({'error': 'Résumé non trouvé', 'success': False}), 404
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Efface tout l'historique de l'utilisateur"""
    try:
        user_id = get_current_user_id()
        db.clear_all_history(user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== FAVORIS ====================

@app.route('/favorites', methods=['GET'])
@login_required
def get_favorites():
    """Récupère les favoris de l'utilisateur"""
    try:
        user_id = get_current_user_id()
        favorites = db.get_favorites(user_id)
        return jsonify({'favorites': favorites, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/favorites', methods=['POST'])
@login_required
def add_favorite():
    """Ajoute un favori"""
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        title = data.get('title', 'Sans titre')
        content = data.get('content', '')
        content_type = data.get('content_type', 'summary')
        
        favorite_id = db.save_favorite(user_id, title, content, content_type)
        return jsonify({'success': True, 'favorite_id': favorite_id})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/favorites/<int:favorite_id>', methods=['DELETE'])
@login_required
def delete_favorite(favorite_id):
    """Supprime un favori"""
    try:
        user_id = get_current_user_id()
        if db.delete_favorite(favorite_id, user_id):
            return jsonify({'success': True})
        return jsonify({'error': 'Favori non trouvé', 'success': False}), 404
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== STATISTIQUES GLOBALES ====================

@app.route('/stats', methods=['GET'])
@login_required
def get_global_stats():
    """Récupère les statistiques d'utilisation de l'utilisateur"""
    try:
        user_id = get_current_user_id()
        stats = db.get_global_stats(user_id)
        return jsonify({'stats': stats, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== Q&A HISTORY ====================

@app.route('/qa-history', methods=['GET'])
@login_required
def get_qa_history():
    """Récupère l'historique des Q&A de l'utilisateur"""
    try:
        user_id = get_current_user_id()
        qa_list = db.get_qa_history(user_id)
        return jsonify({'history': qa_list, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# ==================== EXPORT ====================

@app.route('/export-pdf', methods=['POST'])
def export_pdf():
    # Pour l'export PDF, on retourne un HTML formaté que le front peut imprimer
    try:
        data = request.get_json()
        
        title = data.get('title', 'Document')
        content = data.get('content', '')
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Georgia, serif; line-height: 1.8; padding: 40px; max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; border-bottom: 2px solid #7c3aed; padding-bottom: 10px; }}
        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
        .content {{ text-align: justify; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="meta">Généré par Nectar - {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    <div class="content">{content}</div>
</body>
</html>"""
        
        return jsonify({'html': html, 'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
