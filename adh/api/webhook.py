"""FastAPI webhook endpoint per gestire le reply di Resend."""

import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from sqlmodel import Session, select

from adh.agents.reply_handler import classify_reply, generate_reply_draft, notify_telegram
from adh.models.company import Company, CompanyStatus
from adh.models.message import OutreachMessage, MessageStatus, ReplyIntent, ProcessingLog
from adh.models.database import engine
from adh.config.settings import settings

app = FastAPI(title="ADH Webhook", docs_url=None, redoc_url=None)


@app.post("/webhook/resend")
async def handle_resend_webhook(request: Request):
    """Riceve eventi di Resend: email aperta, cliccata, risposta ricevuta."""
    data = await request.json()
    event_type = data.get("type", "")

    with Session(engine) as session:
        # Trova il messaggio via resend_message_id
        resend_id = data.get("data", {}).get("email_id", "")
        message = session.exec(
            select(OutreachMessage).where(OutreachMessage.resend_message_id == resend_id)
        ).first()

        if not message:
            return {"status": "ignored", "reason": "message not found"}

        if event_type == "email.opened":
            message.status = MessageStatus.opened
            message.opened_at = datetime.utcnow()
            session.add(message)

        elif event_type == "email.clicked":
            message.status = MessageStatus.clicked
            message.clicked_at = datetime.utcnow()
            session.add(message)

        elif event_type == "email.replied":
            reply_body = data.get("data", {}).get("text", "")
            await _handle_reply(session, message, reply_body)

        session.commit()

    return {"status": "ok"}


async def _handle_reply(session: Session, message: OutreachMessage, reply_body: str):
    """Classifica la risposta e aggiorna DB + notifiche."""
    intent = classify_reply(reply_body)
    message.reply_received_at = datetime.utcnow()
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
        company.blacklisted_until = datetime.utcnow() + timedelta(days=365)

    elif intent == ReplyIntent.interested:
        company.status = CompanyStatus.replied
        notify_msg = (
            f"🔥 *Lead caldo!*\n\n"
            f"Azienda: *{company.name}* ({company.sector})\n"
            f"Risposta: {reply_body[:300]}\n\n"
            f"→ Agisci manualmente sul CRM"
        )
        asyncio.create_task(notify_telegram(notify_msg))

    elif intent == ReplyIntent.question:
        # Genera bozza risposta per approval umano
        original_message = session.get(OutreachMessage, message.id)
        if original_message:
            draft = generate_reply_draft(original_message.body, reply_body, company.name)
            message.reply_draft = draft

    elif intent == ReplyIntent.out_of_office:
        pass  # follow-up gestito dallo scheduler

    elif intent == ReplyIntent.not_now:
        pass  # follow-up tra 60 giorni gestito dallo scheduler

    company.updated_at = datetime.utcnow()
    session.add(company)
    session.add(message)


@app.get("/health")
async def health():
    return {"status": "ok", "kill_switch": settings.kill_switch}
