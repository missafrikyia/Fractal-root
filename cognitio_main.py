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

# Clés API
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

# Dossiers
MEMOIRE_DIR = "memoire"
ABONNEMENTS_PATH = "data/abonnements.json"
os.makedirs(MEMOIRE_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# Chargement des forfaits
with open(ABONNEMENTS_PATH, "r", encoding="utf-8") as f:
    FORFAITS = json.load(f)

# IA
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
                messages=[{"role": "system", "content": self.role}, {"role": "user", "content": prompt}]
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

nkouma = NoeudCognitif("Nkouma", "Modératrice éthique", "nkouma.json", reponses={"insulter": "Merci de reformuler avec bienveillance."})
miss = NoeudCognitif("Miss AfrikyIA", "Coach business", "miss_afrikyia.json", reponses={"plan": "Un bon plan commence par une bonne vision."})
sheteachia = NoeudCognitif("SheTeachIA", "Mentor éducatif", "sheteachia.json", reponses={"devoirs": "Je peux t’aider pour les devoirs."})
nkouma.ajouter_enfant(miss)
nkouma.ajouter_enfant(sheteachia)

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

def send_message(chat_id, text, reply_markup=None):
    print(f"[ENVOI MESSAGE] → {chat_id} : {text}")
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": None,
        "reply_markup": json.dumps(reply_markup) if reply_markup else None
    }
    r = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
    print(f"[RÉPONSE TELEGRAM] : {r.status_code} {r.text}")
