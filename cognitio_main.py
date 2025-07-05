from langdetect import detect
from dotenv import load_dotenv
load_dotenv()

import os, json, requests, threading, time
from flask import Flask, request, jsonify
from openai import OpenAI
from gtts import gTTS
from datetime import datetime

app = Flask(__name__)

# 🔐 Clés API et constantes
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

# 🎫 Forfaits disponibles
FORFAITS = {
    "essentiel": {"nom": "Essentiel", "prix": "1000", "duree": 1, "contenu": "10 messages écrits ou vocaux"},
    "premium": {"nom": "Premium", "prix": "5000", "duree": 3, "contenu": "60 messages écrits / vocaux"},
    "vip": {"nom": "VIP", "prix": "10000", "duree": 15, "contenu": "150 messages écrits / vocaux"}
}

# 🧠 Classe IA
class NoeudCognitif:
    def __init__(self, nom, role):
        self.nom = nom
        self.role = role

    def repondre(self, prompt):
        try:
            lang = detect(prompt)
            prefix = {
                "fr": "",
                "ln": "Réponds en lingala : ",
                "en": "Answer in English: "
            }.get(lang, "")
            full_prompt = f"{prefix}{prompt}"

            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.role},
                    {"role": "user", "content": full_prompt}
                ]
            )
            return completion.choices[0].message.content.strip()
        except:
            return "🤖 [GPT indisponible]"

# 🧠 Noeuds IA
miss = NoeudCognitif("Miss AfrikyIA", "Coach business pour femmes africaines.")
sheteachia = NoeudCognitif("SheTeachIA", "Mentor éducatif qui aide aux devoirs et à l’apprentissage.")
shelove = NoeudCognitif("SheLoveIA", "Love coach pour bâtir une vie sentimentale saine.")
nkouma = NoeudCognitif("Nkouma", "Modératrice éthique. Répond toujours avec bienveillance.")

# 🧠 Sessions en mémoire
SESSIONS = {}

def activer_forfait(chat_id, forfait_id):
    infos = FORFAITS.get(forfait_id)
    if not infos:
        return False
    SESSIONS[chat_id] = {
        "forfait": forfait_id,
        "expires": datetime.now().timestamp() + infos["duree"] * 86400,
        "noeud": None
    }
    return True

def est_valide(chat_id):
    session = SESSIONS.get(chat_id)
    return session and datetime.now().timestamp() < session["expires"]

def set_noeud(chat_id, choix):
    if chat_id not in SESSIONS:
        return
    noeuds = {
        "business": miss,
        "education": sheteachia,
        "love": shelove
    }
    SESSIONS[chat_id]["noeud"] = noeuds.get(choix)

def get_noeud(chat_id):
    return SESSIONS.get(chat_id, {}).get("noeud", None)

# 💬 Telegram
def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def show_forfaits(chat_id):
    buttons = [
        [{"text": "🎟️ Essentiel – 1000 FCFA", "callback_data": "f_essentiel"}],
        [{"text": "🎟️ Premium – 5000 FCFA", "callback_data": "f_premium"}],
        [{"text": "🎟️ VIP – 10000 FCFA", "callback_data": "f_vip"}],
    ]
    send_message(chat_id, "Choisis ton forfait IA :", {"inline_keyboard": buttons})

def show_infos(chat_id, fkey):
    infos = FORFAITS[fkey]
    msg = (
        f"*{infos['nom']}*\n"
        f"⏳ Durée : {infos['duree']} jour(s)\n"
        f"📦 {infos['contenu']}\n\n"
        f"📲 Paiement par Airtel : +242 057538060"
    )
    buttons = [[{"text": "✅ J’ai payé", "callback_data": f"paid_{fkey}"}]]
    send_message(chat_id, msg, {"inline_keyboard": buttons})

