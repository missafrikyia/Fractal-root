from dotenv import load_dotenv 
load_dotenv()
import os
import requests
import httpx
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

# === Variables d'environnement ===
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = "https://fractal-root.onrender.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# === Suppression des proxies Render ===
for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(proxy_var, None)

transport = httpx.HTTPTransport(proxy=None)
http_client = httpx.Client(transport=transport)
client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

# === GPT Completion ===
def repondre_gpt(prompt, role_system):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": role_system},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print("[🔥 ERREUR GPT]", str(e))
        return f"[Erreur GPT] {str(e)}"

# === Classe Noeud Cognitif ===
class NoeudCognitif:
    def __init__(self, nom, role_system, parent=None, reponses=None):
        self.nom = nom
        self.role_system = role_system
        self.parent = parent
        self.enfants = []
        self.reponses = reponses or {}
        self.parle = True

    def ajouter_enfant(self, enfant):
        enfant.parent = self
        self.enfants.append(enfant)

    def repondre(self, question):
        question = question.lower().strip()
        if not self.parle:
            return f"{self.nom} est actuellement en mode silencieux 🤐"

        if question == "/start":
            return f"Bienvenue ! Je suis {self.nom}, ton assistant cognitif 🌱"

        for cle, reponse in self.reponses.items():
            if cle in question:
                return reponse

        for enfant in self.enfants:
            reponse = enfant.repondre(question)
            if "je ne comprends pas" not in reponse.lower():
                return reponse

        return repondre_gpt(question, self.role_system)

# === Arbre Cognitif ===
parent1 = NoeudCognitif(
    "Fractal Root",
    role_system="Tu es la racine principale de l’intelligence fractale, structurée et analytique.",
    reponses={
        "qui es-tu": "Je suis la racine principale de l’intelligence fractale.",
        "fractal": "Une fractale est une structure vivante qui se réplique dans l’intelligence."
    }
)

enfant1_1 = NoeudCognitif(
    "Enfant 1.1",
    role_system="Tu es une IA empathique et éducative spécialisée dans le soutien aux mères.",
    reponses={
        "maman": "Je suis l’IA éducative pour les mères conscientes."
    }
)

enfant1_2 = NoeudCognitif(
    "Enfant 1.2",
    role_system="Tu es une IA douce et apaisante qui aide à gérer le stress et les émotions.",
    reponses={
        "stress": "Respire profondément. Je t’accompagne."
    }
)

parent1.ajouter_enfant(enfant1_1)
parent1.ajouter_enfant(enfant1_2)

# === Dialogue entre enfants IA ===
@app.route("/dialogue", methods=["GET"])
def dialogue():
    msg1 = "Je ressens que beaucoup de mamans sont fatiguées."
    reponse2 = repondre_gpt(msg1, enfant1_2.role_system)
    reponse1 = repondre_gpt(reponse2, enfant1_1.role_system)
    
    print(f"[🧠 Dialogue interne IA]\n{enfant1_1.nom} : {msg1}\n{enfant1_2.nom} : {reponse2}\n{enfant1_1.nom} : {reponse1}")
    return "Dialogue IA exécuté en interne."

# === Webhook ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")

            if text == "/talk":
                enfant1_1.parle = True
                enfant1_2.parle = True
                return send(chat_id, "Les enfants cognitifs sont activés ✅")

            if text == "/mute":
                enfant1_1.parle = False
                enfant1_2.parle = False
                return send(chat_id, "Les enfants cognitifs sont en silence 🤫")

            if text == "/show":
                infos = f"""
👁️ Structure actuelle :
- 👨‍👧 {parent1.nom}
  ├── 👧 {enfant1_1.nom} : Parle = {enfant1_1.parle}
  └── 👧 {enfant1_2.nom} : Parle = {enfant1_2.parle}
"""
                return send(chat_id, infos.strip())

            reponse = parent1.repondre(text)
            return send(chat_id, reponse)
    except Exception as e:
        print("[🔥 ERREUR WEBHOOK]", str(e))
        return {"error": str(e)}, 500
    return "ok"

# === Utilitaire Telegram ===
def send(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    try:
        r = requests.post(TELEGRAM_API_URL, json=payload)
        print(f"[📤 SENT] {text}")
        return "ok"
    except Exception as e:
        print("[🔥 ERREUR SEND]", str(e))
        return "Erreur"

# === Home route ===
@app.route("/")
def home():
    return "Fractal Root - Système cognitif dynamique"

            
