from flask import Flask, request, jsonify
import openai
import json
import os
from gtts import gTTS
from datetime import datetime
import threading

app = Flask(__name__)

# 🔐 Clés API
BOT_TOKEN = "TON_TELEGRAM_BOT_TOKEN"
OPENAI_API_KEY = "TON_OPENAI_KEY"
openai.api_key = OPENAI_API_KEY
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 📁 Sessions utilisateurs
user_sessions = {}
user_chat_ids = set()

# 📌 Données de base
LANGUES = ["Français", "Anglais", "Swahili", "Lingala", "Wolof", "Arabe", "Portugais"]
TONS = {
    "bienvaillante": "😊 Bienvaillante",
    "strategique": "📊 Stratégique",
    "zen": "🧘 Zen",
    "motivation": "🔥 Motivation"
}
POLES = [
    "🧠 Éducation", "💼 Business", "🧘 Bien-être", "❤️ Maternité", "👵 SeniorCare",
    "🧒 Enfant", "🛡️ Éthique", "📖 Foi", "❤️ Amour", "💊 Santé"
]
FORFAITS = {
    "starter": {"label": "🔹 Starter – 1000 FCFA", "messages": 5, "jours": 3},
    "standard": {"label": "🔸 Standard – 2500 FCFA", "messages": 15, "jours": 7},
    "premium": {"label": "🔶 Premium – 5000 FCFA", "messages": 30, "jours": 15},
    "elite": {"label": "🌟 Élite – 10 000 FCFA", "messages": 50, "jours": 30}
}

# 🔐 Nkouma : Filtrage éthique
def nkouma_guard(texte, parental=False):
    interdits = ["viol", "suicide", "pédoporno", "tuer", "arme", "esclavage"]
    if parental:
        interdits += ["sexe", "nudité", "mort", "insulte", "démon"]
    return not any(m in texte.lower() for m in interdits)

# 🎤 GPT : message d’accueil
def generer_bienvenue(session):
    nom = session.get("nom", "ton ANI")
    langue = session.get("langue", "Français")
    tone = session.get("tone", "bienvaillante")
    profil = session.get("profil", "une personne")
    pole = session.get("pole", "général")
    parental = session.get("parental", False)
    senior = session.get("senior", False)

    instruction = f"Tu es une IA {tone}, nommée {nom}, pour {profil}. Pôle : {pole}. "
    if parental:
        instruction += "Langage protégé. "
    if senior:
        instruction += "Parle lentement, avec des mots simples. "
    instruction += f"Réponds uniquement en {langue.lower()}."

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": "Génère un message d’accueil chaleureux mais ne commence pas par 'Bonjour'. Sois bienveillant(e), simple et encourageant(e)."}
        ]
    )
    return completion['choices'][0]['message']['content']

# 🔊 Envoi vocal avec Gtts
def send_audio(chat_id, texte):
    tts = gTTS(texte, lang='fr')
    filename = f"audio_{chat_id}.mp3"
    tts.save(filename)
    with open(filename, "rb") as f:
        requests.post(
            f"{TELEGRAM_URL}/sendAudio",
            data={"chat_id": chat_id},
            files={"audio": f}
        )
    os.remove(filename)

# ⏰ Route CRON : envoyer message vocal à tous
@app.route("/send-morning", methods=["GET"])
def send_morning():
    texte = "Ceci est ton message vocal du matin. Prends soin de toi aujourd’hui. Tu es important(e) !"
    for chat_id in list(user_chat_ids):
        send_audio(chat_id, texte)
    return jsonify({"status": "envoyé à tous"}), 200

# 🤖 Route Webhook Telegram
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        user_chat_ids.add(chat_id)

        if "text" in message:
            handle_text(chat_id, message["text"])

    return jsonify({"ok": True})