def show_poles(chat_id):
    buttons = [
        [{"text": "📈 Business", "callback_data": "p_business"}],
        [{"text": "📚 Éducation", "callback_data": "p_education"}],
        [{"text": "💖 Love Plan", "callback_data": "p_love"}],
    ]
    send_message(chat_id, "📍 Quel pôle IA souhaites-tu explorer ?", {"inline_keyboard": buttons})

# 🎧 Envoi vocal du matin
def envoyer_audio_matin(chat_id):
    session = SESSIONS.get(chat_id)
    if not session or not est_valide(chat_id):
        return

    noeud = session.get("noeud")
    if not noeud:
        return

    try:
        prompts = {
            "Miss AfrikyIA": "Dis un message de motivation business pour bien commencer la journée.",
            "SheTeachIA": "Dis une astuce éducative ou une citation d'apprentissage pour motiver un enfant.",
            "SheLoveIA": "Dis une phrase inspirante pour nourrir l’amour de soi et des autres."
        }
        prompt = prompts.get(noeud.nom, "Dis un message inspirant pour démarrer la journée.")
        text = noeud.repondre(prompt)

        tts = gTTS(text=text, lang="fr")
        filename = f"audio_{chat_id}.mp3"
        tts.save(filename)

        with open(filename, "rb") as audio:
            requests.post(f"{TELEGRAM_API_URL}/sendVoice", files={"voice": audio}, data={"chat_id": chat_id})
        os.remove(filename)
    except Exception as e:
        print("Erreur audio matin:", e)

# ⏰ Boucle envoi automatique à 08h
def boucle_matin():
    while True:
        heure = datetime.now().strftime("%H:%M")
        if heure == "08:00":
            for chat_id in SESSIONS:
                envoyer_audio_matin(chat_id)
            time.sleep(60)
        time.sleep(30)

threading.Thread(target=boucle_matin, daemon=True).start()

# 🌐 Webhook principal
@app.route("/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "✅ Webhook actif"

    data = request.json
    chat_id = data.get("message", {}).get("chat", {}).get("id") or data.get("callback_query", {}).get("from", {}).get("id")

    if "message" in data:
        txt = data["message"].get("text", "")
        if txt == "/start":
            show_forfaits(chat_id)
        elif est_valide(chat_id):
            node = get_noeud(chat_id)
            if node:
                answer = node.repondre(txt)
                send_message(chat_id, answer)
            else:
                send_message(chat_id, "❗ Merci de choisir un pôle IA.")
                show_poles(chat_id)
        else:
            send_message(chat_id, "⛔ Forfait expiré ou non activé. Tape /start.")

    elif "callback_query" in data:
        data_cb = data["callback_query"]["data"]
        if data_cb.startswith("f_"):
            show_infos(chat_id, data_cb.replace("f_", ""))
        elif data_cb.startswith("paid_"):
            key = data_cb.replace("paid_", "")
            if activer_forfait(chat_id, key):
                send_message(chat_id, f"✅ Paiement confirmé ! Tu es connectée à *{key.title()}* pour {FORFAITS[key]['duree']} jour(s).")
                show_poles(chat_id)
        elif data_cb.startswith("p_"):
            domaine = data_cb.replace("p_", "")
            set_noeud(chat_id, domaine)
            send_message(chat_id, f"🎯 Super choix. {domaine.title()} est activé. Pose ta première question ✨")

    return "ok"

# 🧪 Route de simulation
@app.route("/simulate", methods=["GET"])
def simulate():
    r1 = sheteachia.repondre("Comment transmettre l'amour d'apprendre ?")
    r2 = miss.repondre("Peut-on monétiser une pédagogie ?")
    return "✅ Simulation IA ok"

# ✅ Route d'éthique
@app.route("/check-ethique", methods=["GET"])
def check_ethique():
    message = request.args.get("message", "")
    return {"analyse": nkouma.repondre(message)}

# 📤 Route manuelle pour envoyer un audio du matin à un ID précis
@app.route("/send-morning/<chat_id>", methods=["GET"])
def send_morning(chat_id):
    envoyer_audio_matin(int(chat_id))
    return f"✅ Audio du matin envoyé à {chat_id}"
