from langdetect import detect
from dotenv import load_dotenv
load_dotenv()
import os, json, requests
from flask import Flask, request, jsonify
from openai import OpenAI
from gtts import gTTS
from datetime import datetime

app = Flask(name)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

FORFAITS = {
"essentiel": {"nom": "Essentiel", "prix": "1000", "duree": 1, "contenu": "10 messages écrits ou vocaux"},
"premium": {"nom": "Premium", "prix": "5000", "duree": 3, "contenu": "60 messages écrits / vocaux"},
"vip": {"nom": "VIP", "prix": "10000", "duree": 15, "contenu": "150 messages écrits / vocaux"}
}

SESSIONS = {}

 Classe IA

class NoeudCognitif:
def init(self, nom, role):
self.nom = nom
self.role = role

def repondre(self, prompt):
    try:
        lang = detect(prompt)
        if lang == "fr":
            prefix = ""
        elif lang == "ln":
            prefix = "Réponds en lingala : "
        elif lang == "en":
            prefix = "Answer in English: "
        else:
            prefix = ""
        
        full_prompt = f"{prefix}{prompt}"

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": full_prompt}
            ]
        )
        return completion.choices[0].message.content.strip()
    except:
        return "🤖 [GPT indisponible]"

  Noeuds IA

miss = NoeudCognitif("Miss AfrikyIA", "Coach business pour femmes africaines.")
sheteachia = NoeudCognitif("SheTeachIA", "Mentor éducatif qui aide aux devoirs et à l’apprentissage.")
shelove = NoeudCognitif("SheLoveIA", "Love coach pour bâtir une vie sentimentale saine.")
nkouma = NoeudCognitif("Nkouma", "Modératrice éthique. Répond toujours avec bienveillance.")

Sessions en mémoire

def activer_forfait(chat_id, forfait_id):
infos = FORFAITS.get(forfait_id)
if not infos:
return False
SESSIONS[chat_id] = {
"forfait": forfait_id,
"expires": datetime.now().timestamp() + infos["duree"] * 86400,
"noeud": None
}
return True

def est_valide(chat_id):
session = SESSIONS.get(chat_id)
if not session:
return False
return datetime.now().timestamp() < session["expires"]

def set_noeud(chat_id, choix):
if chat_id not in SESSIONS:
return
if choix == "business":
SESSIONS[chat_id]["noeud"] = miss
elif choix == "education":
SESSIONS[chat_id]["noeud"] = sheteachia
elif choix == "love":
SESSIONS[chat_id]["noeud"] = shelove

def get_noeud(chat_id):
return SESSIONS.get(chat_id, {}).get("noeud", None)

💬 Telegram

def send_message(chat_id, text, reply_markup=None):
payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
if reply_markup:
payload["reply_markup"] = json.dumps(reply_markup)
requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def show_forfaits(chat_id):
buttons = [
[{"text": "🎟️ Essentiel – 1000 FCFA", "callback_data": "f_essentiel"}],
[{"text": "🎟️ Premium – 5000 FCFA", "callback_data": "f_premium"}],
[{"text": "🎟️ VIP – 10000 FCFA", "callback_data": "f_vip"}],
]
send_message(chat_id, "Choisis ton forfait IA :", {"inline_keyboard": buttons})

def show_infos(chat_id, fkey):
infos = FORFAITS[fkey]
msg = (
f"{infos['nom']}\n"
f"⏳ Durée : {infos['duree']} jour(s)\n"
f"📦 {infos['contenu']}\n\n"
f"📲 Paiement par Airtel : +242 057538060"
)
buttons = [[{"text": "✅ J’ai payé", "callback_data": f"paid_{fkey}"}]]
send_message(chat_id, msg, {"inline_keyboard": buttons})

def show_poles(chat_id):
buttons = [
[{"text": "📈 Business", "callback_data": "p_business"}],
[{"text": "📚 Éducation", "callback_data": "p_education"}],
[{"text": "💖 Love Plan", "callback_data": "p_love"}],
]
send_message(chat_id, "📍 Quel pôle IA souhaites-tu explorer ?", {"inline_keyboard": buttons})

🌐 Webhook

@app.route("/webhook", methods=["POST", "GET"])
def webhook():
if request.method == "GET":
return "✅ Webhook actif"

data = request.json  
chat_id = data.get("message", {}).get("chat", {}).get("id") or data.get("callback_query", {}).get("from", {}).get("id")  

if "message" in data:  
    txt = data["message"].get("text", "")  
    if txt == "/start":  
        show_forfaits(chat_id)  
    elif est_valide(chat_id):  
        node = get_noeud(chat_id)  
        if node:  
            answer = node.repondre(txt)  
            send_message(chat_id, answer)  
        else:  
            send_message(chat_id, "❗ Merci de choisir un pôle IA.")  
            show_poles(chat_id)  
    else:  
        send_message(chat_id, "⛔ Forfait expiré ou non activé. Tape /start.")  

elif "callback_query" in data:  
    data_cb = data["callback_query"]["data"]  
    if data_cb.startswith("f_"):  
        show_infos(chat_id, data_cb.replace("f_", ""))  
    elif data_cb.startswith("paid_"):  
        key = data_cb.replace("paid_", "")  
        if activer_forfait(chat_id, key):  
            send_message(chat_id, f"✅ Paiement confirmé ! Tu es connectée à *{key.title()}* pour {FORFAITS[key]['duree']} jour(s).")  
            show_poles(chat_id)  
    elif data_cb.startswith("p_"):  
        domaine = data_cb.replace("p_", "")  
        set_noeud(chat_id, domaine)  
        send_message(chat_id, f"🎯 Super choix. {domaine.title()} est activé. Pose ta première question ✨")  

return "ok"

🧪 simulate

@app.route("/simulate", methods=["GET"])
def simulate():
r1 = sheteachia.repondre("Comment transmettre l'amour d'apprendre ?")
r2 = miss.repondre("Peut-on monétiser une pédagogie ?")
return "✅ Simulation IA ok"

✅ check-ethique

@app.route("/check-ethique", methods=["GET"])
def check_ethique():
message = request.args.get("message", "")
return {"analyse": nkouma.repondre(message)}

