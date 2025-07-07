import uuid
from flask import Flask, request, jsonify
from langdetect import detect
from openai import OpenAI
import os, requests, json
from gtts import gTTS
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 🔐 Clés API
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

# 📁 Sessions utilisateurs
user_sessions = {}
user_chat_ids = set()

# 🌍 Langues, tons, pôles, forfaits
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
    "start": {
        "label": "💎 MyAiFab START – 9 €/semaine",
        "prix": "9",
        "devise": "€",
        "duree": 7,
        "messages": 20,
        "description": (
            "1 IA activée (nom + spécialité)\n"
            "⏳ 7 jours d’accès\n"
            "💬 20 messages (vocaux ou écrits)\n"
            "📍 1 pôle unique\n"
            "⚡ Réponse en <30 min\n"
            "📲 Support WhatsApp\n"
            "⏫ Upgrade possible"
        )
    },
    "pro": {
        "label": "💎 MyAiFab PRO – 29 €/mois",
        "prix": "29",
        "devise": "€",
        "duree": 30,
        "messages": 60,
        "description": (
            "IA personnalisée (langue, style, ton)\n"
            "🗓️ 30 jours d’accès\n"
            "💬 60 messages\n"
            "📍 2 pôles\n"
            "🧾 Résumé PDF mensuel\n"
            "🛠️ Intégration outils/scripts"
        )
    },
    "proplus": {
        "label": "⚡ MyAiFab PRO+ – 59 €/mois",
        "prix": "59",
        "devise": "€",
        "duree": 30,
        "messages": 150,
        "description": (
            "Jusqu’à 3 IA connectées\n"
            "💬 150 messages/mois\n"
            "⚡ Réponses express (<10 min de 9h à 18h)\n"
            "📍 4 pôles\n"
            "🔊 IA vocale + audio matin automatique\n"
            "👥 Connexion IA famille/équipe"
        )
    },
    "illimite": {
        "label": "🚀 MyAiFab ILLIMITÉ – 99 €/mois",
        "prix": "99",
        "devise": "€",
        "duree": 30,
        "messages": 9999,
        "description": (
            "🔓 Illimité (usage raisonnable)\n"
            "🤖 Jusqu’à 5 IA connectées\n"
            "🎙️ IA vocale, visuelle, émotionnelle, business\n"
            "🧠 Génération pitchs, visuels, business plans\n"
            "🔐 Accès API GPT / plateforme IA avancée"
        )
    }
}

# 🔐 Nkouma : Filtrage éthique
def nkouma_guard(texte, parental=False):
    interdits = ["viol", "suicide", "pédoporno", "tuer", "arme", "esclavage"]
    if parental:
        interdits += ["sexe", "nudité", "mort", "insulte", "démon"]
    return not any(m in texte.lower() for m in interdits)

# 🔊 Envoi audio
def envoyer_vocal(chat_id, texte):
    tts = gTTS(text=texte, lang="fr")
    filename = f"voice_{uuid.uuid4().hex}.mp3"
    filepath = os.path.join("static/audio", filename)
    os.makedirs("static/audio", exist_ok=True)  # Crée le dossier si besoin
    tts.save(filepath)
    with open(filepath, 'rb') as f:
        requests.post(f"{TELEGRAM_URL}/sendVoice", data={"chat_id": chat_id}, files={"voice": f})
    os.remove(filepath)

# ⏰ Route CRON vocale
@app.route("/send-morning", methods=["GET"])
def send_morning():
    texte = "Bonjour ☀️ ! Voici ton message vocal du matin. Tu es capable, tu es digne, et cette journée est à toi !"
    for chat_id in list(user_chat_ids):
        send_audio(chat_id, texte)
    return jsonify({"status": "envoyé à tous"}), 200

# 🤖 Webhook Telegram
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "callback_query" in data:
        return handle_callback(data)
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_chat_ids.add(chat_id)
        texte = data["message"].get("text", "")
        handle_text(chat_id, texte)
    return jsonify({"ok": True})

# 📩 Traitement texte
def handle_text(chat_id, text):
    session = user_sessions.setdefault(chat_id, {})
    cleaned = text.lower().strip()

    if cleaned in ["start", "/start"]:
        show_language_menu(chat_id)

    elif session.get("étape") == "nom":
        session["nom"] = text
        session["étape"] = "profil"
        send_message(chat_id, "✍️ Décris à qui est destinée cette ANI.")

    elif session.get("étape") == "profil":
        if nkouma_guard(text, parental=session.get("parental", False)):
            session["profil"] = text
            show_pole_menu(chat_id)
        else:
            send_message(chat_id, "❌ Contenu inapproprié.")

elif session.get("étape") == "conversation":
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
    instruction += f"Réponds uniquement en {langue.lower()}. "
    instruction += "Tu peux aussi répondre en vocal grâce à une synthèse vocale."

    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": text}
            ]
        )
        reponse = completion.choices[0].message.content.strip()
        send_message(chat_id, reponse)
        envoyer_vocal(chat_id, reponse)
    except Exception as e:
        send_message(chat_id, f"❌ Une erreur est survenue : {str(e)}")

