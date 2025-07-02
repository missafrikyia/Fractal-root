import os
from flask import Flask, request
import requests

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
                return f"Je suis {self.nom} et mon parent est {self.parent.nom}."
            else:
                return f"Je suis {self.nom} et je suis la racine (aucun parent)."
        else:
            return f"Je suis {self.nom}. Pose-moi une autre question !"

# Création de l’arbre de base
parent1 = NoeudCognitif("Fractal Root")

# === Webhook Telegram ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

@app.route("/", methods=["GET"])
def home():
    return "Fractal Root - IA statique prête."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        question = data["message"].get("text", "")
        reponse = parent1.repondre(question)

        payload = {
            "chat_id": chat_id,
            "text": reponse
        }
        requests.post(TELEGRAM_API_URL, json=payload)

    return {"status": "ok"}

if __name__ == "__main__":
    app.run(debug=True)
