elif session.get("étape") == "conversation":
        nom = session.get("nom", "ton ANI")
        langue = session.get("langue", "Français")
        tone = session.get("tone", "bienvaillante")
        profil = session.get("profil", "une personne")
        pole = session.get("pole", "général")
        parental = session.get("parental", False)
        senior = session.get("senior", False)

        instruction = f"Tu es une IA {tone}, nommée {nom}, pour {profil}. Pôle : {pole}. "
        if parental:
            instruction += "Langage protégé. "
        if senior:
            instruction += "Parle lentement, avec des mots simples. "
        instruction += f"Réponds uniquement en {langue.lower()}. "
        instruction += "Tu peux aussi répondre en vocal grâce à une synthèse vocale."

        try:
            completion = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": text}
                ]
            )
            reponse = completion.choices[0].message.content.strip()
            send_message(chat_id, reponse)
            envoyer_vocal(chat_id, reponse)
        except Exception as e:
            send_message(chat_id, f"❌ Une erreur est survenue : {str(e)}")
