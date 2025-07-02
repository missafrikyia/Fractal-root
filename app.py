from dotenv import load_dotenv 
load_dotenv()
import os
from flask import Flask, request
import requests
import httpx
from openai import OpenAI

# 🔐 Config
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = "https://fractal-root.onrender.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# 🧹 Suppression des proxies Render
for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(proxy_var, None)

# 🔗 OpenAI
transport = httpx.HTTPTransport(proxy=None)
http_client = httpx.Client(transport=transport)
client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

# 🚦 Flask
app = Flask(__name__)

# 🌱 Classe Noeud Cognitif
class NoeudCognitif:
    def __init__(self, nom, identite, parent=None, reponses=None):
        self.nom = nom
        self.identite = identite
        self.parent = parent
        self.enfants = []
        self.reponses = reponses or {}
        self.visible = True

    def ajouter_enfant(self, enfant):
        enfant.parent = self
        self.enfants.append(enfant)

    def generer_reponse_gpt(self, question):
        try:
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.identite},
                    {"role": "user", "content": question},
                ]
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return "Erreur GPT."

    def repondre(self, question):
        question = question.lower().strip()
        if question == "/start":
            return f"Bienvenue ! Je suis {self.nom} 🌱"

        for cle, reponse in self.reponses.items():
            if cle in question:
                return reponse

        if self.visible:
            for enfant in self.enfants:
                reponse = enfant.repondre(question)
                if "je ne comprends pas" not in reponse.lower():
                    return reponse

        return self.generer_reponse_gpt(question)

# 🌳 Construction de l’arbre cognitif
parent1 = NoeudCognitif("Fractal Root", identite="Tu es la racine principale d'une IA fractale. Tu organises les flux d'information entre les modules enfants.", reponses={
    "qui es-tu": "Je suis la racine de l’intelligence fractale.",
    "fractal": "Une fractale est une structure auto-répétée.",
})

enfant1_1 = NoeudCognitif("Enfant 1.1", identite="Tu es une IA éducative pour les mamans, bienveillante, simple et encourageante.", reponses={
    "rôle": "J’aide les mamans à mieux comprendre leurs enfants.",
})

enfant1_2 = NoeudCognitif("Enfant 1.2", identite="Tu es une IA de soutien émotionnel pour les femmes stressées.", reponses={
    "stress": "Respire doucement. Tu n’es pas seule.",
})

parent1.ajouter_enfant(enfant1_1)
parent1.ajouter_enfant(enfant1_2)

# 📬 Webhook Telegram
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        question = data["message"].get("text", "")
        reponse = parent1.repondre(question)
        payload = {"chat_id": chat_id, "text": reponse}
        requests.post(TELEGRAM_API_URL, json=payload)
    return "ok"

# 🛠 Routes utiles
@app.route("/", methods=["GET"])
def home():
    return "Fractal Root - IA cognitive enrichie avec GPT"

@app.route("/set_webhook")
def set_webhook():
    if not TOKEN:
        return {"error": "Token non défini"}, 500
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    return requests.get(url).json()

@app.route("/talk")
def talk():
    enfant1_1.visible = True
    enfant1_2.visible = True
    return "Les enfants sont activés."

@app.route("/mute")
def mute():
    enfant1_1.visible = False
    enfant1_2.visible = False
    return "Les enfants sont désactivés."

@app.route("/show")
def show():
    return {
        "parent": parent1.nom,
        "enfants": [e.nom for e in parent1.enfants],
        "actifs": [e.nom for e in parent1.enfants if e.visible]
    }
