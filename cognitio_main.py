from flask import Flask, request, jsonify
from langdetect import detect
from openai import OpenAI
import os
import requests
from gtts import gTTS
from datetime import datetime

app = Flask(__name__)

# 🔐 Clés API
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

# 📁 Sessions utilisateurs
user_sessions = {}
user_chat_ids = set()

# 🌐 Langues, tons, pôles, forfaits
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

# 🔊 Envoi audio
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

# ⏰ Route CRON vocale pour Render
@app.route("/send-morning", methods=["GET"])
def send_morning():
    texte = "Bonjour ☀️ ! Voici ton message vocal du matin. Tu es capable, tu es digne, et cette journée est à toi !"
    for chat_id in list(user_chat_ids):
        send_audio(chat_id, texte)
    return jsonify({"status": "envoyé à tous"}), 200

# 🤖 Accueil Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_chat_ids.add(chat_id)
        texte = data["message"].get("text", "")
        handle_text(chat_id, texte)
    return jsonify({"ok": True})

# 📩 Message texte
def handle_text(chat_id, text):
    session = user_sessions.setdefault(chat_id, {})

    if text.lower().startswith("start"):
        show_language_menu(chat_id)

    elif session.get("étape") == "nom":
        session["nom"] = text
        session["étape"] = "profil"
        send_message(chat_id, "✍️ Décris à qui est destinée cette ANI (ex : pour ma grand-mère, mon fils, une maman stressée...)")

    elif session.get("étape") == "profil":
        if nkouma_guard(text):
            session["profil"] = text
            show_pole_menu(chat_id)
        else:
            send_message(chat_id, "❌ Contenu inapproprié.")
    else:
        send_message(chat_id, "Utilise les boutons ci-dessous pour commencer.")

# 🧠 Générer message de bienvenue avec GPT-4
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

    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": "Génère un message d’accueil chaleureux mais ne commence pas par 'Bonjour'. Sois simple, bienveillant(e) et encourageant(e)."}
        ]
    )
    return completion.choices[0].message.content

# 📍 Menus inline
def show_language_menu(chat_id):
    boutons = [{"text": lang, "callback_data": f"lang:{lang}"} for lang in LANGUES]
    send_inline_menu(chat_id, "🌍 Choisis ta langue :", boutons)

def show_tone_menu(chat_id):
    boutons = [{"text": v, "callback_data": f"tone:{k}"} for k, v in TONS.items()]
    send_inline_menu(chat_id, "🎭 Choisis le ton de ton ANI :", boutons)

def send_modes(chat_id):
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
    send_message(chat_id, "📦 Voici nos forfaits pour activer ton ANI :")
    send_inline_menu(chat_id, "💰 Choisis ton forfait :", boutons)

# 📤 Envoi messages & menus
def send_message(chat_id, texte):
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={"chat_id": chat_id, "text": texte})

def send_inline_menu(chat_id, texte, boutons):
    keyboard = {"inline_keyboard": [[{"text": b["text"], "callback_data": b["callback_data"]}] for b in boutons]}
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": texte,
        "reply_markup": keyboard
    })

# 🔁 Callbacks inline
@app.route("/callback", methods=["POST"])
def callback():
    data = request.get_json()
    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data_cb = cb["data"]
        session = user_sessions.setdefault(chat_id, {})

        if data_cb.startswith("lang:"):
            session["langue"] = data_cb.split(":")[1]
            show_tone_menu(chat_id)

        elif data_cb.startswith("tone:"):
            session["tone"] = data_cb.split(":")[1]
            send_modes(chat_id)

        elif data_cb.startswith("mode:"):
            mode = data_cb.split(":")[1]
            session[mode] = not session.get(mode, False)
            send_modes(chat_id)

        elif data_cb == "continue":
            session["étape"] = "nom"
            send_message(chat_id, "📝 Donne un prénom à ton ANI :")

        elif data_cb.startswith("pole:"):
            session["pole"] = data_cb.split(":")[1]
            show_forfaits(chat_id)

        elif data_cb.startswith("pay:"):
            session["forfait"] = data_cb.split(":")[1]
            try:
                msg = generer_bienvenue(session)
                send_message(chat_id, f"✅ ANI créée avec succès !\n\n{msg}")
                send_audio(chat_id, msg)
            except Exception as e:
                send_message(chat_id, f"❌ Une erreur est survenue : {str(e)}")

        user_sessions[chat_id] = session

    return jsonify({"ok": True})

# ✅ Test de vie
@app.route("/", methods=["GET"])
def home():
    return "✅ ANI Creator en ligne"
