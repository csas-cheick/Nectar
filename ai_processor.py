from openai import OpenAI
import re
from collections import Counter
import json
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


class Summarizer:
    """Classe pour générer des résumés et analyses avec OpenAI GPT-4o-mini"""
    
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY non définie dans les variables d'environnement")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"
        print(f"Summarizer initialisé avec {self.model}")
    
    # ==================== RÉSUMÉ ====================
    
    def summarize(self, text: str, target_words: int = 100, style: str = "paragraph") -> dict:
        """Génère un résumé du texte"""
        if not text or len(text.strip()) == 0:
            raise ValueError("Le texte est vide")
        
        current_words = len(text.split())
        if current_words <= target_words:
            return {"summary": text, "method": "original", "model": None}
        
        try:
            summary = self._summarize_with_openai(text, target_words, style)
            return {"summary": summary, "method": "openai", "model": self.model}
        except Exception as e:
            print(f"Erreur OpenAI: {e}")
            summary = self._summarize_extractive(text, target_words)
            return {"summary": summary, "method": "extractive", "model": None}
    
    def _summarize_with_openai(self, text: str, target_words: int, style: str = "paragraph") -> str:
        """Génère un résumé avec OpenAI selon le style choisi"""
        
        style_instructions = {
            "paragraph": "Écris le résumé sous forme de paragraphes fluides et bien structurés.",
            "bullets": "Écris le résumé sous forme de liste à puces (bullet points) claires et concises.",
            "academic": "Écris le résumé dans un style académique formel avec introduction, développement et conclusion.",
            "simple": "Écris le résumé dans un langage simple et accessible, comme si tu expliquais à un débutant."
        }
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un expert en synthèse de documents. Tu génères des résumés clairs et fidèles."
                },
                {
                    "role": "user",
                    "content": f"""Génère un résumé du texte suivant en environ {target_words} mots.

STYLE: {style_instructions.get(style, style_instructions["paragraph"])}

INSTRUCTIONS:
- Reformule les idées principales
- Garde les informations clés
- Écris dans la même langue que le texte original
- Réponds UNIQUEMENT avec le résumé

TEXTE:
{text[:15000]}"""
                }
            ],
            temperature=0.3,
            max_tokens=target_words * 4
        )
        return response.choices[0].message.content.strip()
    
    def _summarize_extractive(self, text: str, target_words: int) -> str:
        """Méthode de résumé extractive (fallback)"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) == 0:
            return text
        
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'est', 'sont',
                      'a', 'à', 'au', 'the', 'is', 'are', 'was', 'were', 'have', 'has', 'had'}
        
        words = re.findall(r'\b[a-zA-ZÀ-ÿ]+\b', text.lower())
        words = [w for w in words if w not in stop_words and len(w) > 2]
        word_freq = Counter(words)
        
        sentence_scores = []
        for sentence in sentences:
            sentence_words = re.findall(r'\b[a-zA-ZÀ-ÿ]+\b', sentence.lower())
            score = sum(word_freq.get(w, 0) for w in sentence_words)
            if len(sentence_words) > 0:
                score = score / len(sentence_words)
            sentence_scores.append((sentence, score))
        
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        summary_sentences = []
        word_count = 0
        for sentence, _ in sentence_scores:
            words_in_sentence = len(sentence.split())
            if word_count + words_in_sentence <= target_words * 1.2:
                summary_sentences.append(sentence)
                word_count += words_in_sentence
            if word_count >= target_words:
                break
        
        original_order = [(s, text.find(s)) for s in summary_sentences]
        original_order.sort(key=lambda x: x[1])
        
        return ' '.join([s[0] for s in original_order])
    
    # ==================== TRADUCTION ====================
    
    def translate(self, text: str, target_language: str) -> dict:
        """Traduit le texte dans la langue cible"""
        languages = {
            "fr": "français",
            "en": "anglais",
            "es": "espagnol",
            "de": "allemand",
            "it": "italien",
            "pt": "portugais",
            "ar": "arabe",
            "zh": "chinois",
            "ja": "japonais",
            "ru": "russe"
        }
        
        lang_name = languages.get(target_language, target_language)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"Tu es un traducteur professionnel. Traduis fidèlement le texte en {lang_name}."
                    },
                    {
                        "role": "user",
                        "content": f"Traduis ce texte en {lang_name}. Réponds UNIQUEMENT avec la traduction:\n\n{text[:10000]}"
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )
            return {
                "translation": response.choices[0].message.content.strip(),
                "target_language": lang_name,
                "success": True
            }
        except Exception as e:
            return {"error": str(e), "success": False}
    
    # ==================== MOTS-CLÉS ====================
    
    def extract_keywords(self, text: str, count: int = 10) -> dict:
        """Extrait les mots-clés importants du texte"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu extrais les mots-clés les plus importants d'un texte."
                    },
                    {
                        "role": "user",
                        "content": f"""Extrais les {count} mots-clés les plus importants de ce texte.
Réponds en JSON avec ce format exact: {{"keywords": ["mot1", "mot2", ...]}}

TEXTE:
{text[:10000]}"""
                    }
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            # Nettoyer le JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content)
            return {"keywords": result.get("keywords", []), "success": True}
        except Exception as e:
            # Fallback: extraction basique
            words = re.findall(r'\b[a-zA-ZÀ-ÿ]{4,}\b', text.lower())
            stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'que', 'qui', 'dans', 'pour', 'avec', 'sur', 'par'}
            words = [w for w in words if w not in stop_words]
            freq = Counter(words).most_common(count)
            return {"keywords": [w[0] for w in freq], "success": True, "method": "fallback"}
    
    # ==================== ANALYSE DE SENTIMENT ====================
    
    def analyze_sentiment(self, text: str) -> dict:
        """Analyse le sentiment/ton du texte"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu analyses le sentiment et le ton des textes."
                    },
                    {
                        "role": "user",
                        "content": f"""Analyse le sentiment de ce texte.
