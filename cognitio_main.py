from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
from flask import Flask, request
from openai import OpenAI
from gtts import gTTS
from langdetect import detect
from datetime import datetime

app = Flask(__name__)

# 🔐 Clés d’API
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

# 📁 Dossiers
MEMOIRE_DIR = "memoire"
os.makedirs(MEMOIRE_DIR, exist_ok=True)
ABONNEMENTS_PATH = "data/abonnements.json"
with open(ABONNEMENTS_PATH, "r", encoding="utf-8") as f:
    FORFAITS = json.load(f)

# 🧠 Classe IA
class NoeudCognitif:
    def __init__(self, nom, role, fichier_memoire=None, parent=None, reponses=None):
        self.nom = nom
        self.role = role
        self.parent = parent
        self.enfants = []
        self.reponses = reponses or {}
        self.parle = True
        self.fichier_memoire = fichier_memoire
        self.memoire = self.charger_memoire()

    def ajouter_enfant(self, enfant):
        enfant.parent = self
        self.enfants.append(enfant)

    def repondre(self, question):
        question = question.lower().strip()
        if not self.parle:
            return f"{self.nom} est silencieux."

        for cle, reponse in self.reponses.items():
            if cle in question:
                return reponse

        for enfant in self.enfants:
            reponse = enfant.repondre(question)
            if "je ne comprends pas" not in reponse.lower():
                return reponse

        gpt_reply = self.appel_gpt(question)
        self.memoire[datetime.now().isoformat()] = {"question": question, "réponse": gpt_reply}
        self.sauvegarder_memoire()
        return gpt_reply

    def appel_gpt(self, prompt):
        try:
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.role},
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
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

# 🌱 Noeuds IA
nkouma = NoeudCognitif("Nkouma", "Modératrice éthique", "nkouma.json", reponses={"insulter": "Merci de reformuler."})
miss = NoeudCognitif("Miss AfrikyIA", "Coach business", "miss.json", reponses={"plan": "Un bon plan commence par une vision claire."})
sheteachia = NoeudCognitif("SheTeachIA", "Mentor éducatif", "sheteach.json", reponses={"devoir": "Je t’aide pour les devoirs."})
nkouma.ajouter_enfant(miss)
nkouma.ajouter_enfant(sheteachia)

# 📤 Send Telegram
def send_message(chat_id, text, reply_markup=None):
    lang = detect(text)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": json.dumps(reply_markup) if reply_markup else None
    }
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

# ✅ Menus
def show_main_menu(chat_id):
    boutons = [
        [{"text": "📈 Business", "callback_data": "p_business"}],
        [{"text": "📚 Éducation", "callback_data": "p_education"}]
    ]
    send_message(chat_id, "👋 Que souhaites-tu développer aujourd’hui ?", {"inline_keyboard": boutons})

def show_submenu(chat_id, domaine):
    if domaine == "business":
        poles = [("Plan", "s_plan"), ("Visuel", "s_visuel")]
    else:
        poles = [("École d’été", "s_ecole"), ("Devoirs", "s_devoirs")]
    buttons = [[{"text": nom, "callback_data": code}] for nom, code in poles]
    send_message(chat_id, f"🧭 Choisis un sous-pôle ({domaine.title()}) :", {"inline_keyboard": buttons})

def show_forfaits(chat_id, pole):
    boutons = []
    for key, infos in FORFAITS.items():
        label = f"{infos['nom']} – {infos['prix']} FCFA"
        boutons.append([{"text": label, "callback_data": f"pay_{key}"}])
    send_message(chat_id, f"💸 Choisis ton forfait pour {pole.title()} :", {"inline_keyboard": boutons})

def handle_payment(chat_id, forfait_key):
    infos = FORFAITS.get(forfait_key)
    if not infos:
        send_message(chat_id, "❌ Forfait inconnu.")
        return

    msg = (
        f"🎟️ *{infos['nom']}*\n"
        f"⏳ Durée : {infos['duree']}\n"
        f"📦 Contenu : {infos['contenu']}\n"
        f"\n📲 Paiement par Airtel Money :\n`+242 057538060`\n"
        f"📤 Envoie une preuve ici."
    )

    bouton = {
        "inline_keyboard": [
            [{"text": "✅ J’ai payé", "callback_data": f"confirm_{forfait_key}"}]
        ]
    }

    send_message(chat_id, msg, bouton)

def confirm_access(chat_id, forfait_key):
    msg = f"✅ Accès activé pour le forfait {forfait_key.upper()} !\nTu peux poser ta première question à Miss AfrikyIA 💬"
    send_message(chat_id, msg)

# ✅ Webhook
@app.route("/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "OK ✅"

    data = request.json
    chat_id = data.get("message", {}).get("chat", {}).get("id") or data.get("callback_query", {}).get("from", {}).get("id")

    if "message" in data:
        text = data["message"].get("text", "")
        if text == "/start":
            show_main_menu(chat_id)
            return "OK"
        response = nkouma.repondre(text)
        send_message(chat_id, response)
        return "Reçu"

    if "callback_query" in data:
        callback = data["callback_query"]
        data_cb = callback["data"]

        if data_cb.startswith("p_"):
            domaine = data_cb.split("_")[1]
            show_submenu(chat_id, domaine)
        elif data_cb.startswith("s_"):
            pole = data_cb.split("_")[1]
            show_forfaits(chat_id, pole)
        elif data_cb.startswith("pay_"):
            forfait = data_cb.replace("pay_", "")
            handle_payment(chat_id, forfait)
        elif data_cb.startswith("confirm_"):
            forfait = data_cb.replace("confirm_", "")
            confirm_access(chat_id, forfait)
        return "Callback ok"

    return "OK"

# ✅ Routes simulate & éthique
@app.route("/simulate", methods=["GET"])
def simulate():
    r1 = miss.repondre("Comment démarrer une activité ?")
    r2 = sheteachia.repondre("Comment motiver les élèves ?")
    return jsonify({"Miss AfrikyIA": r1, "SheTeachIA": r2})

@app.route("/check-ethique", methods=["GET"])
def check_ethique():
    message = request.args.get("message", "")
    return jsonify({"analyse": nkouma.repondre(message)})
