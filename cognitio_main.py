from flask import Flask, request, jsonify
from openai import OpenAI
from gtts import gTTS
import os, json, requests
from datetime import datetime
from langdetect import detect

app = Flask(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
GPT = OpenAI(api_key=OPENAI_API_KEY)

DATA_FILE = "utilisateurs.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

LANGUES = ["Français", "Anglais", "Swahili", "Lingala", "Wolof", "Arabe", "Portugais"]
TONS = {
    "bienvaillante": "😊 Bienvaillante",
    "strategique": "📊 Stratégique",
    "zen": "🧘 Zen",
    "motivation": "🔥 Motivation"
}
POLES = [
    "🧠 Éducation", "💼 Business", "🧘 Bien-être", "❤️ Maternité",
    "👵 SeniorCare", "🧒 Enfant", "🛡️ Éthique", "📖 Foi",
    "❤️ Amour", "💊 Santé"
]
FORFAITS = {
    "essentiel": {"label": "Essentiel – 1000 FCFA (5 messages)", "messages": 5},
    "premium": {"label": "Premium – 2500 FCFA (15 messages)", "messages": 15},
    "vip": {"label": "VIP – 5000 FCFA (40 messages)", "messages": 40},
    "elite": {"label": "Élite – 10 000 FCFA (100 messages)", "messages": 100}
}


def save_user(chat_id, data):
    with open(DATA_FILE, "r") as f:
        users = json.load(f)
    users[str(chat_id)] = data
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)


def get_all_chat_ids():
    with open(DATA_FILE, "r") as f:
        return list(json.load(f).keys())


def nkouma_guard(texte):
    interdits = ["viol", "suicide", "pédoporno", "tuer", "arme", "esclavage", "sexe", "démon"]
    return not any(m in texte.lower() for m in interdits)


def gpt_message_accueil(session):
    nom = session.get("nom", "ton ANI")
    tone = session.get("tone", "bienvaillante")
    profil = session.get("profil", "une personne")
    pole = session.get("pole", "général")
    langue = session.get("langue", "Français")

    prompt = f"""
Tu es une IA {tone}, nommée {nom}. Tu accompagnes {profil} dans le domaine {pole}.
Tu t’exprimes uniquement en {langue}, avec douceur, empathie et clarté.
Génère un message d’accueil court (3 phrases max), chaleureux et adapté à ton rôle.
"""
    chat = GPT.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}]
    )
    return chat.choices[0].message.content.strip()


def envoyer_message(chat_id, texte):
    requests.post(f"{TELEGRAM_API}/sendMessage", data={"chat_id": chat_id, "text": texte})


def envoyer_inline(chat_id, texte, boutons):
    reply_markup = {"inline_keyboard": [[{"text": b["label"], "callback_data": b["data"]}] for b in boutons]}
    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": texte, "reply_markup": reply_markup})


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    chat_id = str(data["message"]["chat"]["id"]) if "message" in data else str(data["callback_query"]["message"]["chat"]["id"])
    message_text = data.get("message", {}).get("text", "") or data.get("callback_query", {}).get("data", "")
    session = {}

    if message_text == "/start":
        boutons = [{"label": l, "data": f"langue:{l}"} for l in LANGUES]
        envoyer_inline(chat_id, "🌍 Choisis ta langue :", boutons)
        return jsonify(ok=True)

    if message_text.startswith("langue:"):
        session["langue"] = message_text.split(":")[1]
        boutons = [{"label": v, "data": f"tone:{k}"} for k, v in TONS.items()]
        envoyer_inline(chat_id, "🎭 Choisis le ton :", boutons)
        save_user(chat_id, session)
        return jsonify(ok=True)

    if message_text.startswith("tone:"):
        with open(DATA_FILE) as f:
            users = json.load(f)
        session = users.get(chat_id, {})
        session["tone"] = message_text.split(":")[1]
        envoyer_message(chat_id, "💬 Donne un prénom à ton ANI :")
        save_user(chat_id, session)
        return jsonify(ok=True)

    if "text" in data.get("message", {}):
        with open(DATA_FILE) as f:
            users = json.load(f)
        session = users.get(chat_id, {})

        if "nom" not in session:
            nom = message_text
            session["nom"] = nom
            envoyer_message(chat_id, "🧬 Décris le profil de la personne à qui est destinée cette ANI :")
            save_user(chat_id, session)
            return jsonify(ok=True)

        elif "profil" not in session:
            if not nkouma_guard(message_text):
                envoyer_message(chat_id, "❌ Message bloqué par Nkouma.")
                return jsonify(ok=True)
            session["profil"] = message_text
            boutons = [{"label": p, "data": f"pole:{p}"} for p in POLES]
            envoyer_inline(chat_id, "📍 Choisis un pôle :", boutons)
            save_user(chat_id, session)
            return jsonify(ok=True)

    if message_text.startswith("pole:"):
        pole = message_text.split(":")[1]
        with open(DATA_FILE) as f:
            users = json.load(f)
        session = users.get(chat_id, {})
        session["pole"] = pole
        boutons = [{"label": FORFAITS[k]["label"], "data": f"forfait:{k}"} for k in FORFAITS]
        envoyer_inline(chat_id, "💰 Choisis ton forfait pour valider la naissance :", boutons)
        save_user(chat_id, session)
        return jsonify(ok=True)

    if message_text.startswith("forfait:"):
        forfait = message_text.split(":")[1]
        with open(DATA_FILE) as f:
            users = json.load(f)
        session = users.get(chat_id, {})
        session["forfait"] = forfait
        message = gpt_message_accueil(session)
        envoyer_message(chat_id, f"🎉 Bienvenue ! Je suis {session['nom']}, ton ANI {session['pole']}.\n\n{message}")
        save_user(chat_id, session)
        return jsonify(ok=True)

    return jsonify(ok=True)


@app.route("/send-morning", methods=["GET"])
def send_morning_audio():
    chat_ids = get_all_chat_ids()
    for chat_id in chat_ids:
        with open(DATA_FILE) as f:
            session = json.load(f).get(chat_id, {})
        if not session:
            continue
        text = gpt_message_accueil(session)
        tts = gTTS(text=text, lang="fr")
        filepath = f"audio_{chat_id}.mp3"
        tts.save(filepath)
        files = {"voice": open(filepath, "rb")}
        requests.post(f"{TELEGRAM_API}/sendVoice", data={"chat_id": chat_id}, files=files)
        os.remove(filepath)
    return jsonify(ok=True)
