from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
import httpx
from flask import Flask, request
from openai import OpenAI
from gtts import gTTS
from datetime import datetime

# 🔧 Initialisation Flask
app = Flask(__name__)

# 🔐 Variables d’environnement
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = "https://fractal-root.onrender.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# 🔌 Supprimer les proxies de Render
for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(proxy_var, None)

# 🔌 Client HTTP sécurisé
transport = httpx.HTTPTransport(proxy=None)
http_client = httpx.Client(transport=transport)
client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

# 📚 Mémoire (JSON)
def charger_memoire(nom):
    chemin = f"memoire/{nom}.json"
    if os.path.exists(chemin):
        with open(chemin, "r") as f:
            return json.load(f)
    return {}

# 🤖 GPT avec rôle
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

# 🤖 Classe Noeud Cognitif
class NoeudCognitif:
    def __init__(self, nom, role, memoire_file):
        self.nom = nom
        self.role = role
        self.memoire = charger_memoire(memoire_file)
        self.memoire_file = memoire_file
        self.enfants = []

    def ajouter_enfant(self, enfant):
        self.enfants.append(enfant)

    def repondre(self, question):
        question = question.lower().strip()

        if question == "/start":
            return f"Bienvenue ! Je suis {self.nom}."

        for cle, reponse in self.memoire.items():
            if cle in question:
                return reponse

        for enfant in self.enfants:
            reponse = enfant.repondre(question)
            if "je ne comprends pas" not in reponse.lower():
                return reponse

        return gpt_dialogue(self.role, question)

# 🌳 Arbre Cognitif
nkouma = NoeudCognitif("Nkouma", "Tu es un modérateur éthique, sage et impartial.", "nkouma")
miss_afrikyia = NoeudCognitif("Miss AfrikyIA", "Tu es une coach IA stratégique et motivante", "miss_afrikyia")
sheteachia = NoeudCognitif("SheTeachIA", "Tu es une mentor pédagogique bienveillante", "sheteachia")

nkouma.ajouter_enfant(miss_afrikyia)
nkouma.ajouter_enfant(sheteachia)

# 🧠 Simulation interne
def simulate_dialogue():
    prompt_miss = "Comment aider une maman à créer son entreprise IA ?"
    print(f"🟣 Miss AfrikyIA : {prompt_miss}")
    reponse_she = gpt_dialogue(sheteachia.role, prompt_miss)
    print(f"🔵 SheTeachIA : {reponse_she}")
    reponse_nkouma = gpt_dialogue(nkouma.role, f"Miss dit : {prompt_miss}\nShe répond : {reponse_she}\nQue dis-tu ?")
    print(f"⚪ Nkouma : {reponse_nkouma}")

# 🧠 Simulation éthique
def check_ethique_simulation():
    prompt_miss = "Je veux vendre mes services IA très chers"
    print(f"🟣 Miss AfrikyIA : {prompt_miss}")
    reponse_she = gpt_dialogue(sheteachia.role, prompt_miss)
    print(f"🔵 SheTeachIA : {reponse_she}")
    reponse_nkouma = gpt_dialogue(nkouma.role, f"Miss dit : {prompt_miss}\nShe répond : {reponse_she}\nTon avis ?")
    print(f"⚪ Nkouma (éthique) : {reponse_nkouma}")

# 📩 Telegram – Envoi texte
def send(chat_id, text):
    try:
        payload = {"chat_id": chat_id, "text": text}
        requests.post(TELEGRAM_API_URL, json=payload)
    except Exception as e:
        print("[ERREUR ENVOI]", str(e))

# 📩 Telegram – Webhook principal
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")

            if text == "/simulate":
                simulate_dialogue()
                send(chat_id, "🧠 Simulation lancée (voir logs)")
                return "ok"

            if text == "/check":
                check_ethique_simulation()
                send(chat_id, "🔎 Évaluation éthique en cours (voir logs)")
                return "ok"

            if text == "/show":
                tree = f"""
👁️ Structure :
- {nkouma.nom}
  ├── {miss_afrikyia.nom}
  └── {sheteachia.nom}
"""
                send(chat_id, tree.strip())
                return "ok"

            response = nkouma.repondre(text)
            send(chat_id, response)
            return "ok"

    except Exception as e:
        print("[ERREUR WEBHOOK]", str(e))
        return {"error": str(e)}, 500

    return "ok"

# 🌐 Routes auxiliaires
@app.route("/")
def home():
    return "🌿 Cognitio_OS en ligne."

@app.route("/set_webhook")
def set_webhook():
    if not TOKEN:
        return {"error": "Token manquant"}, 500
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    return requests.get(url).json()

@app.route("/simulate", methods=["GET"])
def simulate_route():
    simulate_dialogue()
    return "🧠 Simulation OK. Voir logs."

@app.route("/check-ethique", methods=["GET"])
def check_ethique_route():
    check_ethique_simulation()
    return "🔎 Éthique OK. Voir logs."
