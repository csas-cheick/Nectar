import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration Firebase via variables d'environnement
firebase_config = {
    "type": "service_account",
    "project_id": os.environ.get("FIREBASE_PROJECT_ID", ""),
    "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", ""),
    "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
    "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL", ""),
    "client_id": os.environ.get("FIREBASE_CLIENT_ID", ""),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.environ.get("FIREBASE_CERT_URL", "")
}

# Initialisation Firebase
try:
    # Essayer d'abord avec le fichier de credentials
    if os.path.exists('firebase-credentials.json'):
        cred = credentials.Certificate('firebase-credentials.json')
        firebase_admin.initialize_app(cred)
        print("Firebase initialisé avec le fichier de credentials")
    else:
        # Sinon utiliser les variables d'environnement
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
        print("Firebase initialisé avec les variables d'environnement")
except ValueError:
    # App déjà initialisée
    pass

# Référence Firestore
db = firestore.client()


def _get_timestamp():
    """Retourne le timestamp actuel"""
    return datetime.now().isoformat()


# ==================== USERS ====================

def create_user(username, email, password):
    """Crée un nouvel utilisateur"""
    password_hash = generate_password_hash(password)
    
    try:
        # Vérifier si l'email existe déjà
        users_ref = db.collection('users')
        email_query = users_ref.where('email', '==', email).limit(1).get()
        if len(list(email_query)) > 0:
            return {'success': False, 'error': 'Cet email est déjà utilisé'}
        
        # Vérifier si le username existe déjà
        username_query = users_ref.where('username', '==', username).limit(1).get()
        if len(list(username_query)) > 0:
            return {'success': False, 'error': 'Ce nom d\'utilisateur est déjà pris'}
        
        # Créer l'utilisateur
        user_data = {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'is_active': True,
            'created_at': _get_timestamp()
        }
        
        doc_ref = users_ref.add(user_data)
        return {'success': True, 'user_id': doc_ref[1].id}
    
    except Exception as e:
        return {'success': False, 'error': f'Erreur lors de la création du compte: {str(e)}'}


def authenticate_user(email, password):
    """Authentifie un utilisateur"""
    try:
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).where('is_active', '==', True).limit(1).get()
        
        users = list(query)
        if users:
            user_doc = users[0]
            user = user_doc.to_dict()
            
            if check_password_hash(user['password_hash'], password):
                return {
                    'success': True,
                    'user': {
                        'id': user_doc.id,
                        'username': user['username'],
                        'email': user['email'],
                        'created_at': user['created_at']
                    }
                }
        
        return {'success': False, 'error': 'Email ou mot de passe incorrect'}
    
    except Exception as e:
        return {'success': False, 'error': f'Erreur d\'authentification: {str(e)}'}


def get_user_by_id(user_id):
    """Récupère un utilisateur par son ID"""
    try:
        doc = db.collection('users').document(user_id).get()
        if doc.exists:
            user = doc.to_dict()
            return {
                'id': doc.id,
                'username': user['username'],
                'email': user['email'],
                'created_at': user['created_at']
            }
        return None
    except Exception:
        return None


# ==================== SUMMARIES ====================

def save_summary(user_id, filename, original_text, summary, original_words, summary_words, 
                 target_words, style, method, model):
    """Sauvegarde un résumé dans Firestore"""
    compression_rate = round((1 - summary_words / original_words) * 100, 1) if original_words > 0 else 0
    
    try:
        summary_data = {
            'user_id': user_id,
            'filename': filename,
            'original_text': original_text[:5000],
            'summary': summary,
            'original_words': original_words,
            'summary_words': summary_words,
            'target_words': target_words,
            'style': style,
            'method': method,
            'model': model,
            'compression_rate': compression_rate,
            'created_at': _get_timestamp()
        }
        
        doc_ref = db.collection('summaries').add(summary_data)
        return doc_ref[1].id
    except Exception as e:
        print(f"Erreur save_summary: {e}")
        return None


