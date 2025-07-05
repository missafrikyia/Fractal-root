from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from gtts import gTTS
from datetime import datetime

app = Flask(__name__)

# 🔐 Clés d'API et constantes
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

# 📁 Dossiers
MEMOIRE_DIR = "memoire"
ABONNEMENTS_PATH = "data/abonnements.json"
os.makedirs(MEMOIRE_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# 📦 Chargement des forfaits
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

        if question == "/start":
            return f"Bonjour, je suis {self.nom}. Je suis là pour te guider avec clarté et stratégie."

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

# 🌱 Noeuds IA
nkouma = NoeudCognitif("Nkouma", "Modératrice éthique", "nkouma.json", reponses={"insulter": "Merci de reformuler avec bienveillance."})
miss = NoeudCognitif("Miss AfrikyIA", "Coach business", "miss_afrikyia.json", reponses={"plan": "Un bon plan commence par une bonne vision."})
sheteachia = NoeudCognitif("SheTeachIA", "Mentor éducatif", "sheteachia.json", reponses={"devoirs": "Je peux t’aider pour les devoirs."})
nkouma.ajouter_enfant(miss)
nkouma.ajouter_enfant(sheteachia)

# 🎧 Audio
def send_audio_to_telegram(chat_id, file_path):
    url = f"{TELEGRAM_API_URL}/sendVoice"
    with open(file_path, 'rb') as audio:
        files = {'voice': audio}
        data = {'chat_id': chat_id}
        requests.post(url, files=files, data=data)

@app.route('/send-audio/<chat_id>', methods=['GET'])
def send_audio(chat_id):
    texte = "Bonjour, je suis Miss AfrikyIA, ta coach business. Ensemble, sortons de la survie."
    filename = f"audio_{chat_id}.mp3"
    tts = gTTS(texte, lang="fr")
    tts.save(filename)
    send_audio_to_telegram(chat_id, filename)
    os.remove(filename)
    return f"✅ Audio envoyé à {chat_id}"

# ✅ Menus & Forfaits
def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": json.dumps(reply_markup) if reply_markup else None
    }
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def show_main_menu(chat_id):
    buttons = [
        [{"text": "📈 Business", "callback_data": "p_business"}],
        [{"text": "📚 Éducation", "callback_data": "p_education"}]
    ]
    send_message(chat_id, "👋 Bonjour ! Qu’est-ce qu’on augmente aujourd’hui ?", {"inline_keyboard": buttons})

def show_submenu(chat_id, domaine):
    if domaine == "business":
        poles = [("Plan", "s_plan"), ("Visuel", "s_visuel"), ("Branding", "s_branding")]
    else:
        poles = [("École d’été", "s_ecole"), ("Aide aux devoirs", "s_devoirs")]
    buttons = [[{"text": nom, "callback_data": code}] for nom, code in poles]
    send_message(chat_id, f"🧭 Choisis un sous-pôle ({domaine.title()}) :", {"inline_keyboard": buttons})

def show_forfaits(chat_id, pole):
    buttons = []
    for key, infos in FORFAITS.items():
        btn_text = f"{infos['nom']} – {infos['prix']} FCFA"
        buttons.append([{"text": btn_text, "callback_data": f"pay_{key}"}])
    send_message(chat_id, f"💸 Choisis ton forfait pour le pôle **{pole}** :", {"inline_keyboard": buttons})

def handle_payment(chat_id, forfait):
    infos = FORFAITS.get(forfait)
    if not infos:
        send_message(chat_id, "Forfait non reconnu.")
        return
    msg = (
        f"✅ Forfait *{infos['nom']}* sélectionné :\n"
        f"- Prix : {infos['prix']} FCFA\n"
        f"- Accès : {infos['duree']}\n\n"
        f"📲 *Paiement par Airtel Money* :\n"
        f"`+242 057538060`\n\n"
        f"📤 Envoie ensuite une preuve de paiement ici."
    )
    send_message(chat_id, msg)

# ✅ Webhook complet
@app.route("/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "Webhook prêt ✅"

    data = request.json
    chat_id = data.get("message", {}).get("chat", {}).get("id") or data.get("callback_query", {}).get("from", {}).get("id")

    if "message" in data:
        text = data["message"].get("text", "")
        if text == "/start":
            show_main_menu(chat_id)
            return "menu"
        response = nkouma.repondre(text)
        send_message(chat_id, response)
        return "ok"

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
        return "callback handled"

    return "ok"

# ✅ Simulation IA
@app.route('/simulate', methods=['GET'])
def simulate():
    r1 = sheteachia.repondre("Comment transmettre l'amour d'apprendre ?")
    r2 = miss.repondre("Peut-on monétiser une pédagogie ?")
    print("[Simu] Miss → SheTeachIA\n", r1, "\n", r2)
    return "✅ Simulation IA ok"

# ✅ Éthique
@app.route('/check-ethique', methods=['GET'])
def check_ethique():
    message = request.args.get("message", "")
    return {"analyse": nkouma.repondre(message)}