# 🧠 Générer message de bienvenue
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
    instruction += f"Réponds uniquement en {langue.lower()}. "
    instruction += "Tu peux aussi répondre en vocal grâce à une synthèse vocale. Si l'utilisateur ne peut pas écrire, propose-lui de lui répondre à l'oral. "

    user_prompt = (
        f"Présente-toi comme une IA nommée {nom}, conçue pour {profil}. "
        f"Sois chaleureuse, adapte ton ton ({tone}). Termine par : 'Que puis-je faire pour toi aujourd’hui ?'"
    )

    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": user_prompt}
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
    session = user_sessions.get(chat_id, {})
    boutons = [
        {"text": f"👶 Mode parental {'✅' if session.get('parental') else ''}", "callback_data": "mode:parental"},
        {"text": f"🧓 Mode senior {'✅' if session.get('senior') else ''}", "callback_data": "mode:senior"},
        {"text": "⏭️ Continuer", "callback_data": "continue"}
    ]
    send_inline_menu(chat_id, "🔧 Activer un mode spécial ?", boutons)

def show_pole_menu(chat_id):
    boutons = [{"text": pole, "callback_data": f"pole:{pole}"} for pole in POLES]
    send_inline_menu(chat_id, "📍 Choisis un pôle :", boutons)

def show_forfaits(chat_id):
    session = user_sessions.setdefault(chat_id, {})

    # 📨 Introduction
    intro = (
        "📦 *Voici nos formules MyAiFab :*\n\n"
        "💳 Paiement CB sécurisé : [Clique ici](https://myaishop.com/paiement)\n"
        "✅ Une fois payé, clique sur 'J’ai payé'."
    )
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": intro,
        "parse_mode": "Markdown"
    })

    # 📲 Boutons avec descriptions intégrées (1 message par formule)
    for key, f in FORFAITS.items():
        texte = (
            f"*{f['label']}*\n"
            f"{f['description']}\n\n"
            "👇"
        )
        bouton = [{"text": "📌 J’ai payé", "callback_data": f"pay:{key}"}]
        send_inline_menu(chat_id, texte, bouton, parse_mode="Markdown")

# 📤 Fonctions d’envoi
def send_message(chat_id, texte):
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={"chat_id": chat_id, "text": texte})

def send_inline_menu(chat_id, texte, boutons, parse_mode=None):
    keyboard = {"inline_keyboard": [[{"text": b["text"], "callback_data": b["callback_data"]}] for b in boutons]}
    payload = {
        "chat_id": chat_id,
        "text": texte,
        "reply_markup": keyboard
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    requests.post(f"{TELEGRAM_URL}/sendMessage", json=payload)

# 🔁 Callback centralisé (inchangé)
def handle_callback(data):
    cb = data["callback_query"]
    chat_id = cb["message"]["chat"]["id"]
    data_cb = cb["data"]
    session = user_sessions.setdefault(chat_id, {})

    if data_cb.startswith("lang:"):
        session["langue"] = data_cb.split(":", 1)[1]
        send_message(chat_id, f"🌐 Langue sélectionnée : {session['langue']}")
        show_tone_menu(chat_id)

    elif data_cb.startswith("tone:"):
        session["tone"] = data_cb.split(":", 1)[1]
        send_message(chat_id, f"🎭 Ton sélectionné : {TONS.get(session['tone'], session['tone'])}")
        send_modes(chat_id)

    elif data_cb.startswith("mode:"):
        mode = data_cb.split(":", 1)[1]
        session[mode] = not session.get(mode, False)
        etat = "activé ✅" if session[mode] else "désactivé ❌"
        send_message(chat_id, f"🔧 Mode {mode} : {etat}")
        send_modes(chat_id)

    elif data_cb == "continue":
        session["étape"] = "nom"
        send_message(chat_id, "📝 Donne un prénom à ton ANI :")

    elif data_cb.startswith("pole:"):
        session["pole"] = data_cb.split(":", 1)[1]
        show_forfaits(chat_id)

    elif data_cb.startswith("pay:"):
        session["forfait"] = data_cb.split(":", 1)[1]
        if not session.get("ani_crée"):
            try:
                msg = generer_bienvenue(session)
                send_message(chat_id, f"✅ ANI créée avec succès !\n\n{msg}")
                send_audio(chat_id, msg)
                session["ani_crée"] = True
                session["étape"] = "conversation"
            except Exception as e:
                send_message(chat_id, f"❌ Erreur : {str(e)}")
        else:
            send_message(chat_id, "🔁 ANI déjà activée.")

    user_sessions[chat_id] = session
    return jsonify({"ok": True})

# ✅ Route test
@app.route("/", methods=["GET"])
def home():
    return "✅ ANI Creator en ligne"