def get_summaries(user_id, limit=20, offset=0):
    """Récupère l'historique des résumés d'un utilisateur"""
    try:
        summaries_ref = db.collection('summaries')
        # Requête simple sans order_by pour éviter le besoin d'index composite
        query = summaries_ref.where('user_id', '==', user_id).get()
        
        results = []
        for doc in query:
            data = doc.to_dict()
            results.append({
                'id': doc.id,
                'created_at': data.get('created_at'),
                'filename': data.get('filename'),
                'summary': data.get('summary'),
                'original_words': data.get('original_words'),
                'summary_words': data.get('summary_words'),
                'style': data.get('style'),
                'method': data.get('method'),
                'compression_rate': data.get('compression_rate')
            })
        
        # Trier côté Python par date décroissante
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Appliquer limit et offset
        return results[offset:offset + limit]
    except Exception as e:
        print(f"Erreur get_summaries: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_summary_by_id(summary_id, user_id):
    """Récupère un résumé par son ID"""
    try:
        doc = db.collection('summaries').document(summary_id).get()
        if doc.exists:
            data = doc.to_dict()
            if data.get('user_id') == user_id:
                data['id'] = doc.id
                return data
        return None
    except Exception:
        return None


def delete_summary(summary_id, user_id):
    """Supprime un résumé"""
    try:
        doc_ref = db.collection('summaries').document(summary_id)
        doc = doc_ref.get()
        
        if doc.exists and doc.to_dict().get('user_id') == user_id:
            doc_ref.delete()
            return True
        return False
    except Exception:
        return False


# ==================== TRANSLATIONS ====================

def save_translation(user_id, source_text, translated_text, target_language):
    """Sauvegarde une traduction"""
    try:
        translation_data = {
            'user_id': user_id,
            'source_text': source_text[:5000],
            'translated_text': translated_text,
            'target_language': target_language,
            'created_at': _get_timestamp()
        }
        
        doc_ref = db.collection('translations').add(translation_data)
        return doc_ref[1].id
    except Exception as e:
        print(f"Erreur save_translation: {e}")
        return None


def get_translations(user_id, limit=20):
    """Récupère l'historique des traductions"""
    try:
        translations_ref = db.collection('translations')
        query = translations_ref.where('user_id', '==', user_id).get()
        
        results = []
        for doc in query:
            data = doc.to_dict()
            results.append({
                'id': doc.id,
                'created_at': data.get('created_at'),
                'source_text': data.get('source_text'),
                'translated_text': data.get('translated_text'),
                'target_language': data.get('target_language')
            })
        
        # Trier côté Python
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]
    except Exception as e:
        print(f"Erreur get_translations: {e}")
        return []


# ==================== ANALYSES ====================

def save_analysis(user_id, analysis_type, source_text, result):
    """Sauvegarde une analyse"""
    try:
        analysis_data = {
            'user_id': user_id,
            'analysis_type': analysis_type,
            'source_text_preview': source_text[:200],
            'result': result,
            'created_at': _get_timestamp()
        }
        
        doc_ref = db.collection('analyses').add(analysis_data)
        return doc_ref[1].id
    except Exception as e:
        print(f"Erreur save_analysis: {e}")
        return None


def get_analyses(user_id, analysis_type=None, limit=20):
    """Récupère l'historique des analyses"""
    try:
        analyses_ref = db.collection('analyses')
        query = analyses_ref.where('user_id', '==', user_id).get()
        
        results = []
        for doc in query:
            data = doc.to_dict()
            # Filtrer par type si spécifié
            if analysis_type and data.get('analysis_type') != analysis_type:
                continue
            results.append({
                'id': doc.id,
                'created_at': data.get('created_at'),
                'analysis_type': data.get('analysis_type'),
                'source_text_preview': data.get('source_text_preview'),
                'result': data.get('result')
            })
        
        # Trier côté Python
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]
    except Exception as e:
        print(f"Erreur get_analyses: {e}")
        return []


# ==================== Q&A ====================

def save_qa(user_id, document_preview, question, answer):
    """Sauvegarde une Q&A"""
    try:
        qa_data = {
            'user_id': user_id,
            'document_preview': document_preview[:200],
            'question': question,
            'answer': answer,
            'created_at': _get_timestamp()
        }
        
        doc_ref = db.collection('qa_history').add(qa_data)
        return doc_ref[1].id
    except Exception as e:
        print(f"Erreur save_qa: {e}")
        return None


