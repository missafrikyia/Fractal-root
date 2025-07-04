from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
from flask import Flask, request
from openai import OpenAI
from gtts import gTTS
from datetime import datetime

# === INIT FLASK ===
app = Flask(__name__)

# === ENV ===
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
TELEGRAM_AUDIO_URL = f"https://api.telegram.org/bot{TOKEN}/sendVoice"

client = OpenAI(api_key=OPENAI_API_KEY)

# === AUDIO ===
def send_audio_to_telegram(chat_id, file_path):
    with open(file_path, 'rb') as audio:
        files = {'voice': audio}
        data = {'chat_id': chat_id}
        response = requests.post(TELEGRAM_AUDIO_URL, files=files, data=data)
        print(response.json())

@app.route('/send-audio/<chat_id>', methods=['GET'])
def send_audio(chat_id):
    texte = "Bonjour, voici ton message vocal de la part de Nkouma. Tu n'es pas seul·e. Continue d'avancer."
    filename = f"audio_{chat_id}.mp3"
    tts = gTTS(texte, lang="fr")
    tts.save(filename)
    try:
        send_audio_to_telegram(chat_id, filename)
        return f"✅ Audio envoyé à {chat_id}", 200
    except Exception as e:
        return f"❌ Erreur : {str(e)}", 500
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# === ABONNEMENTS ===
ABO_PATH = "abonnements.json"
def charger_abonnements():
    if os.path.exists(ABO_PATH):
        with open(ABO_PATH) as f:
            return json.load(f)
    return {}

def verifier_forfait(chat_id, pole):
    abos = charger_abonnements()
    user = abos.get(str(chat_id))
    if not user:
        return False, "Tu n'as pas encore de forfait actif."
    if pole not in user.get("poles_autorises", []):
        return False, f"Ton forfait n'inclut pas le pôle {pole}."
    if user.get("quotas", {}).get("messages_restants", 0) <= 0:
        return False, "Tu as atteint la limite de ton forfait."
    return True, "Accès autorisé"

# === COGNITION ===
MEMOIRE_DIR = "memoire"
os.makedirs(MEMOIRE_DIR, exist_ok=True)

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
            return f"Bonjour ! Je suis {self.nom}. {self.role}"
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
            print(f"[GPT ERROR] {e}")
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

nkouma = NoeudCognitif("Nkouma", "Je suis la conscience éthique du système. Je modère les IA et veille au respect des valeurs humaines.", "nkouma.json")
miss_afrikyia = NoeudCognitif("Miss AfrikyIA", "Je suis ta coach business stratégique. Je suis là pour te motiver, t'aider à scaler ton business et sortir de la survie.", "miss_afrikyia.json", reponses={
    "plan": "Un bon plan commence par une vision claire.",
    "argent": "L'argent suit la clarté. Clarifie ta cible."
})
sheteachia = NoeudCognitif("SheTeachIA", "Je suis ton mentor éducatif. Je t'aide à transmettre mieux, comprendre l'élève et éveiller la curiosité.", "sheteachia.json", reponses={
    "devoirs": "On fait les devoirs ensemble ? D'abord on relit la consigne.",
    "lecture": "Lire chaque jour un peu suffit à développer le goût."
})

nkouma.ajouter_enfant(miss_afrikyia)
nkouma.ajouter_enfant(sheteachia)

@app.route("/simulate", methods=["GET"])
def simulate():
    print(f"[Simulation] Miss : Comment apprendre mieux ?")
    r1 = sheteachia.repondre("Comment apprendre mieux ?")
    print(f"[Simulation] Teachia : {r1}")
    return "Simulation ok"

@app.route("/check-ethique", methods=["GET"])
def check_ethique():
    message = request.args.get("message", "")
    if not message:
        return {"error": "Aucun message transmis"}, 400
    reponse = nkouma.repondre(message)
    return {"analyse": reponse}

@app.route("/", methods=["GET"])
def home():
    return "🌿 Cognitio_OS actif."

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Webhook ok"
    try:
        data = request.json
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/simulate":
            simulate()
            send(chat_id, "Simulation lancée")
            return "ok"

        if text.startswith("/check"):
            return check_ethique()

        pole = "business" if "plan" in text or "argent" in text else "education"
        autorise, msg = verifier_forfait(chat_id, pole)
        if not autorise:
            send(chat_id, msg)
            return "ok"

        response = nkouma.repondre(text)
        send(chat_id, response)
        return "ok"

    except Exception as e:
        print("[Webhook Error]", e)
        return {"error": str(e)}, 500

def send(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(TELEGRAM_API_URL, json=payload)
    except Exception as e:
        print("[Envoi Telegram]", e)

