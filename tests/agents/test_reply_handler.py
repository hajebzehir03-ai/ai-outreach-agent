"""Test Reply Handler: 9 categorie, GDPR unsubscribe, urgency, draft_response."""

import json
import pytest
from unittest.mock import patch, MagicMock
from adh.agents.reply_handler import classify_reply


def _make_reply_response(**overrides) -> MagicMock:
    payload = {
        "category": "interested",
        "confidence": 0.92,
        "extracted": {
            "redirected_to": None,
            "follow_up_date": None,
            "question": None,
            "objection": None,
            "meeting_proposal": None,
        },
        "recommended_action": "Rispondi entro 2 ore lavorative con orari concreti",
        "draft_response": "Buongiorno Marco,\n\nperfetto! Le propongo martedì alle 15:00 o mercoledì alle 10:00. Va bene per Lei?\n\nBuona giornata,\nZehir",
        "urgency": "high",
    }
    payload.update(overrides)
    mock = MagicMock()
    mock.content = [MagicMock(text=json.dumps(payload))]
    return mock


class TestClassifyReply:
    @patch("adh.agents.reply_handler.client")
    def test_interested_high_urgency(self, mock_client):
        mock_client.messages.create.return_value = _make_reply_response()
        result = classify_reply("Sì, mi interessa. Quando possiamo sentirci?")

        assert result.category == "interested"
        assert result.urgency == "high"
        assert result.draft_response is not None
        assert result.confidence >= 0.9

    @patch("adh.agents.reply_handler.client")
    def test_unsubscribe_high_urgency(self, mock_client):
        mock_client.messages.create.return_value = _make_reply_response(
            category="unsubscribe",
            urgency="high",
            draft_response=None,
            recommended_action="Aggiungi a blacklist permanente e invia conferma di rimozione entro 24h",
        )
        result = classify_reply("STOP. Non scrivermi più.")

        assert result.category == "unsubscribe"
        assert result.urgency == "high"
        assert result.draft_response is None

    @patch("adh.agents.reply_handler.client")
    def test_interested_later_with_date(self, mock_client):
        mock_client.messages.create.return_value = _make_reply_response(
            category="interested_later",
            urgency="low",
            draft_response=None,
            extracted={
                "redirected_to": None,
                "follow_up_date": "2025-09-01T09:00:00Z",
                "question": None,
                "objection": None,
                "meeting_proposal": None,
            },
            recommended_action="Schedula follow-up alla data indicata",
        )
        result = classify_reply("Interessante, ma ora siamo in chiusura bilancio. Ricontattami a settembre.")

        assert result.category == "interested_later"
        assert result.extracted.follow_up_date is not None
        assert result.urgency == "low"

    @patch("adh.agents.reply_handler.client")
    def test_wrong_person_redirect(self, mock_client):
        mock_client.messages.create.return_value = _make_reply_response(
            category="wrong_person",
            urgency="medium",
            draft_response=None,
            extracted={
                "redirected_to": "Laura Bianchi — l.bianchi@studio.it",
                "follow_up_date": None,
                "question": None,
                "objection": None,
                "meeting_proposal": None,
            },
            recommended_action="Ringrazia e contatta la persona giusta separatamente",
        )
        result = classify_reply("Non sono io il referente per questo, scrivi a Laura Bianchi.")

        assert result.category == "wrong_person"
        assert result.extracted.redirected_to is not None
        assert "Laura" in result.extracted.redirected_to

    @patch("adh.agents.reply_handler.client")
    def test_question_generates_draft(self, mock_client):
        mock_client.messages.create.return_value = _make_reply_response(
            category="question",
            urgency="medium",
            draft_response="Il sistema si integra con i principali gestionali italiani via API. Per TeamSystem e Zucchetti ho già dei connettori pronti.",
            extracted={
                "redirected_to": None,
                "follow_up_date": None,
                "question": "Si integra con il nostro gestionale TeamSystem?",
                "objection": None,
                "meeting_proposal": None,
            },
        )
        result = classify_reply("Interessante — ma si integra con il nostro gestionale TeamSystem?")

        assert result.category == "question"
        assert result.draft_response is not None
        assert result.extracted.question is not None

    @patch("adh.agents.reply_handler.client")
    def test_out_of_office_low_urgency(self, mock_client):
        mock_client.messages.create.return_value = _make_reply_response(
            category="out_of_office",
            urgency="low",
            draft_response=None,
            extracted={
                "redirected_to": None,
                "follow_up_date": "2025-06-10T09:00:00Z",
                "question": None,
                "objection": None,
                "meeting_proposal": None,
            },
            recommended_action="Schedula re-send alla data di ritorno + 1 giorno",
        )
        result = classify_reply("Sono fuori ufficio fino al 9 giugno. Per urgenze contattare...")

        assert result.category == "out_of_office"
        assert result.urgency == "low"
        assert result.extracted.follow_up_date is not None

    @patch("adh.agents.reply_handler.client")
    def test_not_interested_no_draft(self, mock_client):
        mock_client.messages.create.return_value = _make_reply_response(
            category="not_interested",
            urgency="low",
            draft_response=None,
            extracted={
                "redirected_to": None,
                "follow_up_date": None,
                "question": None,
                "objection": "Abbiamo già un sistema interno",
                "meeting_proposal": None,
            },
        )
        result = classify_reply("Grazie ma non ci interessa, abbiamo già un sistema interno.")

        assert result.category == "not_interested"
        assert result.draft_response is None

    @patch("adh.agents.reply_handler.client")
    def test_fallback_on_parse_error(self, mock_client):
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="risposta non JSON valida {{{")]
        )
        result = classify_reply("qualcosa di strano")

        assert result.category == "other"
        assert result.confidence < 0.5
