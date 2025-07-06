# ✅ SCRIPT COMPLET – ANI Creator Bot avec Pôles, GPT, Éthique (Nkouma), Profil & Forfaits

from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import openai
import json
import os

app = Flask(__name__)

# 🔐 Clés API
BOT_TOKEN = "TON_TELEGRAM_BOT_TOKEN"
OPENAI_API_KEY = "TON_OPENAI_KEY"
bot = telebot.TeleBot(BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

user_sessions = {}

# 📌 Données de base
LANGUES = ["Français", "Anglais", "Swahili", "Lingala", "Wolof", "Arabe", "Portugais"]

TONS = {
    "gentille": "😊 Gentille",
    "strategique": "📊 Stratégique",
    "zen": "🧘 Zen",
    "motivation": "🔥 Motivation"
}

FORFAITS = {
    "essentiel": "💡 Essentiel – 1000 FCFA",
    "premium": "🚀 Premium – 2500 FCFA",
    "vip": "👑 VIP – 5000 FCFA"
}

POLES = [
    "🧠 Éducation",
    "💼 Business",
    "🧘 Bien-être",
    "❤️ Maternité",
    "👵 SeniorCare",
    "🧒 Enfant",
    "🛡️ Éthique",
    "📖 Foi/Spiritualité",
    "❤️ Amour",
    "💊 Santé"
]

# 🔐 Nkouma – Filtre éthique

def nkouma_guard(user_input, parental=False):
    interdits_base = ["viol", "suicide", "pédoporno", "tuer", "arme", "esclavage"]
    interdits_parental = ["sexe", "nudité", "mort", "insulte", "démon", "diable", "sang"]
    mots = interdits_base + (interdits_parental if parental else [])
    return not any(mot in user_input.lower() for mot in mots)

# 🎤 GPT : Génération du message d’accueil

def generer_message_bienvenue(session):
    langue = session.get("langue", "Français")
    tone = session.get("tone", "gentille")
    profil = session.get("profil", "quelqu’un")
    pole = session.get("pole", "général")
    parental = session.get("parental", False)
    senior = session.get("senior", False)

    instruction = f"Tu es une IA {tone} pour {profil}. Pôle : {pole}. "
    if parental:
        instruction += "Ton langage est adapté à un environnement protégé. "
    if senior:
        instruction += "Tu parles lentement et clairement, avec des mots simples. "
    instruction += f"Réponds en {langue.lower()} avec douceur."

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": "Génère un message d'accueil."}
        ]
    )
    return completion['choices'][0]['message']['content']

# 🧱 Route Webhook
@app.route('/webhook', methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# ▶️ /start
@bot.message_handler(commands=['start'])
def start(message):
    user_sessions[message.chat.id] = {}
    markup = InlineKeyboardMarkup()
    for lang in LANGUES:
        markup.add(InlineKeyboardButton(lang, callback_data=f"lang:{lang}"))
    bot.send_message(message.chat.id, "🌍 Choisis la langue :", reply_markup=markup)

# ▶️ Langue → Ton
@bot.callback_query_handler(func=lambda call: call.data.startswith("lang:"))
def select_lang(call):
    lang = call.data.split(":")[1]
    user_sessions[call.message.chat.id]["langue"] = lang

    markup = InlineKeyboardMarkup()
    for code, label in TONS.items():
        markup.add(InlineKeyboardButton(label, callback_data=f"tone:{code}"))
    bot.edit_message_text("🎭 Choisis le ton de ton ANI :", call.message.chat.id, call.message.message_id, reply_markup=markup)

# ▶️ Ton → Modes
@bot.callback_query_handler(func=lambda call: call.data.startswith("tone:"))
def select_tone(call):
    tone = call.data.split(":")[1]
    user_sessions[call.message.chat.id]["tone"] = tone

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("👶 Mode parental ❌", callback_data="mode:parental"),
        InlineKeyboardButton("🧓 Mode senior ❌", callback_data="mode:senior")
    )
    markup.add(InlineKeyboardButton("⏭️ Continuer", callback_data="profil"))
    bot.edit_message_text("🔧 Activer un mode spécial ?", call.message.chat.id, call.message.message_id, reply_markup=markup)

# ▶️ Toggle Mode
@bot.callback_query_handler(func=lambda call: call.data.startswith("mode:"))
def toggle_mode(call):
    mode = call.data.split(":")[1]
    session = user_sessions[call.message.chat.id]
    session[mode] = not session.get(mode, False)

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(f"👶 Mode parental {'✅' if session.get('parental') else '❌'}", callback_data="mode:parental"),
        InlineKeyboardButton(f"🧓 Mode senior {'✅' if session.get('senior') else '❌'}", callback_data="mode:senior")
    )
    markup.add(InlineKeyboardButton("⏭️ Continuer", callback_data="profil"))
    bot.edit_message_text("🔧 Mode ajusté. Clique sur ⏭️ pour continuer.", call.message.chat.id, call.message.message_id, reply_markup=markup)

# ▶️ Description Profil
@bot.callback_query_handler(func=lambda call: call.data == "profil")
def ask_profil(call):
    bot.send_message(call.message.chat.id, "✍️ Décris à qui est destinée cette ANI :")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_profil)

def save_profil(message):
    if not nkouma_guard(message.text):
        bot.send_message(message.chat.id, "🚫 Contenu inapproprié bloqué par Nkouma.")
        return

    user_sessions[message.chat.id]["profil"] = message.text
    markup = InlineKeyboardMarkup()
    for pole in POLES:
        markup.add(InlineKeyboardButton(pole, callback_data=f"pole:{pole}"))
    bot.send_message(message.chat.id, "🔍 Choisis le **pôle** de ton ANI :", reply_markup=markup)

# ▶️ Sauver Pôle → Forfait
@bot.callback_query_handler(func=lambda call: call.data.startswith("pole:"))
def save_pole(call):
    pole = call.data.split(":")[1]
    user_sessions[call.message.chat.id]["pole"] = pole

    markup = InlineKeyboardMarkup()
    for key, label in FORFAITS.items():
        markup.add(InlineKeyboardButton(label, callback_data=f"forfait:{key}"))
    bot.send_message(call.message.chat.id, f"✅ Pôle sélectionné : {pole}\n\n💰 Choisis un forfait :", reply_markup=markup)

# ▶️ Forfait → Générer l’ANI
@bot.callback_query_handler(func=lambda call: call.data.startswith("forfait:"))
def finalise_ani(call):
    forfait = call.data.split(":")[1]
    session = user_sessions[call.message.chat.id]
    session["forfait"] = forfait

    bot.send_message(call.message.chat.id, "✨ Création de ton ANI...")
    message_bienvenue = generer_message_bienvenue(session)

    bot.send_message(call.message.chat.id, "✅ ANI créée avec succès !")
    bot.send_message(call.message.chat.id, f"```json\n{json.dumps(session, indent=2, ensure_ascii=False)}\n```", parse_mode="Markdown")
    bot.send_message(call.message.chat.id, f"👋 Message d'accueil :\n\n{message_bienvenue}")
