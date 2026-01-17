# 🤖 Nectar - AI Document Summarizer

<p align="center">
  <img src="images/nectar-preview.png" alt="Nectar App Preview" width="800"/>
</p>

<p align="center">
  <strong>Une application web intelligente pour extraire et résumer vos documents avec l'IA</strong>
</p>

<p align="center">
  <a href="#-fonctionnalités">Fonctionnalités</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-utilisation">Utilisation</a> •
  <a href="#-technologies">Technologies</a>
</p>

---

## ✨ Fonctionnalités

- 📄 **Upload de documents** : Support des formats PDF, DOCX et TXT
- 📊 **Statistiques détaillées** : Nombre de mots, caractères, phrases, temps de lecture
- ✂️ **Résumé personnalisable** : Choisissez le nombre de mots et le style
- 🤖 **IA intégrée** : Utilise OpenAI GPT-4o-mini pour des résumés de qualité
- 🌐 **Traduction** : Traduisez vos résumés en plusieurs langues
- 📋 **Export facile** : Copiez ou téléchargez votre résumé
- 👤 **Comptes utilisateurs** : Historique et statistiques personnalisés
- 🌙 **Mode sombre/clair** : Interface adaptative

## 🚀 Installation

### 1. Cloner le projet

```bash
git clone https://github.com/votre-username/nectar.git
cd nectar
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration des variables d'environnement

Copiez le fichier `.env.example` vers `.env` et remplissez vos clés :

```bash
cp .env.example .env
```

Modifiez le fichier `.env` avec vos propres clés :

```env
# Flask
FLASK_SECRET_KEY=votre-cle-secrete-unique

# OpenAI API
OPENAI_API_KEY=sk-votre-cle-openai

# Firebase Configuration
FIREBASE_PROJECT_ID=votre-project-id
FIREBASE_PRIVATE_KEY_ID=votre-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=votre-service-account@projet.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=votre-client-id
FIREBASE_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/votre-service-account
```

> ⚠️ **Important** : Ne commitez JAMAIS le fichier `.env` sur GitHub !

## 🎮 Utilisation

### Lancer l'application

```bash
python app.py
```

L'application sera accessible à : **http://localhost:5000**

### Comment utiliser

1. **Uploadez** un document (glisser-déposer ou clic)
2. **Cliquez** sur "Extraire le texte"
3. **Consultez** les statistiques du document
4. **Ajustez** le nombre de mots souhaité pour le résumé
5. **Cliquez** sur "Générer le résumé"
6. **Copiez** ou **téléchargez** le résumé

## 📁 Structure du projet

```
📦 AI-Document-Summarizer
├── 📄 app.py                 # Application Flask principale
├── 📄 document_processor.py  # Extraction de texte
├── 📄 summarizer.py          # Génération de résumés
├── 📁 templates/
│   └── 📄 index.html         # Interface utilisateur
├── 📁 static/
│   ├── 📄 style.css          # Styles CSS
│   └── 📄 script.js          # JavaScript frontend
├── 📄 requirements.txt       # Dépendances Python
└── 📄 README.md              # Documentation
```

## 🔧 Technologies utilisées

- **Backend** : Python, Flask
- **Frontend** : HTML5, CSS3, JavaScript
- **Extraction PDF** : PyPDF2, pdfplumber
- **Extraction DOCX** : python-docx
- **IA** : OpenAI GPT-3.5 (optionnel)

## 📝 API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/` | GET | Page d'accueil |
| `/upload` | POST | Upload et extraction de texte |
| `/summarize` | POST | Génération du résumé |

## 🎨 Captures d'écran

L'interface propose :
- Zone de drag & drop moderne
- Statistiques visuelles
- Slider pour ajuster le résumé
- Design sombre et élégant

## ⚙️ Configuration avancée

### Modifier la taille max des fichiers

Dans `app.py` :
```python
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
```

### Ajouter des formats de fichiers

Dans `app.py` :
```python
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt', 'rtf'}
```

## 🐛 Résolution de problèmes

### Erreur d'encodage avec les fichiers TXT
L'application essaie automatiquement plusieurs encodages (UTF-8, Latin-1, CP1252).

### PDF non supporté
Certains PDF scannés (images) ne peuvent pas être extraits. Utilisez un outil OCR au préalable.

### Résumé de mauvaise qualité sans OpenAI
La méthode extractive sélectionne les phrases importantes mais ne reformule pas. Pour de meilleurs résultats, configurez une clé API OpenAI.

## 📄 Licence

MIT License - Libre d'utilisation et de modification.

---

Fait avec ❤️ pour simplifier vos résumés de documents !
