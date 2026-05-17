"""Sender Agent — invia email via Resend con timing intelligente e tracking GDPR."""

import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import resend
from adh.agents.state import AgentState
from adh.config.settings import settings

resend.api_key = settings.resend_api_key
ITALY_TZ = ZoneInfo("Europe/Rome")


def _is_within_sending_window() -> bool:
    """Verifica che l'ora corrente sia nella finestra 9:00-18:00 lun-gio."""
    now = datetime.now(ITALY_TZ)
    if now.weekday() >= 4:  # Venerdì (4) = non inviare
        return False
    return 9 <= now.hour < 18


def _random_delay_seconds() -> int:
    """Ritardo casuale per simulare comportamento umano (30s-5min)."""
    return random.randint(30, 300)


def _build_email_body_html(body: str, company_name: str) -> str:
    """Converte il testo plain in HTML minimale con tracking privacy-aware."""
    paragraphs = body.split("\n\n")
    html_paragraphs = "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)
    return f"""<!DOCTYPE html>
<html lang="it">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; font-size: 15px; color: #222; max-width: 600px;">
{html_paragraphs}
<hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
<p style="font-size: 12px; color: #999;">
Hai ricevuto questa email perché il tuo contatto è disponibile pubblicamente.
Se preferisci non ricevere ulteriori email da parte mia, rispondi con STOP e ti rimuoverò immediatamente.
</p>
</body>
</html>"""


def sender_node(state: AgentState) -> AgentState:
    """Nodo LangGraph: invia l'email via Resend (solo se approval_status == 'approved')."""
    if settings.kill_switch:
        return state.model_copy(
            update={"status": "stopped", "error": "Kill switch attivo — invio bloccato"}
        )

    if state.approval_status != "approved":
        return state.model_copy(
            update={"status": "waiting_approval", "current_step": "approval_gate"}
        )

    message = state.message
    company = state.company

    if not message or not company:
        return state.model_copy(update={"status": "error", "error": "Message o Company mancanti nel Sender"})

    recipient_email = (
        company.decision_maker_email or company.email
    )
    if not recipient_email:
        return state.model_copy(
            update={"status": "error", "error": f"Nessuna email per {company.name}"}
        )

    html_body = _build_email_body_html(message.body, company.name)

    try:
        result = resend.Emails.send({
            "from": f"{settings.outreach_from_name} <{settings.outreach_from_email}>",
            "to": [recipient_email],
            "subject": message.subject,
            "html": html_body,
            "text": message.body,
            "reply_to": settings.outreach_from_email,
            "headers": {
                "X-Campaign-ID": state.run_id or "manual",
                "List-Unsubscribe": f"<mailto:{settings.outreach_from_email}?subject=STOP>",
            },
        })
        return state.model_copy(
            update={
                "status": "sent",
                "current_step": "sent",
            }
        )
    except Exception as e:
        return state.model_copy(
            update={"status": "error", "error": f"Errore invio Resend: {str(e)}"}
        )
