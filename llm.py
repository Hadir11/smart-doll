import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.environ["LLM_MODEL"]
_client = None

LEVELS = {1: "très facile", 2: "moyen", 3: "un peu difficile"}

SYSTEM = """Tu es une poupée éducative gentille et joyeuse qui parle en français à un enfant.
Tu fais des phrases COURTES et simples (maximum 2 phrases), adaptées à son âge.
Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte autour, avec ces clés :
- "is_correct": true ou false si l'enfant répond à une question posée, sinon null
- "feedback": ta réaction à sa réponse (félicitation ou encouragement avec la bonne réponse). Si pas de question posée : une courte salutation.
- "next_question": UNE nouvelle question sur le thème, différente des précédentes."""


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ["LLM_BASE_URL"])
    return _client


def _parse(text):
    text = (text or "").strip()
    a, b = text.find("{"), text.rfind("}")
    if a != -1 and b > a:
        try:
            return json.loads(text[a:b + 1])
        except json.JSONDecodeError:
            pass
    return None


def teach_turn(topic, level, age, history, last_question, child_text):
    past = " | ".join(m["content"] for m in history[-8:] if m["role"] == "assistant")
    context = (f"Thème : {topic['title']} ({topic.get('subject') or ''}). "
               f"Contenu : {topic.get('content') or ''}\n"
               f"Âge de l'enfant : {age} ans. Difficulté : {LEVELS.get(level, 'facile')}.\n"
               f"Ce que tu as déjà dit : {past or 'rien'}\n")
    if last_question:
        user = (context + f'Tu avais demandé : "{last_question}"\n'
                f'L\'enfant répond : "{child_text}"\n'
                "Évalue sa réponse puis pose une nouvelle question.")
    else:
        user = context + "Commence la leçon : salue l'enfant et pose la première question."

    for _ in range(2):
        r = _get_client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            max_tokens=800,
            extra_body={"reasoning_effort": "low"},
        )
        data = _parse(r.choices[0].message.content)
        if data:
            if not last_question:
                data["is_correct"] = None
            return data
    return {"is_correct": None, "feedback": "Oups, je n'ai pas bien compris.",
            "next_question": last_question or "Combien font 2 plus 2 ?"}