from flask import Flask, request
import openai
import os
import requests
import json

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
openai.api_key = OPENAI_API_KEY

user_sessions = {}
violation_counts = {}

LANGUES = ["Français", "Anglais", "Swahili", "Lingala", "Wolof", "Arabe", "Portugais"]
TONS = {
    "gentille": "😊 Gentille", "strategique": "📊 Stratégique",
    "zen": "🧘 Zen", "motivation": "🔥 Motivation"
}
POLES = [
    "🧠 Éducation", "💼 Business", "🧘 Bien-être", "❤️ Maternité", "👵 SeniorCare",
    "🧒 Enfant", "📖 Foi", "❤️ Amour", "💊 Santé"
]
FORFAITS = {
    "essentiel": "💡 Essentiel – 1000 FCFA",
    "premium": "🚀 Premium – 2500 FCFA",
    "vip": "👑 VIP – 5000 FCFA"
}

# 🔐 Nkouma : filtre moral
def nkouma_guard(text, chat_id):
    interdits = ["viol", "suicide", "pédoporno", "tuer", "esclavage", "arme", "insulte", "porno"]
    if any(m in text.lower() for m in interdits):
        violation_counts[chat_id] = violation_counts.get(chat_id, 0) + 1
        if violation_counts[chat_id] >= 3:
            send_text(chat_id, "🚨 Tu as dépassé les limites autorisées. Ce comportement sera signalé.")
        else:
            send_text(chat_id, "⛔ Contenu bloqué par la cellule éthique Nkouma.")
        return False
    return True

def send_text(chat_id, message):
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": message
    })

def send_inline_menu(chat_id, question, options, prefix):
    buttons = [[{"text": opt, "callback_data": f"{prefix}:{opt}"}] for opt in options]
    reply_markup = {"inline_keyboard": buttons}
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": question,
        "reply_markup": reply_markup
    })

def generate_ani_intro(session):
    instruction = (
        f"Tu es une ANI {session.get('tone', 'gentille')} dédiée à {session.get('profil', 'quelqu’un')}, "
        f"attachée au pôle {session.get('pole', 'général')}. "
        "Tu es encadrée par Nkouma, cellule souche éthique. "
        "Tu ne dois jamais produire de contenu illégal, immoral, haineux ou explicite. "
        f"Parle en {session.get('langue', 'Français')} avec douceur."
    )
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": "Génère un message d'accueil personnalisé."}
        ]
    )
    return completion["choices"][0]["message"]["content"]

@app.route('/webhook', methods=["POST"])
def webhook():
    data = request.json
    message = data.get("message")
    callback = data.get("callback_query")

    if message:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        if text == "/start":
            user_sessions[chat_id] = {}
            send_inline_menu(chat_id, "🌍 Choisis ta langue :", LANGUES, "lang")
        elif chat_id in user_sessions and "profil" not in user_sessions[chat_id]:
            if nkouma_guard(text, chat_id):
                user_sessions[chat_id]["profil"] = text
                send_inline_menu(chat_id, "🧭 Choisis un pôle :", POLES, "pole")

    elif callback:
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        data = callback["data"]
        key, value = data.split(":")

        session = user_sessions.setdefault(chat_id, {})
        session[key] = value

        if key == "lang":
            send_inline_menu(chat_id, "🎭 Choisis un ton :", list(TONS.values()), "tone")
        elif key == "tone":
            send_text(chat_id, "✍️ Décris à qui est destinée ton ANI (ex : mon fils autiste, une maman débordée...)")
        elif key == "pole":
            send_inline_menu(chat_id, "💰 Choisis ton forfait :", list(FORFAITS.values()), "forfait")
        elif key == "forfait":
            message_ani = generate_ani_intro(session)
            send_text(chat_id, "🎉 ANI générée avec succès !")
            send_text(chat_id, f"👋 Message d'accueil :\n\n{message_ani}")

    return "OK"
