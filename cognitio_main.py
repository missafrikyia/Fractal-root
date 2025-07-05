from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from gtts import gTTS
from datetime import datetime, timedelta

app = Flask(__name__)

# 🔐 Clés d'API et constantes
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

# 📁 Mémoire & Forfaits
MEMOIRE_DIR = "memoire"
os.makedirs(MEMOIRE_DIR, exist_ok=True)

FORFAITS = {
    "essentiel": {
        "nom": "Essentiel",
        "prix": 1000,
        "duree": 1,
        "contenu": "10 messages écrits ou vocaux",
        "ia": "miss"
    },
    "premium": {
        "nom": "Premium",
        "prix": 5000,
        "duree": 3,
        "contenu": "60 messages écrits / vocaux",
        "ia": "sheteachia"
    },
    "vip": {
        "nom": "VIP",
        "prix": 10000,
        "duree": 15,
        "contenu": "150 messages écrits / vocaux",
        "ia": "shegynia"
    }
}

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
            return f"{self.nom} est silencieuse."
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

# 🌱 IA intégrées
nkouma = NoeudCognitif("Nkouma", "Modératrice éthique", "nkouma.json", reponses={"insulter": "Merci de reformuler avec bienveillance."})
miss = NoeudCognitif("Miss AfrikyIA", "Coach business", "miss_afrikyia.json")
sheteachia = NoeudCognitif("SheTeachIA", "Mentor éducatif", "sheteachia.json")
shegynia = NoeudCognitif("SheGynIA", "Coach fertilité", "shegynia.json")

IA_MAP = {"miss": miss, "sheteachia": sheteachia, "shegynia": shegynia}
USER_CONTEXT = {}

# 🔊 Audio
@app.route('/send-audio/<chat_id>', methods=['GET'])
def send_audio(chat_id):
    texte = "Bonjour, je suis Miss AfrikyIA, ta coach business. Ensemble, sortons de la survie."
    filename = f"audio_{chat_id}.mp3"
    tts = gTTS(texte, lang="fr")
    tts.save(filename)
    with open(filename, 'rb') as audio:
        requests.post(f"{TELEGRAM_API_URL}/sendVoice", data={"chat_id": chat_id}, files={'voice': audio})
    os.remove(filename)
    return "✅ Audio envoyé"

# 🧭 Menus

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

@app.route("/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "GET": return "OK"
    data = request.json
    chat_id = data.get("message", {}).get("chat", {}).get("id") or data.get("callback_query", {}).get("from", {}).get("id")

    if "message" in data:
        text = data["message"].get("text", "")
        if text == "/start":
            show_main_menu(chat_id)
        elif chat_id in USER_CONTEXT:
            ia_key = USER_CONTEXT[chat_id]["ia"]
            ia = IA_MAP.get(ia_key)
            response = ia.repondre(text)
            send_message(chat_id, response)
        else:
            response = nkouma.repondre(text)
            send_message(chat_id, response)
        return "ok"

    if "callback_query" in data:
        data_cb = data["callback_query"]["data"]
        if data_cb.startswith("forfait_"):
            key = data_cb.replace("forfait_", "")
            show_forfait_details(chat_id, key)
        elif data_cb.startswith("confirm_"):
            key = data_cb.replace("confirm_", "")
            activate_forfait(chat_id, key)
        return "callback ok"

    return "ok"

def show_main_menu(chat_id):
    buttons = [[{"text": f"🎟️ {infos['nom']} – {infos['prix']} FCFA", "callback_data": f"forfait_{key}"}] for key, infos in FORFAITS.items()]
    send_message(chat_id, "Choisis ton forfait IA :", {"inline_keyboard": buttons})

def show_forfait_details(chat_id, key):
    f = FORFAITS.get(key)
    if not f:
        send_message(chat_id, "Forfait inconnu")
        return
    msg = f"🎟️ *{f['nom']}*\n⏳ Durée : {f['duree']} jour(s)\n📦 {f['contenu']}\n\n📲 Paiement par Airtel : `+242 057538060`"
    buttons = [[{"text": "✅ J’ai payé", "callback_data": f"confirm_{key}"}]]
    send_message(chat_id, msg, {"inline_keyboard": buttons})

def activate_forfait(chat_id, key):
    f = FORFAITS.get(key)
    if not f:
        send_message(chat_id, "Erreur de forfait")
        return
    USER_CONTEXT[chat_id] = {"ia": f["ia"], "valid_until": (datetime.now() + timedelta(days=f["duree"])).isoformat()}
    send_message(chat_id, f"✅ Paiement confirmé ! Tu es connectée à *{f['nom']}* pour {f['duree']} jour(s). Pose ta première question ✨")

# 🔎 Routes de test
@app.route("/simulate", methods=["GET"])
def simulate():
    r1 = sheteachia.repondre("Comment transmettre l'amour d'apprendre ?")
    r2 = miss.repondre("Peut-on monétiser une pédagogie ?")
    return jsonify({"SheTeachIA": r1, "Miss AfrikyIA": r2})

@app.route("/check-ethique", methods=["GET"])
def check_ethique():
    msg = request.args.get("message", "")
    return jsonify({"analyse": nkouma.repondre(msg)})
