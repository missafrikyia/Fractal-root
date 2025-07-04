from dotenv import load_dotenv
load_dotenv()

import os, json, requests
from flask import Flask, request
from gtts import gTTS
from datetime import datetime
from openai import OpenAI

# 🔧 Init Flask
app = Flask(__name__)

# 🔐 Config
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
client = OpenAI(api_key=OPENAI_API_KEY)

# 📁 Dossiers
MEMOIRE_DIR = "memoire"
DATA_DIR = "data"
os.makedirs(MEMOIRE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# 📁 Fichier des abonnements
ABONNEMENTS_FILE = os.path.join(DATA_DIR, "abonnements.json")
if not os.path.exists(ABONNEMENTS_FILE):
    with open(ABONNEMENTS_FILE, "w") as f:
        json.dump({}, f)

def get_abonnement(chat_id):
    with open(ABONNEMENTS_FILE, "r") as f:
        abonnements = json.load(f)
    return abonnements.get(str(chat_id))

def poles_menu(poles):
    options = {
        "miss_afrikyia": "💼 Miss AfrikyIA : business & motivation",
        "sheteachia": "🎓 SheTeachIA : école augmentée"
    }
    return "\n".join([f"➡️ {options[p]}" for p in poles if p in options])

# 🎤 Audio vocal GET
@app.route('/send-audio/<chat_id>', methods=['GET'])
def send_audio(chat_id):
    texte = "Bonjour, je suis Miss AfrikyIA, ta coach business. Je suis là pour te donner des stratégies concrètes, te motiver et t’aider à scaler ton activité. Sortons ensemble de la survie."
    filename = f"audio_{chat_id}.mp3"
    tts = gTTS(texte, lang="fr")
    tts.save(filename)

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
        with open(filename, 'rb') as audio:
            files = {'voice': audio}
            data = {'chat_id': chat_id}
            requests.post(url, files=files, data=data)
        return f"✅ Audio envoyé à {chat_id}", 200
    except Exception as e:
        return f"❌ Erreur : {str(e)}", 500
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# 🧠 Noeud Cognitif
class NoeudCognitif:
    def __init__(self, nom, role, fichier_memoire=None, reponses=None):
        self.nom = nom
        self.role = role
        self.fichier_memoire = fichier_memoire
        self.reponses = reponses or {}
        self.memoire = self.charger_memoire()

    def repondre(self, question):
        question = question.lower().strip()
        for cle, rep in self.reponses.items():
            if cle in question:
                return rep
        return self.appel_gpt(question)

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
            with open(path, "r") as f:
                return json.load(f)
        return {}

# 👩🏾‍💼 Les IA
miss_afrikyia = NoeudCognitif("Miss AfrikyIA", "Tu es une coach business stratégique", "miss_afrikyia.json", {
    "business": "Parle-moi de ton idée. On va clarifier ton plan.",
    "argent": "L’argent est un outil. Quelle est ta vraie mission ?"
})
sheteachia = NoeudCognitif("SheTeachIA", "Tu es une mentor éducative bienveillante", "sheteachia.json", {
    "école": "Chaque enfant apprend différemment. Encourage-le.",
    "apprendre": "Rends l’apprentissage joyeux et concret."
})

# ✅ Simulate
@app.route('/simulate', methods=['GET'])
def simulate():
    q1 = "Comment enseigner avec amour ?"
    r1 = sheteachia.repondre(q1)
    q2 = "Comment gagner de l'argent avec mes talents ?"
    r2 = miss_afrikyia.repondre(q2)
    print(f"[SIMU] {q1} -> {r1}")
    print(f"[SIMU] {q2} -> {r2}")
    return "Simulation IA effectuée ✅"

# ✅ Check éthique
@app.route('/check-ethique', methods=['GET'])
def check_ethique():
    msg = request.args.get("message", "")
    if not msg:
        return {"error": "Aucun message transmis"}, 400
    if "voler" in msg or "insulter" in msg:
        return {"analyse": "Non éthique. Reformule ce message."}
    return {"analyse": "✅ Conforme à l’éthique."}

# ✅ Accueil navigateur
@app.route("/", methods=["GET"])
def accueil():
    return "🌿 Cognitio_OS – Actif"

# ✅ Webhook principal
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        if "message" not in data:
            return "ok"
        chat_id = str(data["message"]["chat"]["id"])
        text = data["message"].get("text", "")

        ab = get_abonnement(chat_id)
        if not ab:
            send(chat_id, "Tu n'as pas encore de forfait actif. Merci de choisir un forfait :\n1. 🟢 1000 FCFA\n2. 🟠 5000 FCFA\n3. 🔵 10 000 FCFA")
            return "ok"

        if text.lower() in ["/start", "menu"]:
            msg = "🌍 Bienvenue dans Cognitio_OS\nVoici les pôles accessibles :\n"
            msg += poles_menu(ab["poles_autorises"])
            send(chat_id, msg)
            return "ok"

        if "miss_afrikyia" in ab["poles_autorises"]:
            if any(kw in text.lower() for kw in ["business", "argent"]):
                send(chat_id, miss_afrikyia.repondre(text))
                return "ok"

        if "sheteachia" in ab["poles_autorises"]:
            if any(kw in text.lower() for kw in ["école", "apprendre"]):
                send(chat_id, sheteachia.repondre(text))
                return "ok"

        send(chat_id, "Désolé, je ne peux pas répondre à cette demande.")
        return "ok"
    except Exception as e:
        print(f"[ERREUR] {e}")
        return {"error": str(e)}, 500

# ✅ Envoi message
def send(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(TELEGRAM_API_URL, json=payload)
    except Exception as e:
        print(f"[SEND ERROR] {e}")
