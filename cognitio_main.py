from flask import Flask, request, jsonify
import openai
import json
import os
from gtts import gTTS
import requests

app = Flask(__name__)

# 🔐 Clés API
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

user_sessions = {}
violation_counts = {}

# 📌 Données
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
    "essentiel": {"label": "💡 Essentiel – 1000 FCFA", "messages": 10, "jours": 3},
    "premium": {"label": "🚀 Premium – 2500 FCFA", "messages": 20, "jours": 7},
    "vip": {"label": "👑 VIP – 5000 FCFA", "messages": 40, "jours": 15},
    "elite": {"label": "🌟 Élite – 10 000 FCFA", "messages": 100, "jours": 30}
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
    tone = session.get("tone", "gentille")
    profil = session.get("profil", "une personne")
    pole = session.get("pole", "général")
    parental = session.get("parental", False)
    senior = session.get("senior", False)

    instruction = f"Tu es une IA {tone} nommée {nom}, pour {profil}. Pôle : {pole}. "
    if parental:
        instruction += "Langage protégé. "
    if senior:
        instruction += "Parle lentement, mots simples. "
    instruction += f"Parle en {langue}."

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": "Génère un message d’accueil."}
        ]
    )
    return completion['choices'][0]['message']['content']

# 💬 Génère un vocal du matin
def generer_message_matin():
    prompt = "Crée un message vocal court et bienveillant pour bien démarrer la journée. Langue : français."
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion['choices'][0]['message']['content']

def envoyer_audio(chat_id, texte):
    tts = gTTS(text=texte, lang="fr")
    fichier = f"/tmp/audio_{chat_id}.mp3"
    tts.save(fichier)
    with open(fichier, "rb") as audio:
        requests.post(
            f"{TELEGRAM_API_URL}/sendVoice",
            data={"chat_id": chat_id},
            files={"voice": audio}
        )

# 📁 Charger les utilisateurs
def charger_utilisateurs():
    try:
        with open("utilisateurs.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("utilisateurs", [])
    except FileNotFoundError:
        return []

# 🌅 Route CRON – envoyer audio à tous
@app.route("/send-morning", methods=["GET"])
def send_morning():
    utilisateurs = charger_utilisateurs()
    message = generer_message_matin()
    for chat_id in utilisateurs:
        try:
            envoyer_audio(chat_id, message)
        except Exception as e:
            print(f"Erreur pour {chat_id} : {e}")
    return "✔️ Vocaux envoyés", 200

# 🧪 Test de création d’ANI (Console)
@app.route("/simulate", methods=["GET"])
def simulate():
    session = {}
    session["langue"] = "Français"
    session["tone"] = "bienvaillante"
    session["parental"] = False
    session["senior"] = False
    session["nom"] = "Sarah"
    session["profil"] = "une entrepreneure qui se sent débordée"
    session["pole"] = "💼 Business"
    session["forfait"] = "premium"

    msg = generer_bienvenue(session)
    print(json.dumps(session, indent=2, ensure_ascii=False))
    return jsonify({"message_bienvenue": msg})

# 🔐 Page d’accueil
@app.route("/")
def index():
    return "🤖 ANI Creator + Audio Matin OK"

if __name__ == "__main__":
    app.run(debug=True)