# 📩 Logique textuelle
def handle_text(chat_id, text):
    session = user_sessions.get(chat_id, {})

    if text.lower().startswith("start") or "bonjour" in text.lower():
        user_sessions[chat_id] = {}
        show_language_menu(chat_id)

    elif text in LANGUES:
        session["langue"] = text
        show_tone_menu(chat_id)

    elif text in TONS:
        session["tone"] = text
        send_modes(chat_id)

    elif text.lower() in ["oui", "non"]:
        pass  # handled via inline boutons

    elif "forfait" in session and "nom" in session:
        if nkouma_guard(text):
            session["profil"] = text
            show_pole_menu(chat_id)
        else:
            send_message(chat_id, "❌ Contenu inapproprié bloqué par Nkouma.")
    else:
        session["nom"] = text
        send_message(chat_id, "✍️ Décris à qui est destinée cette ANI (ex : pour ma grand-mère, mon fils autiste, une maman stressée...)")
        session["étape"] = "profil"

# 🧭 Menus inline
def show_language_menu(chat_id):
    boutons = [{"text": lang, "callback_data": f"lang:{lang}"} for lang in LANGUES]
    send_inline_menu(chat_id, "🌍 Choisis ta langue :", boutons)

def show_tone_menu(chat_id):
    boutons = [{"text": v, "callback_data": f"tone:{k}"} for k, v in TONS.items()]
    send_inline_menu(chat_id, "🎭 Choisis le ton de ton ANI :", boutons)

def show_mode_menu(chat_id):
    boutons = [
        {"text": "👶 Mode parental", "callback_data": "mode:parental"},
        {"text": "🧓 Mode senior", "callback_data": "mode:senior"},
        {"text": "⏭️ Continuer", "callback_data": "continue"}
    ]
    send_inline_menu(chat_id, "🔧 Activer un mode spécial ?", boutons)

def show_pole_menu(chat_id):
    boutons = [{"text": pole, "callback_data": f"pole:{pole}"} for pole in POLES]
    send_inline_menu(chat_id, "📍 Choisis un pôle :", boutons)

def show_forfaits(chat_id):
    boutons = [{"text": f["label"], "callback_data": f"pay:{key}"} for key, f in FORFAITS.items()]
    send_inline_menu(chat_id, "💰 Choisis un forfait pour donner naissance à ton ANI :", boutons)

# 📤 Utilitaires
def send_message(chat_id, texte):
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={"chat_id": chat_id, "text": texte})

def send_inline_menu(chat_id, texte, boutons):
    keyboard = {"inline_keyboard": [[{"text": b["text"], "callback_data": b["callback_data"]}] for b in boutons]}
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": texte,
        "reply_markup": keyboard
    })

# 🎯 Inline callback
@app.route(f"/{BOT_TOKEN}/callback", methods=["POST"])
def callback():
    data = request.get_json()
    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        user_id = cb["from"]["id"]
        data_cb = cb["data"]
        session = user_sessions.setdefault(chat_id, {})

        if data_cb.startswith("lang:"):
            session["langue"] = data_cb.split(":")[1]
            show_tone_menu(chat_id)

        elif data_cb.startswith("tone:"):
            session["tone"] = data_cb.split(":")[1]
            show_mode_menu(chat_id)

        elif data_cb.startswith("mode:"):
            mode = data_cb.split(":")[1]
            session[mode] = not session.get(mode, False)
            show_mode_menu(chat_id)

        elif data_cb == "continue":
            send_message(chat_id, "📝 Donne un prénom à ton ANI :")

        elif data_cb.startswith("pole:"):
            session["pole"] = data_cb.split(":")[1]
            show_forfaits(chat_id)

        elif data_cb.startswith("pay:"):
            forfait_key = data_cb.split(":")[1]
            session["forfait"] = forfait_key
            msg = generer_bienvenue(session)
            send_message(chat_id, f"✅ ANI créée avec succès !\n\n👋 {msg}")

    return jsonify({"ok": True})

# 🌐 Route simple de test
@app.route("/", methods=["GET"])
def home():
    return "ANI Creator est en ligne ! ✅"
