from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
from flask import Flask, request
from openai import OpenAI
from gtts import gTTS
from datetime import datetime

app = Flask(__name__)

# 🔐 Clés d'API
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

# 📁 Dossiers
os.makedirs("memoire", exist_ok=True)
os.makedirs("data", exist_ok=True)

ABONNEMENTS_PATH = "data/abonnements.json"
UTILISATEURS_PATH = "data/utilisateurs.json"

# 📦 Chargement des forfaits
with open(ABONNEMENTS_PATH, "r", encoding="utf-8") as f:
    FORFAITS = json.load(f)

# 📦 Chargement utilisateurs
if os.path.exists(UTILISATEURS_PATH):
    with open(UTILISATEURS_PATH, "r", encoding="utf-8") as f:
        UTILISATEURS = json.load(f)
else:
    UTILISATEURS = {}

# 🧠 Classe IA
class NoeudCognitif:
    def __init__(self, nom, role, fichier_memoire=None, parent=None, reponses=None):
        self.nom = nom
        self.role = role
        self.parent = parent
        self.enfants = []
        self.reponses = reponses or {}
        self.parle = True
        self.fichier_memoire = fichier_memoire
        self.memoire = self.charger_memoire()

    def ajouter_enfant(self, enfant):
        enfant.parent = self
        self.enfants.append(enfant)

    def repondre(self, question):
        question = question.lower().strip()
        if not self.parle:
            return f"{self.nom} est silencieux."

        if question == "/start":
            return f"Bonjour, je suis {self.nom}. Je suis là pour te guider avec clarté et stratégie."

        for cle, reponse in self.reponses.items():
            if cle in question:
                return reponse

        for enfant in self.enfants:
            reponse = enfant.repondre(question)
            if "je ne comprends pas" not in reponse.lower():
                return reponse

        gpt_reply = self.appel_gpt(question)
        self.memoire[datetime.now().isoformat()] = {"question": question, "réponse": gpt_reply}
        self.sauvegarder_memoire()
        return gpt_reply

    def appel_gpt(self, prompt):
        try:
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.role},
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices[0].message.content.strip()
        except:
            return "[GPT indisponible]"

    def charger_memoire(self):
        if not self.fichier_memoire:
            return {}
        path = os.path.join("memoire", self.fichier_memoire)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def sauvegarder_memoire(self):
        if not self.fichier_memoire:
            return
        path = os.path.join("memoire", self.fichier_memoire)
        with open(path, "w") as f:
            json.dump(self.memoire, f, indent=2)

# 🌱 Noeuds
nkouma = NoeudCognitif("Nkouma", "Modératrice éthique", "nkouma.json", reponses={"insulter": "Merci de reformuler avec bienveillance."})
miss = NoeudCognitif("Miss AfrikyIA", "Coach business", "miss_afrikyia.json", reponses={"plan": "Un bon plan commence par une bonne vision."})
sheteachia = NoeudCognitif("SheTeachIA", "Mentor éducatif", "sheteachia.json", reponses={"devoirs": "Je peux t’aider pour les devoirs."})
nkouma.ajouter_enfant(miss)
nkouma.ajouter_enfant(sheteachia)

# ✅ MENUS & INLINE

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(reply_markup) if reply_markup else None
    }
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def show_main_menu(chat_id):
    buttons = [
        [{"text": "📈 Business", "callback_data": "p_business"}],
        [{"text": "📚 Éducation", "callback_data": "p_education"}]
    ]
    send_message(chat_id, "👋 Bonjour ! Qu’est-ce qu’on augmente aujourd’hui ?", {"inline_keyboard": buttons})

def show_submenu(chat_id, domaine):
    if domaine == "business":
        poles = [("Plan", "s_plan"), ("Visuel", "s_visuel"), ("Branding", "s_branding")]
    else:
        poles = [("École d’été", "s_ecole"), ("Aide aux devoirs", "s_devoirs")]
    buttons = [[{"text": nom, "callback_data": code}] for nom, code in poles]
    send_message(chat_id, f"🧭 Choisis un sous-pôle ({domaine.title()}) :", {"inline_keyboard": buttons})

def show_forfaits(chat_id, pole):
    buttons = []
    for key, infos in FORFAITS.items():
        btn_text = f"{infos['nom']} – {infos['prix']} FCFA"
        buttons.append([{"text": btn_text, "callback_data": f"infos_{key}"}])
    send_message(chat_id, f"💸 Choisis ton forfait pour le pôle **{pole}** :", {"inline_keyboard": buttons})

def show_inline_info(chat_id, forfait_key):
    infos = FORFAITS.get(forfait_key)
    if not infos:
        send_message(chat_id, "❌ Forfait non reconnu.")
        return

    text = (
        f"🎟️ *{infos['nom']}*\n"
        f"⏳ *{infos['duree']}*\n"
        f"📦 *{infos['contenu']}*\n"
        f"📲 Paiement Airtel : [📞 +242 057538060](tel:+242057538060)"
    )
    button = [[{"text": "✅ J’ai payé", "callback_data": f"activate_{forfait_key}"}]]
    send_message(chat_id, text, {"inline_keyboard": button})