def get_qa_history(user_id, limit=20):
    """Récupère l'historique des Q&A"""
    try:
        qa_ref = db.collection('qa_history')
        query = qa_ref.where('user_id', '==', user_id).get()
        
        results = []
        for doc in query:
            data = doc.to_dict()
            results.append({
                'id': doc.id,
                'created_at': data.get('created_at'),
                'document_preview': data.get('document_preview'),
                'question': data.get('question'),
                'answer': data.get('answer')
            })
        
        # Trier côté Python
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]
    except Exception as e:
        print(f"Erreur get_qa_history: {e}")
        return []


# ==================== FAVORITES ====================

def save_favorite(user_id, title, content, content_type='summary'):
    """Sauvegarde un favori"""
    try:
        favorite_data = {
            'user_id': user_id,
            'title': title,
            'content': content,
            'content_type': content_type,
            'created_at': _get_timestamp()
        }
        
        doc_ref = db.collection('favorites').add(favorite_data)
        return doc_ref[1].id
    except Exception as e:
        print(f"Erreur save_favorite: {e}")
        return None


def get_favorites(user_id, limit=50):
    """Récupère les favoris"""
    try:
        favorites_ref = db.collection('favorites')
        query = favorites_ref.where('user_id', '==', user_id).get()
        
        results = []
        for doc in query:
            data = doc.to_dict()
            results.append({
                'id': doc.id,
                'created_at': data.get('created_at'),
                'title': data.get('title'),
                'content': data.get('content'),
                'content_type': data.get('content_type')
            })
        
        # Trier côté Python
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]
        
        return results
    except Exception as e:
        print(f"Erreur get_favorites: {e}")
        return []


def delete_favorite(favorite_id, user_id):
    """Supprime un favori"""
    try:
        doc_ref = db.collection('favorites').document(favorite_id)
        doc = doc_ref.get()
        
        if doc.exists and doc.to_dict().get('user_id') == user_id:
            doc_ref.delete()
            return True
        return False
    except Exception:
        return False


# ==================== STATISTICS ====================

def get_global_stats(user_id):
    """Récupère les statistiques d'utilisation"""
    try:
        # Nombre total de résumés
        summaries = list(db.collection('summaries').where('user_id', '==', user_id).get())
        total_summaries = len(summaries)
        
        # Calculs sur les résumés
        total_words = 0
        total_compression = 0
        style_counts = {}
        
        for doc in summaries:
            data = doc.to_dict()
            total_words += data.get('original_words', 0)
            total_compression += data.get('compression_rate', 0)
            style = data.get('style', 'paragraph')
            style_counts[style] = style_counts.get(style, 0) + 1
        
        avg_compression = round(total_compression / total_summaries, 1) if total_summaries > 0 else 0
        favorite_style = max(style_counts, key=style_counts.get) if style_counts else 'paragraph'
        
        # Nombre de traductions
        translations = list(db.collection('translations').where('user_id', '==', user_id).get())
        total_translations = len(translations)
        
        # Nombre de Q&A
        qa = list(db.collection('qa_history').where('user_id', '==', user_id).get())
        total_qa = len(qa)
        
        return {
            'total_summaries': total_summaries,
            'total_words_processed': total_words,
            'total_translations': total_translations,
            'total_qa': total_qa,
            'avg_compression_rate': avg_compression,
            'favorite_style': favorite_style
        }
    except Exception as e:
        print(f"Erreur get_global_stats: {e}")
        return {
            'total_summaries': 0,
            'total_words_processed': 0,
            'total_translations': 0,
            'total_qa': 0,
            'avg_compression_rate': 0,
            'favorite_style': 'paragraph'
        }


def clear_all_history(user_id):
    """Efface tout l'historique d'un utilisateur"""
    try:
        collections = ['summaries', 'translations', 'analyses', 'qa_history']
        
        for collection_name in collections:
            docs = db.collection(collection_name).where('user_id', '==', user_id).get()
            for doc in docs:
                doc.reference.delete()
        
        return True
    except Exception as e:
        print(f"Erreur clear_all_history: {e}")
        return False


def init_db():
    """Fonction de compatibilité - Firebase n'a pas besoin d'initialisation de schéma"""
    print("Firebase Firestore prêt - pas besoin d'initialisation de schéma")


# Initialiser (pour compatibilité)
init_db()
