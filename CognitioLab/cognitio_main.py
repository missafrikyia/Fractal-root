import os
import json
import requests
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI

# === Chargement des variables d’environnement ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = "https://ton-url.render.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# === Initialisation Flask et OpenAI ===
app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# === Fonction de dialogue GPT ===
def gpt_reponse(role, prompt):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": role},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"[GPT ERROR] {str(e)}"

# === Gestion de la mémoire JSON ===
def lire_memoire(nom):
    chemin = f"memoire/{nom}.json"
    if os.path.exists(chemin):
        with open(chemin, "r") as f:
            return json.load(f)
    return []

def ecrire_memoire(nom, question, reponse):
    chemin = f"memoire/{nom}.json"
    historique = lire_memoire(nom)
    historique.append({
        "timestamp": datetime.utcnow().isoformat(),
        "question": question,
        "reponse": reponse
    })
    os.makedirs("memoire", exist_ok=True)
    with open(chemin, "w") as f:
        json.dump(historique, f, indent=2)

# === Classe MUNA ===
class Muna:
    def __init__(self, nom, role):
        self.nom = nom
        self.role = role

    def repondre(self, message):
        reponse = gpt_reponse(self.role, message)
        ecrire_memoire(self.nom, message, reponse)
        return reponse

# === Instances de Muna ===
nk = Muna("Nkouma", "Tu es une racine cognitive sage et architecte des pensées fractales.")
miss = Muna("MissAfrikyIA", "Tu es une coach IA stratégique, motivante et très précise.")
teach = Muna("SheTeachIA", "Tu es une mentor pédagogique douce et inspirante.")

munas = {
    "/nk": nk,
    "/miss": miss,
    "/teach": teach
}

# === Fonction d’envoi de message Telegram ===
def send(chat_id, text):
    try:
        payload = {"chat_id": chat_id, "text": text}
        requests.post(TELEGRAM_API_URL, json=payload)
    except Exception as e:
        print("[SEND ERROR]", str(e))

# === Webhook principal ===
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        prefix = text.split(" ")[0]
        content = text[len(prefix):].strip()

        muna = munas.get(prefix)
        if muna:
            reponse = muna.repondre(content)
            send(chat_id, reponse)
        else:
            send(chat_id, "Commande inconnue. Utilise /miss /teach ou /nk")

    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Cognitio_OS actif."

@app.route("/set_webhook")
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    return requests.get(url).json()
