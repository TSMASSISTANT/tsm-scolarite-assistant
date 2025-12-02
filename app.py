from flask import Flask, request, jsonify, render_template_string
import os
import groq
from pathlib import Path

# ======== CONFIGURATION ========
app = Flask(__name__)
client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ======== CHARGEMENT AUTOMATIQUE DE TOUS LES PDF DU DOSSIER "documents" ========
def extract_text_from_pdfs():
    text = "\n=== CONTENU DES DOCUMENTS OFFICIELS TSM (extrait automatiquement des PDF) ===\n\n"
    pdf_folder = Path("documents")
    
    if not pdf_folder.exists():
        return "Aucun document chargé (dossier 'documents' manquant)."

    import fitz  # PyMuPDF
    for pdf_file in pdf_folder.glob("*.pdf"):
        try:
            doc = fitz.open(pdf_file)
            text += f"\n--- Document : {pdf_file.name} ---\n"
            for page in doc:
                text += page.get_text("text") + "\n"
            doc.close()
        except Exception as e:
            text += f"\nErreur lecture {pdf_file.name} : {e}\n"
    return text

DOCUMENTS_TSM = extract_text_from_pdfs()

# ======== PROMPT SYSTÈME (blindé avec toutes tes règles) ========
SYSTEM_PROMPT = f"""
Tu es l’assistant virtuel du service scolarité de Toulouse School of Management (TSM).
Ton ton est professionnel mais chaleureux, tu tutoies toujours l’utilisateur.

RÈGLES ABSOLUES ai à respecter à chaque réponse :
- Tu ne réponds QU’avec les informations présentes dans les documents ci-dessous.
- Tu n’inventes jamais une date, un tarif, une procédure, un délai.
- Pour toute question d’admission : « L’admission est décidée par la commission pédagogique, je ne peux pas préjuger de la décision. »
- Si tu n’es pas sûr·e à 100 % ou si c’est un cas particulier → réponds exactement :
  "Je dois vérifier ça avec l’équipe scolarité. Peux-tu m’envoyer un mail à contact@tsm-education.fr avec ton nom et ton numéro étudiant ? Je transmets tout de suite 😊"
- Tu peux aider les agents administratifs (plannings, modèles de mail, astuces outils).

Voici l’ensemble des informations officielles que tu as le droit d’utiliser :
{DOCUMENTS_TSM}
"""

# Mémoire des conversations (simple mais efficace)
conversations = {}

# ======== PAGE D’ACCUEIL + CHAT ========
HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>Assistant Scolarité TSM</title>
    <style>
        body {font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; background:#f5f7fa;}
        h1 {color:#003366; text-align:center;}
        .chat {border:2px solid #003366; border-radius:15px; padding:20px; background:white; height:65vh; overflow-y:scroll; margin-bottom:20px;}
        .msg {margin:15px 0; padding:12px 18px; border-radius:18px; max-width:80%;}
        .user {background:#003366; color:white; margin-left:auto;}
        .bot {background:#e9ecef; margin-right:auto;}
        input {width:100%; padding:15px; font-size:16px; border:2px solid #003366; border-radius:12px;}
    </style>
</head>
<body>
    <h1>Assistant Scolarité TSM</h1>
    <div class="chat" id="chat"></div>
    <input type="text" id="input" placeholder="Ta question (inscription, examen, calendrier…)" autofocus>

    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        function add(msg, type){ 
            const div = document.createElement('div'); 
            div.className='msg '+type; 
            div.textContent=msg; 
            chat.appendChild(div); 
            chat.scrollTop = chat.scrollHeight;
        }
        add("Salut ! Je suis l’assistant scolarité de Toulouse School of Management. Comment puis-je t’aider aujourd’hui ? 😊", "bot");

        input.addEventListener("keypress", async e => {
            if(e.key==="Enter" && input.value.trim()){
                add(input.value, "user");
                const resp = await fetch("/chat", {method:"POST", headers:{"Content-Type":"application/json"},
                    body:JSON.stringify({message:input.value})});
                const data = await resp.json();
                add(data.reply, "bot");
                input.value="";
            }
        });
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message", "")
    user_id = request.remote_addr  # ou tu peux mettre un cookie si tu veux

    if user_id not in conversations:
        conversations[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    conversations[user_id].append({"role": "user", "content": user_msg})

    # On garde les 12 derniers messages max pour ne pas exploser les tokens
    response = client.chat.completions.create(
        model="llama-3.2-3b-fast",      # ultra-rapide et gratuit sur Groq
        messages=conversations[user_id][-12:],
        temperature=0.5,
        max_tokens=700
    )

    reply = response.choices[0].message.content
    conversations[user_id].append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
