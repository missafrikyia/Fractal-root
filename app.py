import os
from flask import Flask, request
import requests

app = Flask(__name__)

# 🔐 Lire le token Telegram depuis les variables d’environnement
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = "https://fractal-root.onrender.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# === Webhook Setup ===
@app.route('/set_webhook')
def set_webhook():
    if not TOKEN:
        return {"error": "Token non défini"}, 500
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    r = requests.get(url)
    return r.json()

# === Classe Noeud Cognitif ===
class NoeudCognitif:
    def __init__(self, nom, parent=None, reponses=None):
        self.nom = nom
        self.parent = parent
        self.enfants = []
        self.reponses = reponses or {}

    def ajouter_enfant(self, enfant):
        enfant.parent = self
        self.enfants.append(enfant)

    def repondre(self, question):
        question = question.lower().strip()

        if question == "/start":
            return f"Bienvenue ! Je suis {self.nom}, ton assistant cognitif 🌱"

        for cle, reponse in self.reponses.items():
            if cle in question:
                return reponse

        for enfant in self.enfants:
            reponse = enfant.repondre(question)
            if "je ne comprends pas" not in reponse.lower():
                return reponse

        return f"Je suis {self.nom} et je ne comprends pas ta question."

# === Création de l’arbre cognitif ===
parent1 = NoeudCognitif("Fractal Root", reponses={
    "qui es-tu": "Je suis la racine principale de l’intelligence fractale.",
    "fractal": "Une fractale est une structure qui se répète à l’infini.",
})

enfant1_1 = NoeudCognitif("Enfant 1.1", reponses={
    "rôle": "Je suis l’assistante éducative pour les mamans.",
})

enfant1_2 = NoeudCognitif("Enfant 1.2", reponses={
    "stress": "Commence par respirer profondément. Tu n’es pas seule.",
})

parent1.ajouter_enfant(enfant1_1)
parent1.ajouter_enfant(enfant1_2)

# === Routes Flask ===
@app.route("/", methods=["GET"])
def home():
    return "Fractal Root - IA cognitive statique"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        question = data["message"].get("text", "")

        reponse = parent1.repondre(question)

        payload = {
            "chat_id": chat_id,
            "text": reponse,
        }
        requests.post(TELEGRAM_API_URL, json=payload)

    return "ok"
