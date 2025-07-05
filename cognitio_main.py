from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
from flask import Flask, request
from openai import OpenAI
from gtts import gTTS
from datetime import datetime

app = Flask(__name__)

# 🔐 Environnement
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

# 📁 Fichiers
MEMOIRE_DIR = "memoire"
ABONNEMENTS_PATH = "data/abonnements.json"
os.makedirs(MEMOIRE_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

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

# 🌱 Initialisation
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

# ✅ Simulation
@app.route('/simulate', methods=['GET'])
def simulate():
    print("[Simu] Miss → SheTeachIA")
    r1 = sheteachia.repondre("Comment transmettre l'amour d'apprendre ?")
    print(r1)
    r2 = miss.repondre("Peut-on monétiser une pédagogie ?")
    print(r2)
    return "✅ Simulation IA ok"

# ✅ Éthique
@app.route('/check-ethique', methods=['GET'])
def check_ethique():
    message = request.args.get("message", "")
    return {"analyse": nkouma.repondre(message)}

# ✅ Menu interactif
def send_inline_keyboard(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "📚 Éducation", "callback_data": "p_education"}],
            [{"text": "💼 Business", "callback_data": "p_business"}]
        ]
    }
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Qu’est-ce qu’on augmente aujourd’hui ?", "reply_markup": keyboard})

def send_services(chat_id, pole):
    if pole == "education":
        keyboard = {
            "inline_keyboard": [
                [{"text": "École d’été", "callback_data": "s_ecole"}],
                [{"text": "Aide aux devoirs", "callback_data": "s_devoirs"}]
            ]
        }
    else:
        keyboard = {
            "inline_keyboard": [
                [{"text": "Plan stratégique", "callback_data": "s_plan"}],
                [{"text": "Créa visuelle", "callback_data": "s_visuel"}],
                [{"text": "Branding", "callback_data": "s_branding"}]
            ]
        }
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Choisis ton service 👇", "reply_markup": keyboard})

def send_pricing(chat_id):
    text = "Voici les forfaits disponibles :\n\n💡 1000 FCFA – Basique\n🚀 5000 FCFA – Pro\n👑 10 000 FCFA – VIP"
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

# ✅ Webhook
@app.route("/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "Webhook prêt ✅"

    data = request.json
    chat_id = data.get("message", {}).get("chat", {}).get("id") or data.get("callback_query", {}).get("message", {}).get("chat", {}).get("id")

    if "message" in data:
        text = data["message"].get("text", "")
        if text == "/start":
            send_inline_keyboard(chat_id)
            return "menu"

        response = nkouma.repondre(text)
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": response})
        return "ok"

    if "callback_query" in data:
        query = data["callback_query"]
        d = query["data"]
        if d.startswith("p_"):
            pole = d.split("_")[1]
            send_services(chat_id, pole)
        elif d.startswith("s_"):
            send_pricing(chat_id)
        return "callback handled"

    return "ok"
