"""Reply Handler — 9 categorie, urgency, draft_response, GDPR-safe."""

import json
import re

import httpx
from anthropic import Anthropic

from adh.agents._utils import extract_text
from adh.agents.state import ReplyData, ReplyExtracted, load_prompt
from adh.config.settings import settings

client = Anthropic(api_key=settings.anthropic_api_key)
SYSTEM_PROMPT = load_prompt("reply_handler")

VALID_CATEGORIES = {
    "interested", "interested_later", "not_now", "not_interested",
    "unsubscribe", "out_of_office", "question", "wrong_person", "other",
}


def classify_reply(reply_body: str, original_subject: str = "") -> ReplyData:
    """Classifica la risposta con Claude Haiku e ritorna un ReplyData strutturato."""
    user_msg = f"""Original email subject: "{original_subject}"

Reply received:
---
{reply_body[:1500]}
---

Classify and produce the full JSON output as specified."""

    try:
        response = client.messages.create(
            model=settings.llm_cheap_model,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = extract_text(response)
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
    except Exception:
        # Fallback sicuro: ambiguità → unsubscribe (regola GDPR)
        return ReplyData(
            category="other",
            confidence=0.3,
            recommended_action="Classificazione fallita — revisione umana necessaria",
            urgency="medium",
        )

    category = data.get("category", "other")
    # Regola GDPR: ambiguità unsubscribe/not_interested → unsubscribe
    if category not in VALID_CATEGORIES:
        category = "other"

    extracted_raw = data.get("extracted", {})
    extracted = ReplyExtracted(
        redirected_to=extracted_raw.get("redirected_to"),
        follow_up_date=extracted_raw.get("follow_up_date"),
        question=extracted_raw.get("question"),
        objection=extracted_raw.get("objection"),
        meeting_proposal=extracted_raw.get("meeting_proposal"),
    )

    return ReplyData(
        category=category,
        confidence=float(data.get("confidence", 0.7)),
        extracted=extracted,
        recommended_action=data.get("recommended_action", ""),
        draft_response=data.get("draft_response"),
        urgency=data.get("urgency", "low"),
    )


async def notify_telegram(message: str) -> None:
    """Notifica Telegram per lead interessati (urgency=high)."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            await c.post(url, json={
                "chat_id": settings.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
            })
    except Exception:
        pass
