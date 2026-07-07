"""Test Qualifier Agent: parsing JSON, do_not_contact, evidence enforcement."""

import json
from unittest.mock import MagicMock, patch

from anthropic.types import TextBlock

from adh.agents.state import (
    AgentState,
    Buyability,
    CompanyData,
    DecisionMaker,
    IntelData,
    PainSignal,
    TechStack,
)


def _make_qualifier_response(**overrides) -> MagicMock:
    payload = {
        "company_id": "test-001",
        "score": 75,
        "score_breakdown": {"fit_icp": 30, "pain_signals": 25, "buyability": 12, "reachability": 8},
        "tier": "secondary",
        "selected_angle": "email_triage",
        "angle_rationale": "Annuncio Indeed per addetto email segnala overhead amministrativo.",
        "evidence_for_writer": [
            "Annuncio Indeed del 12 marzo per 'addetto inserimento dati'",
            "Studio di 14 persone con clientela PMI piemontese",
            "Sito vetrina con form generico e nessun autorisponditore",
        ],
        "risk_flags": [],
        "do_not_contact": False,
    }
    payload.update(overrides)
    mock = MagicMock()
    mock.content = [TextBlock(type="text", text=json.dumps(payload))]
    return mock


def _base_state() -> AgentState:
    return AgentState(
        company_id=1,
        company=CompanyData(
            name="Studio Bertoli & Associati",
            sector="Studi commercialisti",
            city="Torino",
            region="Piemonte",
            employees_estimate="10-25",
        ),
        intel=IntelData(
            pain_signals=[
                PainSignal(signal="email_overhead", evidence="Annuncio Indeed", source_url="https://indeed.com/job/123", weight=8),
            ],
            decision_makers=[
                DecisionMaker(name="Marco Bertoli", role="Socio fondatore", email_guessed="m.bertoli@studiobertoli.it", email_pattern_confidence=0.8, source="https://studiobertoli.it"),
            ],
            buyability=Buyability(score=6, positive_signals=["crescita recente"]),
            tech_stack=TechStack(cms="WordPress", chatbot=None),
            summary_for_writer="Studio di 14 persone a Torino. Annuncio Indeed per addetto email.",
        ),
    )


class TestQualifierNode:
    @patch("adh.agents.qualifier.client")
    def test_normal_qualification_proceeds(self, mock_client):
        mock_client.messages.create.return_value = _make_qualifier_response()

        from adh.agents.qualifier import qualifier_node
        result = qualifier_node(_base_state())

        assert result.qualification is not None
        assert result.qualification.score == 75
        assert result.qualification.should_proceed is True
        assert result.qualification.selected_angle == "email_triage"
        assert len(result.qualification.evidence_for_writer) == 3

    @patch("adh.agents.qualifier.client")
    def test_do_not_contact_blocks_proceed(self, mock_client):
        mock_client.messages.create.return_value = _make_qualifier_response(
            do_not_contact=True, score=80, tier="priority"
        )

        from adh.agents.qualifier import qualifier_node
        result = qualifier_node(_base_state())

        assert result.qualification.do_not_contact is True
        assert result.qualification.should_proceed is False
        assert result.current_step == "drop"

    @patch("adh.agents.qualifier.client")
    def test_low_score_drops(self, mock_client):
        mock_client.messages.create.return_value = _make_qualifier_response(
            score=45, tier="drop"
        )

        from adh.agents.qualifier import qualifier_node
        result = qualifier_node(_base_state())

        assert result.qualification.should_proceed is False
        assert result.current_step == "drop"

    @patch("adh.agents.qualifier.client")
    def test_less_than_3_evidence_forces_drop(self, mock_client):
        mock_client.messages.create.return_value = _make_qualifier_response(
            score=70, tier="secondary",
            evidence_for_writer=["Solo un bullet — non abbastanza"],
        )

        from adh.agents.qualifier import qualifier_node
        result = qualifier_node(_base_state())

        # Score deve scendere sotto 60 per regola hard
        assert result.qualification.score < 60
        assert result.qualification.should_proceed is False

    @patch("adh.agents.qualifier.client")
    def test_priority_tier_for_high_score(self, mock_client):
        mock_client.messages.create.return_value = _make_qualifier_response(
            score=85, tier="priority",
            score_breakdown={"fit_icp": 35, "pain_signals": 28, "buyability": 14, "reachability": 8},
        )

        from adh.agents.qualifier import qualifier_node
        result = qualifier_node(_base_state())

        assert result.qualification.tier == "priority"
        assert result.qualification.score == 85
