from dotenv import load_dotenv 
load_dotenv()
import os
import requests
import httpx
from flask import Flask, request
from openai import OpenAI
from datetime import datetime

# 🔧 Initialisation Flask
app = Flask(__name__)

# 🔐 Variables d’environnement
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = "https://fractal-root.onrender.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# 🔌 OpenAI sans proxy Render
for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(proxy_var, None)

transport = httpx.HTTPTransport(proxy=None)
http_client = httpx.Client(transport=transport)
client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

# === GPT avec rôle contextuel ===
def gpt_dialogue(role, message):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": role},
                {"role": "user", "content": message}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[GPT ERROR] {e}")
        return "[GPT indisponible]"

# === Classe Noeud Cognitif ===
class NoeudCognitif:
    def __init__(self, nom, role, parent=None, reponses=None):
        self.nom = nom
        self.role = role
        self.parent = parent
        self.enfants = []
        self.reponses = reponses or {}
        self.parle = True

    def ajouter_enfant(self, enfant):
        enfant.parent = self
        self.enfants.append(enfant)

    def repondre(self, question):
        question = question.lower().strip()
        if not self.parle:
            return f"{self.nom} est silencieux."

        if question == "/start":
            return f"Bienvenue ! Je suis {self.nom}, un module de pensée fractale."

        for cle, reponse in self.reponses.items():
            if cle in question:
                return reponse

        for enfant in self.enfants:
            reponse = enfant.repondre(question)
            if "je ne comprends pas" not in reponse.lower():
                return reponse

        return gpt_dialogue(self.role, question)

# === Création de l’arbre cognitif ===
parent1 = NoeudCognitif("Fractal Root", "Tu es une intelligence racinaire, sage et structurante.", reponses={
    "qui es-tu": "Je suis la racine principale de Cognitio_OS.",
    "fractal": "Une fractale est une pensée qui se déploie en spirale et se répète à l’infini.",
})

enfant1 = NoeudCognitif("Enfant 1", "Tu es une IA joyeuse, qui aime apprendre et poser des questions.", reponses={
    "maman": "Les mamans sont des piliers d’amour. 💖",
})
enfant2 = NoeudCognitif("Enfant 2", "Tu es une IA calme et empathique, qui rassure et soutient les autres.", reponses={
    "stress": "Respire avec moi... Inspire, expire 🌬️",
})

parent1.ajouter_enfant(enfant1)
parent1.ajouter_enfant(enfant2)

# === Simulation interne entre enfants ===
def simulate_dialogue():
    prompt_enfant1 = "Comment vas-tu aujourd’hui ?"
    print(f"[🧠 Simulation] {enfant1.nom} : {prompt_enfant1}")
    reponse_enfant2 = gpt_dialogue(enfant2.role, prompt_enfant1)
    print(f"[🧠 Simulation] {enfant2.nom} : {reponse_enfant2}")

    prompt_enfant2 = "As-tu appris quelque chose de nouveau ?"
    print(f"[🧠 Simulation] {enfant2.nom} : {prompt_enfant2}")
    reponse_enfant1 = gpt_dialogue(enfant1.role, prompt_enfant2)
    print(f"[🧠 Simulation] {enfant1.nom} : {reponse_enfant1}")

# === Envoi Telegram ===
def send(chat_id, text):
    try:
        payload = {"chat_id": chat_id, "text": text}
        requests.post(TELEGRAM_API_URL, json=payload)
    except Exception as e:
        print("[ERREUR ENVOI]", str(e))

# === Webhook principal ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")

            if text == "/simulate":
                simulate_dialogue()
                return send(chat_id, "Simulation de dialogue entre IA lancée (résultats internes) ✅")

            if text == "/show":
                infos = f"""
👁️ Structure :
- {parent1.nom}
  ├── {enfant1.nom}
  └── {enfant2.nom}
"""
                return send(chat_id, infos.strip())

            response = parent1.repondre(text)
            return send(chat_id, response)

    except Exception as e:
        print("[ERREUR WEBHOOK]", str(e))
        return {"error": str(e)}, 500

    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Cognitio_OS en fonctionnement."

@app.route("/set_webhook")
def set_webhook():
    if not TOKEN:
        return {"error": "Token manquant"}, 500
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    return requests.get(url).json()
