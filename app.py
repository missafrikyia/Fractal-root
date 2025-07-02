import os
from flask import Flask, request
import requests
import openai

app = Flask(__name__)

# === CONFIGURATION ===
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = "https://fractal-root.onrender.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
openai.api_key = OPENAI_API_KEY

AFFICHER_DIALOGUE_IA = True

# === WEBHOOK SETUP ===
@app.route('/set_webhook')
def set_webhook():
    if not TOKEN:
        return {"error": "Token non défini"}, 500
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    r = requests.get(url)
    return r.json()

# === NOEUD COGNITIF ===
class NoeudCognitif:
    def __init__(self, nom, parent=None, reponses=None):
        self.nom = nom
        self.parent = parent
        self.enfants = []
        self.reponses = reponses or {}

    def ajouter_enfant(self, enfant):
        enfant.parent = self
        self.enfants.append(enfant)

    def repondre(self, question):
        question = question.lower().strip()

        if question == "/start":
            return f"Bienvenue ! Je suis {self.nom}, ton assistant cognitif 🌱"

        for cle, reponse in self.reponses.items():
            if cle in question:
                return reponse

        for enfant in self.enfants:
            reponse = enfant.repondre(question)
            if "je ne comprends pas" not in reponse.lower():
                return reponse

        return f"Je suis {self.nom} et je ne comprends pas ta question."

    def dialoguer_avec(self, autre_noeud, question, chat_id=None):
        log = f"{self.nom} demande à {autre_noeud.nom} : \"{question}\""
        reponse = autre_noeud.repondre(question)
        log_reponse = f"{autre_noeud.nom} répond : \"{reponse}\""

        if AFFICHER_DIALOGUE_IA and chat_id:
            requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": log})
            requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": log_reponse})

        return reponse

    def gpt_repond(self, prompt):
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"Erreur OpenAI: {str(e)}"

# === CREATION ARBRE ===
parent1 = NoeudCognitif("Fractal Root", reponses={
    "qui es-tu": "Je suis la racine principale de l’intelligence fractale.",
    "fractal": "Une fractale est une structure qui se répète à l’infini."
})

enfant1_1 = NoeudCognitif("Enfant 1.1", reponses={
    "rôle": "Je suis l’assistante éducative pour les mamans."
})

enfant1_2 = NoeudCognitif("Enfant 1.2", reponses={
    "stress": "Commence par respirer profondément. Tu n’es pas seule."
})

parent1.ajouter_enfant(enfant1_1)
parent1.ajouter_enfant(enfant1_2)

# === FLASK ROUTES ===
@app.route("/", methods=["GET"])
def home():
    return "Fractal Root - IA cognitive enrichie"

@app.route("/webhook", methods=["POST"])
def webhook():
    global AFFICHER_DIALOGUE_IA
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        question = data["message"].get("text", "")

        if question.lower() == "/talk":
            enfant1_1.dialoguer_avec(enfant1_2, "Comment aider une maman stressée ?", chat_id=chat_id)
            enfant1_2.dialoguer_avec(enfant1_1, "Quel est ton rôle dans l’arbre cognitif ?", chat_id=chat_id)
            return "ok"

        if question.lower() == "/mute":
            AFFICHER_DIALOGUE_IA = False
            requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": "🔇 Dialogue IA masqué."})
            return "ok"

        if question.lower() == "/show":
            AFFICHER_DIALOGUE_IA = True
            requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": "🔊 Dialogue IA visible."})
            return "ok"

        if question.lower().startswith("gpt:"):
            prompt = question[4:].strip()
            reponse = parent1.gpt_repond(prompt)
        else:
            reponse = parent1.repondre(question)

        payload = {"chat_id": chat_id, "text": reponse}
        requests.post(TELEGRAM_API_URL, json=payload)

    return "ok"
