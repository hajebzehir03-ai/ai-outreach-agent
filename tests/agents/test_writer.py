"""Test Writer Agent: validazione anti-spam, self_check, parsing."""

from unittest.mock import MagicMock, patch

from anthropic.types import TextBlock

from adh.agents.state import (
    AgentState,
    Buyability,
    CompanyData,
    IntelData,
    QualificationData,
    ScoreBreakdown,
    TechStack,
)
from adh.agents.writer import _python_validate

# ---------------------------------------------------------------------------
# Test validazione Python (safety net indipendente dall'LLM)
# ---------------------------------------------------------------------------

class TestPythonValidation:
    def test_valid_message_no_violations(self):
        subject = "Idea per la gestione email — Studio Bertoli"
        body = (
            "Buongiorno Marco,\n\n"
            "ho visto il vostro annuncio su Indeed per un addetto alla gestione email. "
            "In studi di 14 persone questa figura passa il 40-60% del tempo su pratiche ripetitive.\n\n"
            "Lavoro su questo con commercialisti torinesi: un sistema che classifica le email "
            "e prepara bozze di risposta standard. Il team rivede e invia.\n\n"
            "Le va una chiamata di 15 minuti martedì pomeriggio?\n\n"
            "Buona giornata,\nZehir\nAI Automation · Torino"
        )
        assert _python_validate(subject, body) == []

    def test_subject_over_60_chars(self):
        subject = "Questa subject è decisamente troppo lunga e supera i sessanta caratteri"
        violations = _python_validate(subject, "body ok")
        assert any("subject_too_long" in v for v in violations)

    def test_ai_keyword_in_subject(self):
        subject = "Come l'AI può aiutarti"
        violations = _python_validate(subject, "body ok")
        assert any("banned_in_subject:ai" in v for v in violations)

    def test_banned_word_rivoluzionario_in_body(self):
        subject = "Idea per voi"
        body = "Questo sistema rivoluzionario cambierà tutto."
        violations = _python_validate(subject, body)
        assert any("rivoluzionario" in v for v in violations)

    def test_spero_questa_email_banned(self):
        subject = "Idea concreta"
        body = "Spero questa email la trovi bene. Volevo presentarmi."
        violations = _python_validate(subject, body)
        assert any("spero questa email" in v for v in violations)

    def test_body_too_long(self):
        subject = "Idea per voi"
        body = " ".join(["parola"] * 200)
        violations = _python_validate(subject, body)
        assert any("body_too_long" in v for v in violations)

    def test_gpt_banned_in_body(self):
        violations = _python_validate("Soggetto ok", "Uso GPT per automatizzare.")
        assert any("gpt" in v for v in violations)


# ---------------------------------------------------------------------------
# Test writer_node con LLM mockato
# ---------------------------------------------------------------------------

def _make_mock_response(subject: str, body: str, score: int = 9, violations: list = None):
    violations = violations or []
    import json
    payload = json.dumps({
        "subject": subject,
        "body": body,
        "word_count": len(body.split()),
        "self_check": {
            "specific_hook_present": True,
            "banned_words_used": violations,
            "cta_concrete": True,
            "ps_used": False,
            "estimated_personalization_score": score,
        },
    })
    mock = MagicMock()
    mock.content = [TextBlock(type="text", text=payload)]
    return mock


def _valid_state() -> AgentState:
    return AgentState(
        company=CompanyData(
            name="Studio Bertoli & Associati",
            sector="Studi commercialisti",
            city="Torino",
            region="Piemonte",
            employees_estimate="10-25",
        ),
        intel=IntelData(
            summary_for_writer=(
                "Studio di 14 persone a Torino. Annuncio Indeed per addetto inserimento dati. "
                "Sito vetrina con solo form generico."
            ),
            buyability=Buyability(score=6),
            tech_stack=TechStack(),
        ),
        qualification=QualificationData(
            score=78,
            score_breakdown=ScoreBreakdown(fit_icp=30, pain_signals=25, buyability=12, reachability=11),
            tier="secondary",
            selected_angle="email_triage",
            angle_rationale="Annuncio Indeed segnala overhead amministrativo.",
            evidence_for_writer=[
                "Annuncio su Indeed del 12 marzo per 'addetto inserimento dati e gestione email'",
                "Studio di 14 persone, clientela PMI piemontesi",
                "Sito vetrina, contatto solo via form generico e telefono",
            ],
            do_not_contact=False,
            should_proceed=True,
        ),
    )


class TestWriterNode:
    @patch("adh.agents.writer.client")
    def test_writer_produces_valid_message(self, mock_client):
        subject = "Idea per la gestione email — Studio Bertoli"
        body = (
            "Buongiorno Marco,\n\nho visto il vostro annuncio su Indeed per un addetto alla "
            "gestione email. In studi di 14 persone questa figura passa il 40-60% del tempo su "
            "richieste ripetitive.\n\nLavoro su questo: un sistema che classifica le email e "
            "prepara bozze di risposta. Il team rivede e invia.\n\n"
            "Le va una chiamata di 15 minuti martedì pomeriggio?\n\n"
            "Buona giornata,\nZehir\nAI Automation · Torino"
        )
        mock_client.messages.create.return_value = _make_mock_response(subject, body)

        from adh.agents.writer import writer_node
        result = writer_node(_valid_state())

        assert result.message is not None
        assert result.message.subject == subject
        assert result.status != "error"
        assert result.message.self_check.specific_hook_present is True

    @patch("adh.agents.writer.client")
    def test_writer_retries_on_banned_word(self, mock_client):
        bad_subject = "Rivoluziona il tuo studio"
        bad_body = "Sistema rivoluzionario per il vostro studio."
        good_subject = "Idea per la gestione email — Studio Bertoli"
        good_body = (
            "Buongiorno,\n\nho notato il vostro annuncio su Indeed. "
            "Potrei aiutarvi a ridurre il carico amministrativo.\n\n"
            "Le va una call di 15 minuti martedì?\n\nBuona giornata,\nZehir"
        )
        mock_client.messages.create.side_effect = [
            _make_mock_response(bad_subject, bad_body, violations=["rivoluzionario"]),
            _make_mock_response(good_subject, good_body),
        ]

        from adh.agents.writer import writer_node
        state = _valid_state()
        # Primo tentativo: fallisce e incrementa writer_attempts
        r1 = writer_node(state)
        # Secondo tentativo: passa
        r2 = writer_node(r1)

        assert r2.message is not None
        assert r2.status != "error"

    @patch("adh.agents.writer.client")
    def test_writer_archives_after_max_retries(self, mock_client):
        from adh.agents.writer import writer_node
        state = _valid_state().model_copy(update={"writer_attempts": 2})
        result = writer_node(state)
        assert result.status == "error"
        assert "retry" in result.error.lower()

    @patch("adh.agents.writer.client")
    def test_personalization_score_captured(self, mock_client):
        subject = "Richieste perse — Casa Più Immobiliare"
        body = (
            "Buongiorno,\n\nho visto le recensioni Google degli ultimi due mesi: "
            "tre clienti scrivono di non essere stati richiamati. "
            "Con 47 immobili attivi le richieste arrivano anche fuori orario.\n\n"
            "Ho messo in piedi per agenzie simili un assistente WhatsApp che risponde subito "
            "e gira a voi i contatti qualificati.\n\n"
            "Le va una call di 15 minuti la prossima settimana?\n\nBuona giornata,\nZehir"
        )
        mock_client.messages.create.return_value = _make_mock_response(subject, body, score=9)

        from adh.agents.writer import writer_node
        result = writer_node(_valid_state())
        assert result.message.self_check.estimated_personalization_score == 9
