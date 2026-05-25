"""FastAPI webhook endpoint per gestire le reply di Resend."""

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Request
from sqlmodel import Session, select

from adh.agents.reply_handler import classify_reply, notify_telegram
from adh.config.settings import settings
from adh.models.company import Company, CompanyStatus
from adh.models.database import engine
from adh.models.message import MessageStatus, OutreachMessage, ProcessingLog, ReplyIntent

app = FastAPI(title="ADH Webhook", docs_url=None, redoc_url=None)


@app.post("/webhook/resend")
async def handle_resend_webhook(request: Request):
    """Riceve eventi di Resend: email aperta, cliccata, risposta ricevuta."""
    data = await request.json()
    event_type = data.get("type", "")
    with Session(engine) as session:
        # Resend usa "message_id" nel campo data (non "email_id")
        resend_id = (
            data.get("data", {}).get("message_id")
            or data.get("data", {}).get("email_id")
            or ""
        )
        if not resend_id:
            return {"status": "ignored", "reason": "no message_id in payload"}

        message = session.exec(
            select(OutreachMessage).where(OutreachMessage.resend_message_id == resend_id)
        ).first()
        if not message:
            return {"status": "ignored", "reason": "message not found"}

        if event_type == "email.opened":
            message.status = MessageStatus.opened
            message.opened_at = datetime.now(UTC)
            session.add(message)
        elif event_type == "email.clicked":
            message.status = MessageStatus.clicked
            message.clicked_at = datetime.now(UTC)
            session.add(message)
        elif event_type == "email.replied":
            reply_body = data.get("data", {}).get("text", "")
            await _handle_reply(session, message, reply_body)

        session.commit()
    return {"status": "ok"}

async def _handle_reply(session: Session, message: OutreachMessage, reply_body: str):
    """Classifica la risposta e aggiorna DB + notifiche."""
    reply_data = classify_reply(reply_body)
    try:
        intent = ReplyIntent(reply_data.category)
    except ValueError:
        # Categoria sconosciuta dal classifier — fallback prudente
        intent = ReplyIntent.other

    message.reply_received_at = datetime.now(UTC)
    message.reply_intent = intent
    message.reply_body = reply_body[:2000]
    message.status = MessageStatus.replied

    company = session.get(Company, message.company_id)
    if not company:
        return

    if intent == ReplyIntent.unsubscribe:
        company.status = CompanyStatus.blacklisted
        company.blacklisted_until = None  # permanente
        log = ProcessingLog(
            company_id=company.id,
            action="unsubscribe_permanent",
            data_processed=["email"],
            notes="Richiesta STOP ricevuta — rimosso permanentemente",
        )
        session.add(log)

    elif intent == ReplyIntent.not_interested:
        company.status = CompanyStatus.not_interested
        company.blacklisted_until = datetime.now(UTC) + timedelta(days=365)

    elif intent == ReplyIntent.interested:
        company.status = CompanyStatus.replied
        notify_msg = (
            f"🔥 *Lead caldo!*\n\n"
            f"Azienda: *{company.name}* ({company.sector})\n"
            f"Risposta: {reply_body[:300]}\n\n"
            f"→ Agisci manualmente sul CRM"
        )
        await notify_telegram(notify_msg)

    elif intent == ReplyIntent.question:
        # Genera bozza risposta per approval umano
        original_message = session.get(OutreachMessage, message.id)
        if original_message:
            draft = reply_data.draft_response or ""
            message.reply_draft = draft

    elif intent == ReplyIntent.out_of_office:
        pass  # follow-up gestito dallo scheduler

    elif intent == ReplyIntent.not_now:
        pass  # follow-up tra 60 giorni gestito dallo scheduler

    company.updated_at = datetime.now(UTC)
    session.add(company)
    session.add(message)


@app.get("/health")
async def health():
    return {"status": "ok", "kill_switch": settings.kill_switch}
