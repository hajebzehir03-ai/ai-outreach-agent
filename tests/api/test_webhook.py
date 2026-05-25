"""
Test Webhook: classificazione reply, GDPR unsubscribe, notifiche Telegram,
edge case (messaggio non trovato, event type sconosciuto).
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from adh.api.webhook import app
from adh.models import Company, MessageStatus, OutreachMessage, ProcessingLog
from adh.models.company import CompanyStatus
from adh.models.message import ReplyIntent


# ---------------------------------------------------------------------------
# Fixture: TestClient FastAPI + DB in-memory
# ---------------------------------------------------------------------------

@pytest.fixture
def client(in_memory_db):
    """
    TestClient FastAPI con DB in-memory iniettato.
    
    Patcha engine in TUTTI i posti dove viene usato dal webhook:
    - adh.api.webhook.engine (usato inline nel handler)
    - adh.models.database.engine (il modulo sorgente)
    
    Entrambi devono puntare allo stesso in_memory_db altrimenti
    Session() cattura il riferimento originale (PostgreSQL).
    """
    with patch("adh.api.webhook.engine", in_memory_db), \
         patch("adh.models.database.engine", in_memory_db):
        yield TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def company_with_message(in_memory_db):
    """
    Crea Company + OutreachMessage nel DB in-memory.
    Usa direttamente in_memory_db invece di db_session per evitare
    conflitti tra sessioni multiple sullo stesso engine SQLite.
    """
    from adh.models.company import CompanyStatus

    with Session(in_memory_db) as session:
        company = Company(
            name="Studio Bertoli & Associati",
            sector="Studi commercialisti",
            region="Piemonte",
            city="Torino",
            email="info@studiobertoli.it",
            decision_maker_name="Marco Bertoli",
            decision_maker_role="Socio fondatore",
            decision_maker_email="m.bertoli@studiobertoli.it",
            status=CompanyStatus.contacted,
        )
        session.add(company)
        session.commit()
        session.refresh(company)

        message = OutreachMessage(
            company_id=company.id,
            subject="Idea per gestione email — Studio Bertoli",
            body="Buongiorno Marco...",
            pitch_angle="email_triage",
            pain_signal_used="annuncio Indeed",
            sequence_step=1,
            status=MessageStatus.sent,
            resend_message_id="resend-msg-abc123",
            writer_model="claude-sonnet-4",
        )
        session.add(message)
        session.commit()
        session.refresh(message)

        # Ritorna copie "detached" con tutti gli attributi già caricati
        company_id = company.id
        message_id = message.id
        message_resend_id = message.resend_message_id

    # Rileggi fuori dalla sessione per avere oggetti puliti
    with Session(in_memory_db) as session:
        company = session.get(Company, company_id)
        message = session.get(OutreachMessage, message_id)
        return company, message


def _make_webhook_payload(
    event_type: str = "email.replied",
    resend_message_id: str = "resend-msg-abc123",
    reply_body: str = "Sì, mi interessa. Quando possiamo sentirci?",
) -> dict:
    """Costruisce un payload Resend realistico."""
    return {
        "type": event_type,
        "data": {
            "message_id": resend_message_id,
            "text": reply_body,
            "from": "m.bertoli@studiobertoli.it",
            "subject": "Re: Idea per gestione email — Studio Bertoli",
        },
    }

# ---------------------------------------------------------------------------
# Test 1 — Evento sconosciuto (no crash)
# ---------------------------------------------------------------------------

class TestUnknownEvent:
    def test_unknown_event_type_returns_200(self, client):
        """Evento tipo sconosciuto deve essere ignorato silenziosamente."""
        payload = _make_webhook_payload(event_type="email.bounced")

        response = client.post("/webhook/resend", json=payload)

        assert response.status_code == 200

    def test_missing_message_id_returns_200(self, client):
        """Payload senza message_id non deve crashare."""
        payload = {"type": "email.replied", "data": {}}

        response = client.post("/webhook/resend", json=payload)

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test 2 — Messaggio non trovato nel DB
# ---------------------------------------------------------------------------

class TestMessageNotFound:
    def test_unknown_resend_id_returns_200(self, client):
        """Se il resend_message_id non corrisponde a nessun OutreachMessage, no crash."""
        payload = _make_webhook_payload(resend_message_id="id-che-non-esiste")

        response = client.post("/webhook/resend", json=payload)

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test 3 — Unsubscribe (GDPR critico)
# ---------------------------------------------------------------------------

class TestUnsubscribe:
    def test_unsubscribe_blacklists_company_permanently(
        self, client, company_with_message, in_memory_db
    ):
        """
        STOP ricevuto → company.status = blacklisted,
        blacklisted_until = None (permanente),
        ProcessingLog creato.
        """
        company, message = company_with_message

        with patch("adh.api.webhook.classify_reply") as mock_classify, \
             patch("adh.api.webhook.engine", in_memory_db):
            mock_classify.return_value = MagicMock(
                category="unsubscribe",
                confidence=0.99,
                draft_response=None,
                urgency="high",
            )

            payload = _make_webhook_payload(
                resend_message_id=message.resend_message_id,
                reply_body="Non scrivermi più. STOP.",
            )
            response = client.post("/webhook/resend", json=payload)

        assert response.status_code == 200

        # Verifica DB
        with Session(in_memory_db) as s:
            updated_company = s.get(Company, company.id)
            assert updated_company.status == CompanyStatus.blacklisted
            assert updated_company.blacklisted_until is None  # permanente

            # Verifica ProcessingLog GDPR
            log = s.exec(
                select(ProcessingLog).where(
                    ProcessingLog.company_id == company.id
                )
            ).first()
            assert log is not None
            assert "unsubscribe" in log.action.lower()

    def test_unsubscribe_updates_message_status(
        self, client, company_with_message, in_memory_db
    ):
        """Dopo unsubscribe, il messaggio deve essere marcato come replied."""
        company, message = company_with_message

        with patch("adh.api.webhook.classify_reply") as mock_classify, \
             patch("adh.api.webhook.engine", in_memory_db):
            mock_classify.return_value = MagicMock(
                category="unsubscribe",
                confidence=0.99,
                draft_response=None,
                urgency="high",
            )

            payload = _make_webhook_payload(
                resend_message_id=message.resend_message_id,
                reply_body="STOP.",
            )
            client.post("/webhook/resend", json=payload)

        with Session(in_memory_db) as s:
            updated_msg = s.get(OutreachMessage, message.id)
            assert updated_msg.status == MessageStatus.replied
            assert updated_msg.reply_intent == ReplyIntent.unsubscribe


# ---------------------------------------------------------------------------
# Test 4 — Lead caldo (interested)
# ---------------------------------------------------------------------------

class TestInterested:
    def test_interested_notifies_telegram(
        self, client, company_with_message, in_memory_db
    ):
        """Lead caldo → notify_telegram viene chiamata (awaited) con il messaggio."""
        company, message = company_with_message

        with patch("adh.api.webhook.classify_reply") as mock_classify, \
             patch("adh.api.webhook.notify_telegram", new_callable=AsyncMock) as mock_notify, \
             patch("adh.api.webhook.engine", in_memory_db):
            mock_classify.return_value = MagicMock(
                category="interested",
                confidence=0.95,
                draft_response=None,
                urgency="high",
            )

            payload = _make_webhook_payload(
                resend_message_id=message.resend_message_id,
                reply_body="Sì, mi interessa. Quando possiamo sentirci?",
            )
            client.post("/webhook/resend", json=payload)

        mock_notify.assert_called_once()
        call_arg = mock_notify.call_args[0][0]
        assert "lead" in call_arg.lower() or "Studio Bertoli" in call_arg

    def test_interested_updates_company_status(
        self, client, company_with_message, in_memory_db
    ):
        """Company.status → replied dopo risposta positiva."""
        company, message = company_with_message

        with patch("adh.api.webhook.classify_reply") as mock_classify, \
             patch("adh.api.webhook.notify_telegram", new_callable=AsyncMock), \
             patch("adh.api.webhook.engine", in_memory_db):
            mock_classify.return_value = MagicMock(
                category="interested",
                confidence=0.95,
                draft_response=None,
                urgency="high",
            )

            payload = _make_webhook_payload(
                resend_message_id=message.resend_message_id,
                reply_body="Sì, mi interessa.",
            )
            client.post("/webhook/resend", json=payload)

        with Session(in_memory_db) as s:
            updated = s.get(Company, company.id)
            assert updated.status == CompanyStatus.replied


# ---------------------------------------------------------------------------
# Test 5 — Not interested
# ---------------------------------------------------------------------------

class TestNotInterested:
    def test_not_interested_blacklists_for_one_year(
        self, client, company_with_message, in_memory_db
    ):
        """Non interessato → blacklist temporanea 365 giorni."""
        company, message = company_with_message

        with patch("adh.api.webhook.classify_reply") as mock_classify, \
             patch("adh.api.webhook.engine", in_memory_db):
            mock_classify.return_value = MagicMock(
                category="not_interested",
                confidence=0.9,
                draft_response=None,
                urgency="low",
            )

            payload = _make_webhook_payload(
                resend_message_id=message.resend_message_id,
                reply_body="Non ci interessa, grazie.",
            )
            client.post("/webhook/resend", json=payload)

        with Session(in_memory_db) as s:
            updated = s.get(Company, company.id)
            assert updated.status == CompanyStatus.not_interested
            assert updated.blacklisted_until is not None
            # Deve essere circa 365 giorni nel futuro (± 1 giorno di tolleranza)
            # SQLite restituisce datetime naive — aggiungiamo UTC per renderlo comparabile
            blacklisted_until = updated.blacklisted_until.replace(tzinfo=UTC)
            days_ahead = (blacklisted_until - datetime.now(UTC)).days
            assert 363 <= days_ahead <= 366


# ---------------------------------------------------------------------------
# Test 6 — Question (genera bozza risposta)
# ---------------------------------------------------------------------------

class TestQuestion:
    def test_question_saves_draft_response(
        self, client, company_with_message, in_memory_db
    ):
        """Domanda ricevuta → bozza risposta salvata nel messaggio."""
        company, message = company_with_message
        draft_text = "Buongiorno Marco, la soluzione funziona così..."

        with patch("adh.api.webhook.classify_reply") as mock_classify, \
             patch("adh.api.webhook.engine", in_memory_db):
            mock_classify.return_value = MagicMock(
                category="question",
                confidence=0.88,
                draft_response=draft_text,
                urgency="medium",
            )

            payload = _make_webhook_payload(
                resend_message_id=message.resend_message_id,
                reply_body="Ma questo sistema funziona anche con il nostro gestionale?",
            )
            client.post("/webhook/resend", json=payload)

        with Session(in_memory_db) as s:
            updated_msg = s.get(OutreachMessage, message.id)
            assert updated_msg.reply_intent == ReplyIntent.question
            assert updated_msg.reply_draft == draft_text


# ---------------------------------------------------------------------------
# Test 7 — Out of office
# ---------------------------------------------------------------------------

class TestOutOfOffice:
    def test_out_of_office_no_blacklist(
        self, client, company_with_message, in_memory_db
    ):
        """OOO → nessuna blacklist, company.status non cambia."""
        company, message = company_with_message
        original_status = company.status

        with patch("adh.api.webhook.classify_reply") as mock_classify, \
             patch("adh.api.webhook.engine", in_memory_db):
            mock_classify.return_value = MagicMock(
                category="out_of_office",
                confidence=0.99,
                draft_response=None,
                urgency="low",
            )

            payload = _make_webhook_payload(
                resend_message_id=message.resend_message_id,
                reply_body="Sono fuori ufficio fino al 30 maggio.",
            )
            client.post("/webhook/resend", json=payload)

        with Session(in_memory_db) as s:
            updated = s.get(Company, company.id)
            # Status non deve cambiare per OOO
            assert updated.status == original_status
            assert updated.blacklisted_until is None


# ---------------------------------------------------------------------------
# Test 8 — Health check endpoint
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_health_returns_ok(self, client):
        """Endpoint /health deve rispondere 200."""
        response = client.get("/health")
        assert response.status_code == 200