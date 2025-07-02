import os
import requests
from flask import Flask, request

# Initialisation de l'app Flask
app = Flask(__name__)

# === Noeud Cognitif Parent 1 ===
class NoeudCognitif:
    def __init__(self, nom, parent=None):
        self.nom = nom
        self.parent = parent
        self.enfants = []

    def ajouter_enfant(self, enfant):
        enfant.parent = self
        self.enfants.append(enfant)

    def repondre(self, question):
        question = question.lower()
        if "qui est ton parent" in question:
            if self.parent:
                return f"Je suis {self.nom}, mon parent est {self.parent.nom}."
            else:
                return f"Je suis {self.nom}, je n'ai pas de parent."
        return f"Je suis {self.nom} et je ne comprends pas ta question."

# Création de l’arbre de base
parent1 = NoeudCognitif("Fractal Root")

# === Variables d'environnement ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# === Route d'accueil ===
@app.route("/", methods=["GET"])
def home():
    return "Fractal Root - IA statique opérationnelle."

# === Route pour configurer le webhook ===
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    webhook_url = "https://fractal-root.onrender.com/webhook"
    url = f"{TELEGRAM_API_URL}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    return f"Webhook set: {response.text}"

# === Route Webhook Telegram ===
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        question = data["message"].get("text", "")
        réponse = parent1.repondre(question)

        send_url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": réponse
        }
        requests.post(send_url, json=payload)

    return "OK", 200