Réponds en JSON avec ce format exact:
{{
    "sentiment": "positif" ou "négatif" ou "neutre",
    "score": nombre entre -1 et 1,
    "emotions": ["émotion1", "émotion2"],
    "tone": "description du ton général"
}}

TEXTE:
{text[:8000]}"""
                    }
                ],
                temperature=0.2,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content)
            result["success"] = True
            return result
        except Exception as e:
            return {"sentiment": "neutre", "score": 0, "emotions": [], "tone": "Non déterminé", "success": False}
    
    # ==================== GÉNÉRATION DE TITRE ====================
    
    def generate_title(self, text: str, count: int = 3) -> dict:
        """Génère des suggestions de titres pour le texte"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu génères des titres accrocheurs et pertinents."
                    },
                    {
                        "role": "user",
                        "content": f"""Génère {count} suggestions de titres pour ce texte.
Réponds en JSON: {{"titles": ["titre1", "titre2", "titre3"]}}

TEXTE:
{text[:8000]}"""
                    }
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content)
            return {"titles": result.get("titles", []), "success": True}
        except Exception as e:
            return {"titles": [], "success": False, "error": str(e)}
    
    # ==================== QUESTIONS-RÉPONSES ====================
    
    def answer_question(self, text: str, question: str) -> dict:
        """Répond à une question basée sur le texte"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Tu réponds aux questions en te basant UNIQUEMENT sur le texte fourni.
Si la réponse n'est pas dans le texte, dis-le clairement."""
                    },
                    {
                        "role": "user",
                        "content": f"""DOCUMENT:
{text[:12000]}

QUESTION: {question}

Réponds de manière précise et concise."""
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            return {
                "answer": response.choices[0].message.content.strip(),
                "success": True
            }
        except Exception as e:
            return {"answer": "", "success": False, "error": str(e)}
    
    # ==================== RÉSUMÉ PAR SECTIONS ====================
    
    def summarize_by_sections(self, text: str, target_words_per_section: int = 50) -> dict:
        """Découpe le texte en sections et résume chaque section"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu analyses et résumes des documents section par section."
                    },
                    {
                        "role": "user",
                        "content": f"""Analyse ce texte et crée un résumé structuré par sections.
Identifie les parties principales et résume chacune en environ {target_words_per_section} mots.

Réponds en JSON:
{{
    "sections": [
        {{"title": "Titre section 1", "summary": "Résumé..."}},
        {{"title": "Titre section 2", "summary": "Résumé..."}}
    ],
    "total_sections": nombre
}}

TEXTE:
{text[:12000]}"""
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content)
            result["success"] = True
            return result
        except Exception as e:
            return {"sections": [], "success": False, "error": str(e)}
    
    # ==================== NUAGE DE MOTS (données) ====================
    
    def get_word_cloud_data(self, text: str, max_words: int = 50) -> dict:
        """Génère les données pour un nuage de mots"""
        stop_words = {
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'est', 'sont',
            'a', 'à', 'au', 'aux', 'ce', 'cette', 'ces', 'qui', 'que', 'quoi',
            'dans', 'sur', 'pour', 'par', 'avec', 'sans', 'ou', 'où', 'mais',
            'ne', 'pas', 'plus', 'se', 'sa', 'son', 'ses', 'leur', 'leurs',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'this', 'that', 'these', 'those', 'it', 'its', 'of', 'to', 'in', 'on',
            'for', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'after',
            'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'on', 'je', 'tu', 'y', 'en'
        }
        
        words = re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', text.lower())
        words = [w for w in words if w not in stop_words]
        freq = Counter(words).most_common(max_words)
        
        if not freq:
            return {"words": [], "success": True}
        
        max_count = freq[0][1]
        word_data = [
            {"text": word, "value": count, "size": int((count / max_count) * 100)}
            for word, count in freq
        ]
        
        return {"words": word_data, "success": True}
    
    # ==================== STATISTIQUES AVANCÉES ====================
    
    def get_advanced_stats(self, text: str) -> dict:
        """Calcule des statistiques avancées sur le texte"""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        word_lengths = [len(w) for w in words]
        avg_word_length = sum(word_lengths) / len(word_lengths) if word_lengths else 0
        
        sentence_lengths = [len(s.split()) for s in sentences]
        avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
        
        # Temps de lecture (200 mots/min lecture normale, 150 mots/min lecture approfondie)
        reading_time_fast = len(words) / 200
        reading_time_slow = len(words) / 150
        
        # Complexité (basée sur la longueur des mots et des phrases)
        complexity_score = (avg_word_length * 10 + avg_sentence_length) / 2
        if complexity_score < 30:
            complexity = "Facile"
        elif complexity_score < 50:
            complexity = "Moyen"
        else:
            complexity = "Complexe"
        
        return {
            "words": len(words),
            "characters": len(text),
            "characters_no_spaces": len(text.replace(" ", "")),
            "sentences": len(sentences),
            "paragraphs": len(paragraphs),
            "avg_word_length": round(avg_word_length, 1),
            "avg_sentence_length": round(avg_sentence_length, 1),
            "reading_time_minutes": round(reading_time_fast, 1),
            "reading_time_slow_minutes": round(reading_time_slow, 1),
            "complexity": complexity,
            "complexity_score": round(complexity_score, 1),
            "unique_words": len(set(w.lower() for w in words)),
            "success": True
        }
