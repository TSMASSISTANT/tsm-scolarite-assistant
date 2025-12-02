from flask import Flask, request, jsonify, render_template_string
import groq
from datetime import datetime
import os

app = Flask(__name__)

# Configuration (remplace par ta clé Groq)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
client = groq.Groq(api_key=GROQ_API_KEY)

# Documents TSM (à personnaliser avec les vraies infos)
DOCUMENTS_TSM = """
=== INFORMATIONS OFFICIELLES TSM (année 2025-2026) ===
DATES CLÉS :
- Candidatures L1/L2/L3 : via Parcoursup → 15 janvier au 13 mars 2025
- Candidatures Master : via MonMaster → 24 février au 24 mars 2025
- Inscriptions administratives : 1er au 15 septembre 2025 sur ENT
- Examens session 1 : décembre 2025 & mai-juin 2026
- Rattrapages : fin août 2026
CONTACTS : scolarite@tsm-education.fr | contact@tsm-education.fr
(Ajoute ici tous tes docs officiels !)
"""

SYSTEM_PROMPT = f"""
Tu es l'assistant virtuel du service scolarité de Toulouse School of Management (TSM).
Ton ton est professionnel mais chaleureux, tu tutoies l'utilisateur.

RÈGLES ABSOLUES :
- Réponds UNIQUEMENT avec les infos des documents ci-dessous.
- N'invente JAMAIS d'info (dates, procédures, etc.).
- Pour les admissions : "L'admission est décidée par la commission pédagogique, je ne peux pas préjuger de la décision."
- Cas complexe : "Je dois vérifier ça avec l'équipe scolarité. Peux-tu m'envoyer un mail à contact@tsm-education.fr avec ton nom et ton numéro étudiant ? Je transmets tout de suite 😊"
- Pour les agents admin : Propose des astuces pour agendas, mails types, outils (Google Workspace, Notion, etc.).

Infos disponibles : {DOCUMENTS_TSM}
"""

# Mémoire simple (par session)
conversation_history = {}

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)  # On charge l'interface chat

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    user_id = data.get("user_id", "anonyme")

    if user_id not in conversation_history:
        conversation_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    conversation_history[user_id].append({"role": "user", "content": message})

    chat_completion = client.chat.completions.create(
        messages=conversation_history[user_id][-10:],  # Limite pour éviter les tokens
        model="llama-3.2-3b-fast",  # Modèle gratuit et rapide
        temperature=0.6,
        max_tokens=500
    )

    reply = chat_completion.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": reply})

    return jsonify({"reply": reply})

# Template HTML inline pour l'interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Assistant Scolarité TSM</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial; max-width: 800px; margin: 40px auto; padding: 20px; background: #f8f9fa; }
        .chat { border: 1px solid #003366; border-radius: 15px; padding: 20px; background: white; height: 70vh; overflow-y: scroll; }
        .message { margin: 10px 0; padding: 12px; border-radius: 15px; }
        .user { background: #003366; color: white; text-align: right; margin-left: 100px; }
        .bot { background: #e9ecef; margin-right: 100px; }
        input { width: 100%; padding: 15px; font-size: 16px; border-radius: 10px; border: 1px solid #003366; }
        h1 { color: #003366; }
    </style>
</head>
<body>
    <h1>Bienvenue à la scolarité TSM 👋</h1>
    <div class="chat" id="chat"></div>
    <br>
    <input type="text" id="input" placeholder="Pose ta question (candidatures, examens, inscriptions…)" autofocus>
    
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        
        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = text;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        input.addEventListener('keypress', async (e) => {
            if (e.key === 'Enter' && input.value.trim()) {
                addMessage(input.value, 'user');
                const resp = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: input.value, user_id: 'etudiant_' + Date.now()})
                });
                const data = await resp.json();
                addMessage(data.reply, 'bot');
                input.value = '';
            }
        });
        
        addMessage("Salut ! Je suis l’assistant scolarité de Toulouse School of Management. Comment puis-je t’aider aujourd’hui ? 😊", "bot");
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
