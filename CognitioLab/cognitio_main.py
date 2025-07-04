from flask import Flask, request
from openai import OpenAI
from gtts import gTTS
import subprocess
import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

# ==== Chargement des variables d’environnement ====
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Exemple : https://cognitio.onrender.com/webhook

# ==== Suppression des proxies imposés par Render ====
for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(proxy_var, None)

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# ==== Envoi message textuel ====
def send(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        requests.post(url, json=payload)
    except Exception as e:
        print("[ERREUR ENVOI TEXTE]", e)

# ==== Envoi vocal ====
def send_voice(chat_id, message):
    try:
        tts = gTTS(text=message, lang="fr")
        file_mp3 = "temp.mp3"
        file_ogg = "temp.ogg"
        tts.save(file_mp3)
        subprocess.call(["ffmpeg", "-y", "-i", file_mp3, "-acodec", "libopus", file_ogg],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
        with open(file_ogg, 'rb') as audio:
            requests.post(url, data={"chat_id": chat_id}, files={"voice": audio})
    except Exception as e:
        print("[ERREUR ENVOI VOCAL]", e)

# ==== GPT contextualisé ====
def gpt_dialogue(role, message):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": role},
                {"role": "user", "content": message}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("[GPT ERROR]", e)
        return "[GPT indisponible]"

# ==== Lecture mémoire JSON ====
def lire_memoire(nom_fichier):
    try:
        chemin = os.path.join("memoire", nom_fichier)
        with open(chemin, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("contenu", "Aucune donnée enregistrée.")
    except Exception:
        return f"❌ Mémoire non trouvée : {nom_fichier}"

# ==== Classe Cognitio Node ====
class NoeudCognitif:
    def __init__(self, nom, role, memoire):
        self.nom = nom
        self.role = role
        self.memoire = memoire
        self.enfants = []

    def ajouter_enfant(self, enfant):
        self.enfants.append(enfant)

    def repondre(self, question):
        if "/memoire" in question:
            return lire_memoire(self.memoire)
        for enfant in self.enfants:
            reponse = enfant.repondre(question)
            if "je ne comprends pas" not in reponse.lower():
                return reponse
        return gpt_dialogue(self.role, question)

# ==== Arbre Cognitio ====
nkouma = NoeudCognitif("Nkouma", "Tu es un modérateur éthique et sage.", "nkouma.json")
miss = NoeudCognitif("Miss AfrikyIA", "Tu es une coach IA stratégique.", "miss_afrikyia.json")
sheteachia = NoeudCognitif("SheTeachIA", "Tu es un mentor pédagogique bienveillant.", "sheteachia.json")

nkouma.ajouter_enfant(miss)
nkouma.ajouter_enfant(sheteachia)

# ==== Simulation / Réflexion entre IA ====
def simulate_ethique():
    msg1 = "Je veux pousser à la performance extrême."
    msg2 = "Comment accompagner une maman fatiguée ?"

    r1 = gpt_dialogue(miss.role, msg1)
    r2 = gpt_dialogue(sheteachia.role, msg2)
    mod = gpt_dialogue(nkouma.role, f"Miss dit : {r1} /// SheTeachIA dit : {r2}. Que recommandes-tu ?")

    return f"📣 Miss : {r1}\n📚 SheTeachIA : {r2}\n⚖️ Nkouma (modération) : {mod}"

# ==== Webhook Flask ====
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").lower()

        if text == "/simulate":
            result = simulate_ethique()
            send(chat_id, result)
            return "ok"

        if text in ["/nkouma", "/miss", "/sheteachia"]:
            fichier = {
                "/nkouma": "nkouma.json",
                "/miss": "miss_afrikyia.json",
                "/sheteachia": "sheteachia.json"
            }[text]
            contenu = lire_memoire(fichier)
            send(chat_id, contenu)
            return "ok"

        response = nkouma.repondre(text)
        send(chat_id, response)
        return "ok"
    return "no message"

@app.route("/")
def home():
    return "🌱 Cognitio OS est actif."

@app.route("/set_webhook")
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    return requests.get(url).json()
