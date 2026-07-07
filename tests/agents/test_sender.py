"""Test Sender Agent: kill switch, approval gate, edits, DB tracking del resend_id."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from adh.agents.sender import sender_node
from adh.agents.state import (
    AgentState,
    Buyability,
    CompanyData,
    IntelData,
    MessageData,
    QualificationData,
    ScoreBreakdown,
    SelfCheck,
    TechStack,
)
from adh.models import MessageStatus, OutreachMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(
    *,
    company_id: int = 1,
    decision_maker_email: str | None = "m.bertoli@studiobertoli.it",
    email: str | None = "info@studiobertoli.it",
    approval_status: str | None = "approved",
    db_message_id: int | None = None,
    edited_subject: str | None = None,
    edited_body: str | None = None,
) -> AgentState:
    """Costruisce uno stato realistico per il sender."""
    company = CompanyData(
        name="Studio Bertoli & Associati",
        sector="Studi commercialisti",
        region="Piemonte",
        city="Torino",
        decision_maker_email=decision_maker_email,
        email=email,
    )

    qualification = QualificationData(
        score=85,
        score_breakdown=ScoreBreakdown(fit_icp=35, pain_signals=25, buyability=15, reachability=10),
        tier="priority",
        selected_angle="email_triage",
        angle_rationale="Annuncio Indeed indica overload email.",
        evidence_for_writer=["Studio di 14 persone", "Annuncio Indeed", "Sito vetrina"],
        risk_flags=[],
        do_not_contact=False,
    )

    intel = IntelData(
        pain_signals=[],
        decision_makers=[],
        buyability=Buyability(score=7, positive_signals=[], negative_signals=[]),
        tech_stack=TechStack(),
        review_snippets=[],
        summary_for_writer="Studio commercialisti Torino con segnali di overload email.",
    )

    message = MessageData(
        subject="Idea per gestione email — Studio Bertoli",
        body="Buongiorno Marco,\n\nho visto il vostro annuncio su Indeed...",
        word_count=112,
        self_check=SelfCheck(
            specific_hook_present=True,
            banned_words_used=[],
            cta_concrete=True,
            ps_used=False,
            estimated_personalization_score=9,
        ),
        pitch_angle="email_triage",
        sequence_step=1,
        db_message_id=db_message_id,
    )

    return AgentState(
        company_id=company_id,
        run_id="test-run-001",
        company=company,
        intel=intel,
        qualification=qualification,
        message=message,
        current_step="approval_gate",
        approval_status=approval_status,
        edited_subject=edited_subject,
        edited_body=edited_body,
    )


# ---------------------------------------------------------------------------
# Test 1 — Kill switch
# ---------------------------------------------------------------------------

class TestKillSwitch:
    def test_kill_switch_blocks_send(self):
        """Con KILL_SWITCH=true il sender NON deve chiamare Resend."""
        state = _make_state()

        with patch("adh.agents.sender.settings") as mock_settings, \
             patch("adh.agents.sender.resend") as mock_resend:
            mock_settings.kill_switch = True

            result = sender_node(state)

            # Resend NON deve essere chiamato
            mock_resend.Emails.send.assert_not_called()
            # Lo stato deve riflettere il blocco
            assert result.status in ("blocked", "error", "stopped")


# ---------------------------------------------------------------------------
# Test 2 — Approval gate
# ---------------------------------------------------------------------------

class TestApprovalGate:
    def test_without_approval_does_not_send(self):
        """Se approval_status != 'approved' il sender NON deve mandare."""
        state = _make_state(approval_status=None)

        with patch("adh.agents.sender.settings") as mock_settings, \
             patch("adh.agents.sender.resend") as mock_resend:
            mock_settings.kill_switch = False

            result = sender_node(state)

            mock_resend.Emails.send.assert_not_called()
            assert result.status != "sent"

    def test_rejected_does_not_send(self):
        """Se approval_status == 'rejected' niente invio."""
        state = _make_state(approval_status="rejected")

        with patch("adh.agents.sender.settings") as mock_settings, \
             patch("adh.agents.sender.resend") as mock_resend:
            mock_settings.kill_switch = False

            result = sender_node(state)

            mock_resend.Emails.send.assert_not_called()
            assert result.status != "sent"


# ---------------------------------------------------------------------------
# Test 3 — No email destinatario
# ---------------------------------------------------------------------------

class TestRecipient:
    def test_no_email_returns_error(self):
        """Se né decision_maker_email né email sono presenti, errore."""
        state = _make_state(decision_maker_email=None, email=None)

        with patch("adh.agents.sender.settings") as mock_settings, \
             patch("adh.agents.sender.resend") as mock_resend:
            mock_settings.kill_switch = False

            result = sender_node(state)

            mock_resend.Emails.send.assert_not_called()
            assert result.status == "error"
            assert "email" in (result.error or "").lower()

    def test_fallback_to_company_email(self):
        """Senza decision_maker_email usa company.email."""
        state = _make_state(decision_maker_email=None, email="info@studiobertoli.it")

        with patch("adh.agents.sender.settings") as mock_settings, \
             patch("adh.agents.sender.resend") as mock_resend:
            mock_settings.kill_switch = False
            mock_settings.outreach_from_name = "Zehir"
            mock_settings.outreach_from_email = "zehir@example.it"
            mock_resend.Emails.send.return_value = {"id": "fake-resend-id"}

            result = sender_node(state)

            # Verifica che Resend sia stato chiamato CON l'email generica
            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == ["info@studiobertoli.it"]
            assert result.status == "sent"


# ---------------------------------------------------------------------------
# Test 4 — Success + DB tracking (test del fix C3)
# ---------------------------------------------------------------------------

class TestSuccessAndDbTracking:
    def test_resend_id_persisted_to_db(self, in_memory_db, db_session):
        """
        Test critico del fix C3: dopo invio, il resend_message_id deve
        finire nella tabella OutreachMessage.
        """
        # Step 1: crea un record OutreachMessage in pending_approval
        from adh.models import Company

        company = Company(
            name="Studio Test",
            sector="Studi commercialisti",
            region="Piemonte",
        )
        db_session.add(company)
        db_session.commit()
        db_session.refresh(company)

        db_msg = OutreachMessage(
            company_id=company.id,
            subject="Idea per gestione email — Studio Test",
            body="Buongiorno...",
            pitch_angle="email_triage",
            pain_signal_used="annuncio Indeed",
            sequence_step=1,
            status=MessageStatus.pending_approval,
            writer_model="claude-sonnet-4",
        )
        db_session.add(db_msg)
        db_session.commit()
        db_session.refresh(db_msg)
        db_msg_id = db_msg.id

        # Step 2: prepara lo state con il db_message_id che ci aspettiamo
        state = _make_state(company_id=company.id, db_message_id=db_msg_id)

        # Step 3: patcha settings, resend, ed engine così il sender usa il DB in-memory
        with patch("adh.agents.sender.settings") as mock_settings, \
             patch("adh.agents.sender.resend") as mock_resend, \
             patch("adh.agents.sender.engine", in_memory_db):
            mock_settings.kill_switch = False
            mock_settings.outreach_from_name = "Zehir"
            mock_settings.outreach_from_email = "zehir@example.it"
            mock_resend.Emails.send.return_value = {"id": "resend-msg-abc123"}

            result = sender_node(state)

        # Step 4: verifica state
        assert result.status == "sent"
        assert result.resend_id == "resend-msg-abc123"

        # Step 5: verifica DB
        with Session(in_memory_db) as fresh:
            updated = fresh.get(OutreachMessage, db_msg_id)
            assert updated is not None
            assert updated.resend_message_id == "resend-msg-abc123"
            assert updated.status == MessageStatus.sent
            assert updated.sent_at is not None

    def test_success_without_db_message_id_still_sends(self):
        """
        Edge case: se db_message_id è None (es. test o pipeline vecchia),
        l'email viene comunque inviata, solo il DB non viene aggiornato.
        """
        state = _make_state(db_message_id=None)

        with patch("adh.agents.sender.settings") as mock_settings, \
             patch("adh.agents.sender.resend") as mock_resend:
            mock_settings.kill_switch = False
            mock_settings.outreach_from_name = "Zehir"
            mock_settings.outreach_from_email = "zehir@example.it"
            mock_resend.Emails.send.return_value = {"id": "fake-id"}

            result = sender_node(state)

            assert result.status == "sent"
            assert result.resend_id == "fake-id"


# ---------------------------------------------------------------------------
# Test 5 — Resend exception handling
# ---------------------------------------------------------------------------

class TestResendException:
    def test_resend_exception_returns_error(self):
        """Se Resend solleva un'eccezione, sender ritorna status='error'."""
        state = _make_state()

        with patch("adh.agents.sender.settings") as mock_settings, \
             patch("adh.agents.sender.resend") as mock_resend:
            mock_settings.kill_switch = False
            mock_settings.outreach_from_name = "Zehir"
            mock_settings.outreach_from_email = "zehir@example.it"
            mock_resend.Emails.send.side_effect = Exception("Resend API down")

            result = sender_node(state)

            assert result.status == "error"
            assert "Resend" in (result.error or "") or "Errore" in (result.error or "")


