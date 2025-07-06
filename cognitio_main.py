from flask import Flask, request, jsonify
from gtts import gTTS
import openai
import os, json
from datetime import datetime

app = Flask(__name__)

# 🔐 Clés API
BOT_TOKEN = "TELEGRAM_BOT_TOKEN"
OPENAI_API_KEY = "TON_OPENAI_KEY"
openai.api_key = OPENAI_API_KEY

user_sessions = {}

# 📌 Données
LANGUES = ["Français", "Anglais", "Swahili", "Lingala", "Wolof", "Arabe", "Portugais"]
TONS = {
    "bienvaillante": "😊 Bienvaillante",
    "strategique": "📊 Stratégique",
    "zen": "🧘 Zen",
    "motivation": "🔥 Motivation"
}
GENRES = ["féminin", "masculin"]
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

# 🛡️ Nkouma : Filtrage éthique
def nkouma_guard(texte, parental=False):
    interdits = ["viol", "suicide", "pédoporno", "tuer", "arme", "esclavage"]
    if parental:
        interdits += ["sexe", "nudité", "mort", "insulte", "démon"]
    return not any(m in texte.lower() for m in interdits)

# 🎤 Génère message d’accueil
def generer_bienvenue(session):
    nom = session.get("nom", "ton ANI")
    langue = session.get("langue", "Français")
    tone = session.get("tone", "bienvaillante")
    profil = session.get("profil", "une personne")
    pole = session.get("pole", "général")
    genre = session.get("genre", "féminin")
    parental = session.get("parental", False)
    senior = session.get("senior", False)

    instruction = f"Tu es une IA {tone} nommée {nom}, de genre {genre}, pour {profil}. Pôle : {pole}. "
    if parental:
        instruction += "Langage protégé. "
    if senior:
        instruction += "Parle lentement, avec des mots simples. "
    instruction += f"Parle en {langue}."

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": "Génère un message d’accueil."}
        ]
    )
    return completion['choices'][0]['message']['content']

# 🎙️ Générer et sauvegarder un vocal
def creer_vocal(chat_id, texte, langue="fr"):
    tts = gTTS(text=texte, lang=langue[:2])
    filepath = f"ani_{chat_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
    tts.save(filepath)
    return filepath

# 🧪 Route simulation en console
def creation_ani(chat_id):
    session = {}
    print("🌍 Choisis ta langue :", LANGUES)
    session["langue"] = input("Langue choisie : ")

    print("\n🎭 Choisis le ton :", list(TONS.keys()))
    session["tone"] = input("Ton choisi : ")

    session["genre"] = input("\n👤 Genre de l'ANI (féminin/masculin) : ")
    session["parental"] = input("👶 Activer mode parental ? (y/n) : ").lower() == "y"
    session["senior"] = input("🧓 Activer mode senior ? (y/n) : ").lower() == "y"

    session["nom"] = input("\n💬 Choisis un prénom pour ton ANI : ")
    profil = input("✍️ À qui est destinée cette ANI ? ")
    if not nkouma_guard(profil, session["parental"]):
        return print("❌ Contenu bloqué par Nkouma.")
    session["profil"] = profil

    print("\n📍 Choisis un pôle :", POLES)
    session["pole"] = input("Pôle choisi : ")

    print("\n💰 Voici les forfaits disponibles :")
    for key, f in FORFAITS.items():
        print(f"{key} → {f['label']} – {f['messages']} messages / {f['jours']} jours")

    session["forfait"] = input("Ton choix de forfait (essentiel/premium/vip/elite) : ")

    print("\n💳 Simulation de paiement...")
    print("✅ Paiement validé ! ✨ Création de ton ANI...")

    msg = generer_bienvenue(session)
    user_sessions[chat_id] = session
    print(f"\n👋 Message d’accueil de {session['nom']} :\n{msg}")

    # Génère vocal
    path = creer_vocal(chat_id, msg, session["langue"])
    print(f"🔊 Vocal enregistré : {path}")
    return path

# 🚀 Route à appeler via CRON : /send-morning/<chat_id>
@app.route("/send-morning/<chat_id>")
def send_morning(chat_id):
    if chat_id not in user_sessions:
        return jsonify({"error": "Utilisateur inconnu."}), 404

    session = user_sessions[chat_id]
    msg = generer_bienvenue(session)
    audio_path = creer_vocal(chat_id, msg, session["langue"])

    return jsonify({
        "chat_id": chat_id,
        "nom": session["nom"],
        "langue": session["langue"],
        "vocal": audio_path,
        "message": msg
    })

# ✅ Lancer la création manuelle dans console
if __name__ == "__main__":
    chat_id = "test_001"
    creation_ani(chat_id)
    app.run(port=5000)
