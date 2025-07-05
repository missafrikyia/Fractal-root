from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
from flask import Flask, request
from gtts import gTTS
from datetime import datetime
from openai import OpenAI

app = Flask(__name__)

# === Clés d’environnement
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
AUDIO_URL = f"https://api.telegram.org/bot{TOKEN}/sendVoice"

client = OpenAI(api_key=OPENAI_API_KEY)

# === Gestion mémoire locale
MEMOIRE_DIR = "memoire"
ABONNEMENTS_FILE = "abonnements.json"
os.makedirs(MEMOIRE_DIR, exist_ok=True)

# === Classe IA fractale
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

        if question == "/start":
            return f"Bonjour, je suis {self.nom}. {self.role}"

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

# === Instances IA
nkouma = NoeudCognitif("Nkouma", "Modératrice invisible, garante de l’éthique.", "nkouma.json", reponses={
    "voler": "Ce comportement est contraire à l’éthique.",
    "insulter": "Les mots blessent. Reformule avec respect."
})

miss_afrikyia = NoeudCognitif("Miss AfrikyIA", "Je suis ta coach business stratégique. Je t’aide à bâtir ton empire et sortir de la survie.", "miss_afrikyia.json", reponses={
    "plan": "Un bon plan d’action commence par une vision claire.",
    "branding": "Ta marque, c’est ton empreinte. Ne la néglige pas."
})

sheteachia = NoeudCognitif("SheTeachIA", "Mentor en pédagogie bienveillante.", "sheteachia.json", reponses={
    "devoirs": "Réviser un peu chaque jour est plus efficace.",
    "école d’été": "Profiter des vacances pour avancer, c’est puissant."
})

nkouma.ajouter_enfant(miss_afrikyia)
nkouma.ajouter_enfant(sheteachia)

# === Audio vocal
def send_audio_to_telegram(chat_id, file_path):
    with open(file_path, 'rb') as audio:
        files = {'voice': audio}
        data = {'chat_id': chat_id}
        requests.post(AUDIO_URL, files=files, data=data)

@app.route('/send-audio/<chat_id>', methods=['GET'])
def send_audio(chat_id):
    texte = "Bonjour, je suis Miss AfrikyIA, ta coach stratégique. Je suis là pour t’aider à créer, scaler et briller."
    filename = f"audio_{chat_id}.mp3"
    gTTS(texte, lang="fr").save(filename)
    send_audio_to_telegram(chat_id, filename)
    os.remove(filename)
    return f"✅ Audio envoyé à {chat_id}"

# === Vérification forfait
def get_forfait(chat_id):
    try:
        with open(ABONNEMENTS_FILE, "r") as f:
            abonnements = json.load(f)
        return abonnements.get(str(chat_id))
    except:
        return None

# === Menu interactif (3 étages)
def menu_etape1(chat_id):
    payload = {
        "chat_id": chat_id,
        "text": "🌟 Qu’est-ce qu’on augmente aujourd’hui ?",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "🚀 Business", "callback_data": "pole_business"}],
                [{"text": "🎓 Éducation", "callback_data": "pole_education"}]
            ]
        }
    }
    requests.post(TELEGRAM_API_URL, json=payload)

def menu_etape2(chat_id, pole):
    if pole == "pole_business":
        services = [
            [{"text": "📊 Plan", "callback_data": "service_plan"}],
            [{"text": "🎨 Visuel", "callback_data": "service_visuel"}],
            [{"text": "🔥 Branding", "callback_data": "service_branding"}]
        ]
    else:
        services = [
            [{"text": "📚 Aide aux devoirs", "callback_data": "service_devoir"}],
            [{"text": "🏕️ École d’été", "callback_data": "service_ete"}]
        ]
    payload = {"chat_id": chat_id, "text": "📌 Choisis ton service :", "reply_markup": {"inline_keyboard": services}}
    requests.post(TELEGRAM_API_URL, json=payload)

def menu_etape3(chat_id):
    forfaits = [
        [{"text": "💡 Essentiel – 1000 FCFA", "callback_data": "forfait_1000"}],
        [{"text": "✨ Premium – 5000 FCFA", "callback_data": "forfait_5000"}],
        [{"text": "💎 VIP – 10 000 FCFA", "callback_data": "forfait_10000"}]
    ]
    payload = {"chat_id": chat_id, "text": "💰 Choisis ton forfait :", "reply_markup": {"inline_keyboard": forfaits}}
    requests.post(TELEGRAM_API_URL, json=payload)

# === Route simulate
@app.route("/simulate", methods=["GET"])
def simulate():
    print(f"[🧠 Simulation] Miss AfrikyIA ➜ SheTeachIA")
    print(sheteachia.repondre("Comment transmettre l'amour d'apprendre ?"))
    print(f"[🧠 Simulation] SheTeachIA ➜ Miss AfrikyIA")
    print(miss_afrikyia.repondre("Comment monétiser une pédagogie innovante ?"))
    return "Simulation IA terminée ✅"

# === Éthique
@app.route("/check-ethique", methods=["GET"])
def check_ethique():
    message = request.args.get("message", "")
    if not message:
        return {"error": "Aucun message transmis"}, 400
    return {"analyse": nkouma.repondre(message)}

# === Webhook
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Webhook prêt ✅"

    data = request.json
    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    if text == "/start":
        if not get_forfait(chat_id):
            send(chat_id, "Tu n’as pas encore de forfait actif.")
        menu_etape1(chat_id)
        return "ok"

    response = nkouma.repondre(text)
    send(chat_id, response)
    return "ok"

# === Send simple
def send(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    requests.post(TELEGRAM_API_URL, json=payload)

# === Home
@app.route("/", methods=["GET"])
def home():
    return "🌍 Cognitio OS en ligne"
