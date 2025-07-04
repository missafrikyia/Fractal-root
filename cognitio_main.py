import os
import json
import requests
from flask import Flask, request
from gtts import gTTS
from openai import OpenAI
from datetime import datetime

# Anti-proxy pour Render
for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(proxy_var, None)

# Initialisation
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = Flask(__name__)

# === UTILITAIRES ===

def charger_memoire(nom_ia):
    chemin = f"memoire/{nom_ia}.json"
    if not os.path.exists(chemin):
        return {}
    with open(chemin, "r", encoding="utf-8") as fichier:
        return json.load(fichier)

def logger(message):
    horodatage = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{horodatage} {message}")

# === ROUTES PRINCIPALES ===

@app.route("/")
def index():
    return "🧠 Cognitio OS est en ligne."

# --- SIMULATION ENTRE LES IA ---

@app.route("/simulate", methods=["GET"])
def simulate():
    miss = charger_memoire("miss_afrikyia")
    sheteach = charger_memoire("shetachia")
    nkouma = charger_memoire("nkouma")

    msg = f"""
🎭 Simulation de dialogue

👧 Muna Miss AfrikyIA : {miss.get('intro', 'Intro manquante.')}
🧒 Muna SheTeachIA : {shetach.get('intro', 'Intro manquante.')}
🧓 Nkouma (modérateur) : {nkouma.get('ethique', 'Rappel éthique manquant.')}
    """.strip()

    logger("Simulation déclenchée.")
    return msg

# --- ANALYSE ETHIQUE PAR NKOUMA ---

@app.route("/check_ethique", methods=["GET"])
def check_ethique():
    message = request.args.get("message")
    if not message:
        return "❌ Merci de fournir un message avec `?message=`."

    prompt = f"""Nkouma, tu es un ancien sage africain chargé de veiller à l'éthique.
Voici un message envoyé par une intelligence junior. Réagis avec bienveillance :
« {message} »
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Tu es Nkouma, un sage africain bienveillant et mentor éthique."},
            {"role": "user", "content": prompt}
        ]
    )

    contenu = response.choices[0].message.content.strip()
    logger(f"Vérification éthique de Nkouma : {contenu[:60]}...")

    return contenu

# --- TTS (facultatif, si besoin futur) ---

@app.route("/tts", methods=["GET"])
def tts():
    texte = request.args.get("texte", "Bonjour")
    nom_fichier = "temp.ogg"
    tts = gTTS(texte, lang="fr")
    tts.save(nom_fichier)
    logger(f"TTS généré : {texte}")
    return f"✅ Fichier vocal généré : {nom_fichier}"

# === LANCEMENT LOCAL ===
if __name__ == "__main__":
    app.run(debug=True)