# 🧠 Activation via GET
@app.route("/activate", methods=["GET"])
def activate():
    chat_id = request.args.get("chat_id")
    forfait = request.args.get("forfait")
    if not chat_id or not forfait:
        return "❌ Manque chat_id ou forfait"
    if forfait not in FORFAITS:
        return "❌ Forfait inconnu"

    UTILISATEURS[str(chat_id)] = {
        "forfait": forfait,
        "quota_restant": FORFAITS[forfait]["messages"]
    }
    with open(UTILISATEURS_PATH, "w", encoding="utf-8") as f:
        json.dump(UTILISATEURS, f, indent=2)

    send_message(chat_id, f"🎉 Ton forfait *{FORFAITS[forfait]['nom']}* a été activé !")
    return "✅ Forfait activé"

# 🎧 Vocal IA
@app.route('/send-audio/<chat_id>', methods=['GET'])
def send_audio(chat_id):
    utilisateur = UTILISATEURS.get(str(chat_id))
    if not utilisateur or utilisateur.get("quota_restant", 0) <= 0:
        send_message(chat_id, "⚠️ Tu n’as plus de messages disponibles.")
        return "Quota épuisé"

    texte = "Bonjour, je suis Miss AfrikyIA, ta coach business. Ensemble, sortons de la survie."
    filename = f"audio_{chat_id}.mp3"
    tts = gTTS(texte, lang="fr")
    tts.save(filename)
    with open(filename, 'rb') as audio:
        files = {'voice': audio}
        data = {'chat_id': chat_id}
        requests.post(f"{TELEGRAM_API_URL}/sendVoice", files=files, data=data)
    os.remove(filename)

    utilisateur["quota_restant"] -= 1
    with open(UTILISATEURS_PATH, "w", encoding="utf-8") as f:
        json.dump(UTILISATEURS, f, indent=2)

    return f"✅ Audio envoyé à {chat_id}"

# 📡 Webhook
@app.route("/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "Webhook prêt ✅"

    data = request.json
    chat_id = data.get("message", {}).get("chat", {}).get("id") or data.get("callback_query", {}).get("from", {}).get("id")
    if not chat_id:
        return "❌ Pas de chat_id"

    utilisateur = UTILISATEURS.get(str(chat_id))
    if "message" in data:
        text = data["message"].get("text", "")

        # Blocage si quota épuisé
        if utilisateur and utilisateur.get("quota_restant", 0) <= 0:
            send_message(chat_id, "⚠️ Ton quota est épuisé. Merci d’activer un nouveau forfait.")
            return "blocked"

        if text == "/start":
            show_main_menu(chat_id)
            return "menu"

        response = nkouma.repondre(text)

        if utilisateur:
            utilisateur["quota_restant"] -= 1
            with open(UTILISATEURS_PATH, "w", encoding="utf-8") as f:
                json.dump(UTILISATEURS, f, indent=2)
            response += f"\n\n🧮 Il te reste *{utilisateur['quota_restant']} messages*."

        send_message(chat_id, response)
        return "ok"

    if "callback_query" in data:
        callback = data["callback_query"]
        data_cb = callback["data"]

        if data_cb.startswith("p_"):
            domaine = data_cb.split("_")[1]
            show_submenu(chat_id, domaine)
        elif data_cb.startswith("s_"):
            pole = data_cb.split("_")[1]
            show_forfaits(chat_id, pole)
        elif data_cb.startswith("infos_"):
            key = data_cb.replace("infos_", "")
            show_inline_info(chat_id, key)
        elif data_cb.startswith("activate_"):
            forfait_key = data_cb.replace("activate_", "")
            return activate_forfait_from_callback(chat_id, forfait_key)
        return "callback handled"

    return "ok"

def activate_forfait_from_callback(chat_id, forfait_key):
    if forfait_key not in FORFAITS:
        send_message(chat_id, "❌ Forfait inconnu.")
        return "nok"
    UTILISATEURS[str(chat_id)] = {
        "forfait": forfait_key,
        "quota_restant": FORFAITS[forfait_key]["messages"]
    }
    with open(UTILISATEURS_PATH, "w", encoding="utf-8") as f:
        json.dump(UTILISATEURS, f, indent=2)
    send_message(chat_id, f"🎉 Ton forfait *{FORFAITS[forfait_key]['nom']}* a été activé !")
    return "ok"

@app.route('/simulate', methods=['GET'])
def simulate():
    r1 = sheteachia.repondre("Comment transmettre l'amour d'apprendre ?")
    r2 = miss.repondre("Peut-on monétiser une pédagogie ?")
    return f"✅ Simu:\n{r1}\n\n{r2}"

@app.route('/check-ethique', methods=['GET'])
def check_ethique():
    message = request.args.get("message", "")
    return {"analyse": nkouma.repondre(message)}
