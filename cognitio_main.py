# ✅ Cognitio Script – Parcours Forfait → IA Coach (Inline 100%)

from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from gtts import gTTS
from langdetect import detect
from datetime import datetime

app = Flask(__name__)

# 🔐 Clés API et constantes
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

# 📁 Dossiers
MEMOIRE_DIR = "memoire"
os.makedirs(MEMOIRE_DIR, exist_ok=True)

# 🎟️ Forfaits manuels (inline, pas via JSON)
FORFAITS = {
    "essentiel": {
        "nom": "Essentiel",
        "prix": "1 000 FCFA",
        "duree": "1 jour",
        "contenu": "10 messages écrits ou vocaux"
    },
    "premium": {
        "nom": "Premium",
        "prix": "5 000 FCFA",
        "duree": "3 jours",
        "contenu": "60 messages écrits ou vocaux"
    },
    "vip": {
        "nom": "VIP",
        "prix": "10 000 FCFA",
        "duree": "15 jours",
        "contenu": "150 messages écrits ou vocaux"
    }
}

# 🧠 Classe IA
class NoeudCognitif:
    def __init__(self, nom, role, fichier_memoire=None):
        self.nom = nom
        self.role = role
        self.fichier_memoire = fichier_memoire
        self.memoire = self.charger_memoire()

    def repondre(self, question):
        lang = detect(question)
        prefix = "Réponds en lingala : " if lang == "ln" else ""
        prompt = f"{prefix}{question}"

        try:
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.role},
                    {"role": "user", "content": prompt}
                ]
            )
            reponse = completion.choices[0].message.content.strip()
            self.memoire[datetime.now().isoformat()] = {"q": question, "r": reponse}
            self.sauvegarder_memoire()
            return reponse
        except:
            return "[GPT indisponible]"

    def charger_memoire(self):
        if not self.fichier_memoire:
            return {}
        path = os.path.join(MEMOIRE_DIR, self.fichier_memoire)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def sauvegarder_memoire(self):
        if not self.fichier_memoire:
            return
        path = os.path.join(MEMOIRE_DIR, self.fichier_memoire)
        with open(path, "w") as f:
            json.dump(self.memoire, f, indent=2)

# 🧠 Création des IA
miss = NoeudCognitif("Miss AfrikyIA", "Coach IA business", "miss.json")
sheteachia = NoeudCognitif("SheTeachIA", "Mentor IA éducatif", "teach.json")
shelovia = NoeudCognitif("SheLovIA", "Coach IA relationnel/amour", "love.json")

# ✉️ Utilitaires

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(reply_markup) if reply_markup else None
    }
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

# ✅ Étape 1 : choix des forfaits

def show_forfaits(chat_id):
    boutons = [
        [{"text": f"{infos['nom']} – {infos['prix']}", "callback_data": f"forfait_{key}"}]
        for key, infos in FORFAITS.items()
    ]
    send_message(chat_id, "💳 Choisis ton forfait IA :", {"inline_keyboard": boutons})

# ✅ Étape 2 : Détail du forfait choisi

def show_forfait_details(chat_id, key):
    infos = FORFAITS.get(key)
    if not infos:
        send_message(chat_id, "❌ Forfait inconnu.")
        return
    texte = f"🎟️ *{infos['nom']}*"
Durée : {infos['duree']}
Contenu : {infos['contenu']}
Prix : {infos['prix']}

Paiement : Airtel Money +242 057538060"
    boutons = [[{"text": "✅ J’ai payé", "callback_data": f"acces_ia"}]]
    send_message(chat_id, texte, {"inline_keyboard": boutons})

# ✅ Étape 3 : Accès aux IA coachs

def show_ia_options(chat_id):
    boutons = [
        [{"text": "👩‍💼 Miss AfrikyIA", "callback_data": "ia_miss"}],
        [{"text": "👩‍🏫 SheTeachIA", "callback_data": "ia_teach"}],
        [{"text": "💕 SheLovIA", "callback_data": "ia_love"}]
    ]
    send_message(chat_id, "🤖 Choisis ton coach IA :", {"inline_keyboard": boutons})

# ✅ Message de bienvenue IA

def accueil_ia(chat_id, ia):
    message = ia.repondre("Bonjour")
    send_message(chat_id, f"🤖 *{ia.nom} est maintenant activé !*

{message}")

# ✅ Webhook Telegram
@app.route("/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "✅ Webhook ok"

    data = request.json
    chat_id = data.get("message", {}).get("chat", {}).get("id") or data.get("callback_query", {}).get("from", {}).get("id")

    if "message" in data:
        text = data["message"].get("text", "")
        if text == "/start":
            show_forfaits(chat_id)
            return "ok"

    if "callback_query" in data:
        cb = data["callback_query"]
        data_cb = cb["data"]

        if data_cb.startswith("forfait_"):
            key = data_cb.replace("forfait_", "")
            show_forfait_details(chat_id, key)

        elif data_cb == "acces_ia":
            show_ia_options(chat_id)

        elif data_cb == "ia_miss":
            accueil_ia(chat_id, miss)
        elif data_cb == "ia_teach":
            accueil_ia(chat_id, sheteachia)
        elif data_cb == "ia_love":
            accueil_ia(chat_id, shelovia)

    return "ok"

# ✅ Route simulation IA
@app.route('/simulate', methods=['GET'])
def simulate():
    r1 = sheteachia.repondre("Comment motiver les enfants à apprendre ?")
    r2 = miss.repondre("Comment monétiser une école virtuelle ?")
    return f"SheTeachIA: {r1}\nMiss AfrikyIA: {r2}"

# ✅ Route analyse éthique
@app.route('/check', methods=['GET'])
def check():
    message = request.args.get("message", "")
    if not message:
        return jsonify({"erreur": "Message vide"}), 400
    analyse = miss.repondre(message)
    return jsonify({"analyse": analyse})