# ---------------------------------------------------------------------------
# Test 6 — Edits from approval flow
# ---------------------------------------------------------------------------

class TestEditedContent:
    def test_edited_subject_used(self):
        """Se l'utente ha editato il subject in dashboard, deve essere usato quello."""
        state = _make_state(edited_subject="Subject editato dall'utente")

        with patch("adh.agents.sender.settings") as mock_settings, \
             patch("adh.agents.sender.resend") as mock_resend:
            mock_settings.kill_switch = False
            mock_settings.outreach_from_name = "Zehir"
            mock_settings.outreach_from_email = "zehir@example.it"
            mock_resend.Emails.send.return_value = {"id": "fake-id"}

            sender_node(state)

            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["subject"] == "Subject editato dall'utente"

    def test_edited_body_used(self):
        """Se l'utente ha editato il body in dashboard, deve essere usato quello."""
        state = _make_state(edited_body="Body editato dall'utente.\n\nFirma.")

        with patch("adh.agents.sender.settings") as mock_settings, \
             patch("adh.agents.sender.resend") as mock_resend:
            mock_settings.kill_switch = False
            mock_settings.outreach_from_name = "Zehir"
            mock_settings.outreach_from_email = "zehir@example.it"
            mock_resend.Emails.send.return_value = {"id": "fake-id"}

            sender_node(state)

            call_args = mock_resend.Emails.send.call_args[0][0]
            assert "Body editato" in call_args["text"]