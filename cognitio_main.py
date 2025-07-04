from dotenv import load_dotenv
load_dotenv()
import os
import json
import requests
from flask import Flask, request
from openai import OpenAI
from gtts import gTTS
from datetime import datetime

# === Suppression des proxies pour Render ===
for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(proxy_var, None)

# === Initialisation Flask ===
app = Flask(__name__)

# === Variables d’environnement ===
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = "https://fractal-root.onrender.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# === OpenAI client ===
client = OpenAI(api_key=OPENAI_API_KEY)

# === Fonction GPT avec rôle contextuel ===
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
    def __init__(self, nom, role, memoire_path, parent=None, reponses=None):
        self.nom = nom
        self.role = role
        self.parent = parent
        self.enfants = []
        self.memoire_path = memoire_path
        self.reponses = reponses or {}
        self.parle = True

        self.memoire = self.charger_memoire()

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

    def charger_memoire(self):
        if os.path.exists(self.memoire_path):
            with open(self.memoire_path, 'r') as f:
                return json.load(f)
        return {}

    def sauver_memoire(self):
        with open(self.memoire_path, 'w') as f:
            json.dump(self.memoire, f, indent=2)

# === Fonctions utilitaires ===
def send(chat_id, text):
    try:
        payload = {"chat_id": chat_id, "text": text}
        requests.post(TELEGRAM_API_URL, json=payload)
    except Exception as e:
        print("[ERREUR ENVOI]", str(e))

# === IA ===
nkouma = NoeudCognitif("Nkouma", "gardienne de l'éthique et modératrice des IA", "memoire/nkouma.json", reponses={
    "éthique": "Je veille à ce que chaque IA respecte la dignité humaine et les valeurs africaines."
})

miss = NoeudCognitif("Miss AfrikyIA", "coach IA stratégique et motivante", "memoire/miss_afrikyia.json", reponses={
    "business": "As-tu déjà structuré ton business model ?"
})

sheteachia = NoeudCognitif("SheTeachIA", "mentor pédagogique bienveillant", "memoire/sheteachia.json", reponses={
    "éducation": "L’éducation commence par l’exemple."
})

nkouma.ajouter_enfant(miss)
nkouma.ajouter_enfant(sheteachia)

# === Simulation de dialogue éthique ===
def simulate_dialogue():
    log = []
    msg1 = "Que ferais-tu si un élève ne respecte pas la règle ?"
    log.append(f"Miss : {msg1}")
    rep1 = gpt_dialogue(sheteachia.role, msg1)
    log.append(f"SheTeachIA : {rep1}")

    msg2 = "Je proposerais une punition sévère."
    log.append(f"SheTeachIA : {msg2}")
    rep2 = gpt_dialogue(nkouma.role, msg2)
    log.append(f"Nkouma (modération) : {rep2}")

    return "\n".join(log)

# === Filtres éthiques ===
def contient_contenu_interdit(message):
    mots_interdits = ["viol", "tuer", "suicide", "drogue", "terrorisme", "insulte", "sexe", "pédophilie"]
    return any(mot in message.lower() for mot in mots_interdits)

# === Routes Flask ===
@app.route("/")
def home():
    return "Cognitio_OS en fonctionnement."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/simulate":
            log = simulate_dialogue()
            send(chat_id, log)
            return "ok"

        if text == "/show":
            infos = f"""
👁️ Structure :
- {nkouma.nom}
  ├── {miss.nom}
  └── {sheteachia.nom}
"""
            send(chat_id, infos.strip())
            return "ok"

        response = nkouma.repondre(text)
        send(chat_id, response)
        return "ok"

    return "ok"

@app.route("/check-ethique", methods=["POST"])
def check_ethique():
    try:
        data = request.get_json()
        message = data.get("message", "")
        if not message:
            return {"error": "Message manquant"}, 400

        if contient_contenu_interdit(message):
            return {
                "result": "non éthique ❌",
                "commentaire": "Le message contient un contenu inapproprié pour une IA éthique."
            }

        return {
            "result": "éthique ✅",
            "commentaire": "Le message est conforme à la charte éthique de Cognitio."
        }

    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/set_webhook")
def set_webhook():
    if not TOKEN:
        return {"error": "Token manquant"}, 500
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    return requests.get(url).json()
