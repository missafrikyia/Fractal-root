from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
from flask import Flask, request
from openai import OpenAI
from gtts import gTTS
from datetime import datetime

# Initialisation Flask
app = Flask(__name__)

# Environnement
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
TELEGRAM_AUDIO_URL = f"https://api.telegram.org/bot{TOKEN}/sendVoice"

client = OpenAI(api_key=OPENAI_API_KEY)

# Fonction d'envoi vocal

def send_audio_to_telegram(chat_id, file_path):
    with open(file_path, 'rb') as audio:
        files = {'voice': audio}
        data = {'chat_id': chat_id}
        response = requests.post(TELEGRAM_AUDIO_URL, files=files, data=data)
        print(response.json())

# Route GET pour envoyer un message audio
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

# Mémoire
MEMOIRE_DIR = "memoire"
os.makedirs(MEMOIRE_DIR, exist_ok=True)

# Classe Noeud Cognitif
class NoeudCognitif:
    def __init__(self, nom, role, fichier_memoire=None, parent=None, reponses=None, animus=None, mission=None):
        self.nom = nom
        self.role = role
        self.animus = animus or "personnalité non définie"
        self.mission = mission or "mission non définie"
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

        if question == "/start":
            return f"Bienvenue ! Je suis {self.nom}, un module de pensée fractale."

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

# IA
nkouma = NoeudCognitif("Nkouma", "Tu es la voix de la sagesse, modératrice des IA, garante de l’éthique.", "nkouma.json",
    reponses={"voler": "Ce comportement n’est pas acceptable.", "insulter": "Rappelle-toi : les mots blessent."},
    animus="sage, neutre, éthique",
    mission="Modérer les IA internes, garantir la sécurité cognitive.")

miss_afrikyia = NoeudCognitif("Miss AfrikyIA", "Coach stratégique et motivante.", "miss_afrikyia.json",
    reponses={"business": "Clarifie ta vision.", "argent": "L’argent est un outil."},
    animus="stratégique, concrète, motivante",
    mission="Aider les femmes à bâtir leur empire.")

sheteachia = NoeudCognitif("SheTeachIA", "Mentor pédagogique bienveillant.", "sheteachia.json",
    reponses={"éducation": "Répéter avec amour.", "apprendre": "Chaque enfant apprend à son rythme."},
    animus="pédagogue, douce, patiente",
    mission="Guider les enfants vers une connaissance joyeuse.")

nkouma.ajouter_enfant(miss_afrikyia)
nkouma.ajouter_enfant(sheteachia)

# Route simulate
@app.route("/simulate", methods=["GET"])
def simulate():
    print(f"[SIMULATION] {miss_afrikyia.nom} : Comment transmettre l'amour d'apprendre ?")
    r1 = sheteachia.repondre("Comment transmettre l'amour d'apprendre ?")
    print(f"[SIMULATION] {sheteachia.nom} : {r1}")

    print(f"[SIMULATION] {sheteachia.nom} : Est-ce qu'on peut monétiser une pédagogie ?")
    r2 = miss_afrikyia.repondre("Est-ce qu'on peut monétiser une pédagogie ?")
    print(f"[SIMULATION] {miss_afrikyia.nom} : {r2}")

    return "Simulation IA réalisée ✅"

# Route éthique
@app.route("/check-ethique", methods=["GET"])
def check_ethique():
    message = request.args.get("message", "")
    if not message:
        return {"error": "Aucun message transmis"}, 400
    reponse_nkouma = nkouma.repondre(message)
    return {"analyse": reponse_nkouma}

# Home
@app.route("/", methods=["GET"])
def home():
    return "🌿 Cognitio_OS actif."

# Webhook
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Webhook prêt ✅"

    try:
        data = request.json
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")

            if text == "/simulate":
                simulate()
                send(chat_id, "Simulation entre IA effectuée ✅")
                return "ok"

            if text == "/check":
                send(chat_id, "Utilise plutôt : /check-ethique?message=ton+texte")
                return "ok"

            if text == "/start":
                presentation = f"Bienvenue ! Je suis {miss_afrikyia.nom}.\n🎭 Animus : {miss_afrikyia.animus}\n🎯 Mission : {miss_afrikyia.mission}"
                send(chat_id, presentation)
                return "ok"

            response = nkouma.repondre(text)
            send(chat_id, response)
            return "ok"

    except Exception as e:
        print("[ERREUR WEBHOOK]", str(e))
        return {"error": str(e)}, 500

    return "ok"

# Envoi message

def send(chat_id, text):
    try:
        payload = {"chat_id": chat_id, "text": text}
        requests.post(TELEGRAM_API_URL, json=payload)
    except Exception as e:
        print("[ERREUR ENVOI]", str(e))
