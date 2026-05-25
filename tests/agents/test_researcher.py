"""
Test Researcher Agent: _fetch_text, _google_reviews, _llm_analyze, researcher_node.
Nessuna chiamata reale a HTTP o Anthropic API.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock

from adh.agents.researcher import (
    _fetch_text,
    _google_reviews,
    _llm_analyze,
    researcher_node,
)
from adh.agents.state import AgentState, CompanyData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(
    *,
    name: str = "Studio Bertoli & Associati",
    sector: str = "Studi commercialisti",
    region: str = "Piemonte",
    website: str | None = "https://studiobertoli.it",
    google_place_id: str | None = "place_001",
    company_id: int = 1,
) -> AgentState:
    company = CompanyData(
        name=name,
        sector=sector,
        region=region,
        city="Torino",
        website=website,
        google_place_id=google_place_id,
    )
    return AgentState(company=company, company_id=company_id)


def _make_llm_payload(
    pain_signals: list | None = None,
    decision_makers: list | None = None,
    buyability_score: int = 7,
    summary: str = "Studio commercialisti con segnali di overload email.",
) -> dict:
    """Costruisce un payload JSON realistico per la risposta LLM."""
    return {
        "pain_signals": pain_signals or [
            {
                "signal": "Annuncio Indeed per addetto email",
                "evidence": "Annuncio trovato su Indeed del 12 marzo",
                "source_url": "https://indeed.com/123",
                "weight": 8,
            }
        ],
        "decision_makers": decision_makers or [
            {
                "name": "Marco Bertoli",
                "role": "Socio fondatore",
                "linkedin": None,
                "email_guessed": "m.bertoli@studiobertoli.it",
                "email_pattern_confidence": 0.7,
                "source": "https://studiobertoli.it/chi-siamo",
            }
        ],
        "buyability": {
            "score": buyability_score,
            "positive_signals": ["Studio in crescita"],
            "negative_signals": [],
        },
        "tech_stack": {
            "cms": "WordPress",
            "chatbot": None,
            "crm": None,
            "other": [],
        },
        "summary_for_writer": summary,
    }


def _make_llm_response(payload: dict) -> MagicMock:
    """Mock di anthropic.Message con TextBlock reale."""
    mock = MagicMock()
    mock.content = [TextBlock(type="text", text=json.dumps(payload))]
    return mock


# ---------------------------------------------------------------------------
# Test 1 — _fetch_text (HTTP mockato)
# ---------------------------------------------------------------------------

class TestFetchText:
    @pytest.mark.asyncio
    async def test_returns_stripped_html(self):
        """_fetch_text deve ritornare testo senza tag HTML."""
        html = "<html><body><h1>Studio Bertoli</h1><p>Commercialisti a Torino</p></body></html>"
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.url = "https://studiobertoli.it"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("adh.agents.researcher.httpx.AsyncClient", return_value=mock_client):
            text, url = await _fetch_text("https://studiobertoli.it")

        assert "<html>" not in text
        assert "Studio Bertoli" in text
        assert "Commercialisti a Torino" in text
        assert url == "https://studiobertoli.it"

    @pytest.mark.asyncio
    async def test_adds_https_if_missing(self):
        """URL senza schema → aggiunge https://."""
        mock_response = MagicMock()
        mock_response.text = "testo"
        mock_response.url = "https://studiobertoli.it"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("adh.agents.researcher.httpx.AsyncClient", return_value=mock_client):
            text, url = await _fetch_text("studiobertoli.it")

        # Deve aver fatto la chiamata (non ritornato vuoto)
        assert mock_client.get.called
        called_url = mock_client.get.call_args[0][0]
        assert called_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_empty_url_returns_empty(self):
        """URL vuoto → ritorna stringhe vuote senza fare chiamate HTTP."""
        with patch("adh.agents.researcher.httpx.AsyncClient") as mock_cls:
            text, url = await _fetch_text("")

        mock_cls.assert_not_called()
        assert text == ""
        assert url == ""

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        """Errore HTTP → ritorna stringhe vuote (non crasha)."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("adh.agents.researcher.httpx.AsyncClient", return_value=mock_client):
            text, url = await _fetch_text("https://sito-inesistente.it")

        assert text == ""

    @pytest.mark.asyncio
    async def test_truncates_long_text(self):
        """Testo > 6000 caratteri viene troncato."""
        long_html = "<p>" + "x" * 10000 + "</p>"
        mock_response = MagicMock()
        mock_response.text = long_html
        mock_response.url = "https://example.it"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("adh.agents.researcher.httpx.AsyncClient", return_value=mock_client):
            text, _ = await _fetch_text("https://example.it")

        assert len(text) <= 6000


# ---------------------------------------------------------------------------
# Test 2 — _google_reviews (HTTP mockato)
# ---------------------------------------------------------------------------

class TestGoogleReviews:
    @pytest.mark.asyncio
    async def test_returns_pain_snippets(self):
        """Reviews con parole chiave di dolore → incluse negli snippets."""
        reviews_data = {
            "result": {
                "rating": 3.2,
                "user_ratings_total": 45,
                "reviews": [
                    {"rating": 1, "text": "Non rispondono mai al telefono, tempi lunghissimi"},
                    {"rating": 5, "text": "Ottimo studio, molto professionali"},
                    {"rating": 2, "text": "Lento nelle risposte, disorganizzati"},
                ]
            }
        }
        mock_response = MagicMock()
        mock_response.json.return_value = reviews_data

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("adh.agents.researcher.httpx.AsyncClient", return_value=mock_client):
            rating, count, snippets = await _google_reviews("place_001")

        assert rating == 3.2
        assert count == 45
        # Solo le review con pain keywords (non quella 5 stelle positiva)
        assert len(snippets) == 2
        assert all(s.rating in (1, 2) for s in snippets)

    @pytest.mark.asyncio
    async def test_empty_place_id_returns_defaults(self):
        """place_id vuoto → ritorna valori default senza HTTP call."""
        with patch("adh.agents.researcher.httpx.AsyncClient") as mock_cls:
            rating, count, snippets = await _google_reviews("")

        mock_cls.assert_not_called()
        assert rating == 0.0
        assert count == 0
        assert snippets == []

    @pytest.mark.asyncio
    async def test_no_api_key_returns_defaults(self):
        """Senza API key → ritorna valori default."""
        with patch("adh.agents.researcher.settings") as mock_settings:
            mock_settings.google_places_api_key = None

            with patch("adh.agents.researcher.httpx.AsyncClient") as mock_cls:
                rating, count, snippets = await _google_reviews("place_001")

        mock_cls.assert_not_called()
        assert snippets == []

    @pytest.mark.asyncio
    async def test_http_error_returns_defaults(self):
        """Errore HTTP → ritorna defaults senza crashare."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=Exception("Timeout"))

        with patch("adh.agents.researcher.httpx.AsyncClient", return_value=mock_client):
            rating, count, snippets = await _google_reviews("place_001")

        assert rating == 0.0
        assert snippets == []


# ---------------------------------------------------------------------------
# Test 3 — _llm_analyze (Anthropic mockato)
# ---------------------------------------------------------------------------

class TestLlmAnalyze:
    def test_returns_parsed_dict(self):
        """_llm_analyze deve ritornare il dict parsato dalla risposta LLM."""
        payload = _make_llm_payload()
        mock_response = _make_llm_response(payload)

        with patch("adh.agents.researcher.client") as mock_client:
            mock_client.messages.create.return_value = mock_response
            result = _llm_analyze(
                "Studio Bertoli",
                "Studi commercialisti",
                "Testo del sito web",
                "https://studiobertoli.it",
                ["Non rispondono mai"],
            )

        assert result["buyability"]["score"] == 7
        assert len(result["pain_signals"]) == 1
        assert result["pain_signals"][0]["signal"] == "Annuncio Indeed per addetto email"

    def test_strips_markdown_fences(self):
        """Se LLM risponde con ```json ... ```, deve essere strippato."""
        payload = _make_llm_payload()
        raw_with_fences = f"```json\n{json.dumps(payload)}\n```"
        mock_response = MagicMock()
        mock_response.content = [TextBlock(type="text", text=raw_with_fences)]

        with patch("adh.agents.researcher.client") as mock_client:
            mock_client.messages.create.return_value = mock_response
            result = _llm_analyze("test", "test", "", "", [])

        assert isinstance(result, dict)
        assert "pain_signals" in result

    def test_raises_on_invalid_json(self):
        """Se LLM risponde con JSON non valido → ValueError/JSONDecodeError propagato."""
        mock_response = MagicMock()
        mock_response.content = [TextBlock(type="text", text="risposta non JSON {{{")]

        with patch("adh.agents.researcher.client") as mock_client:
            mock_client.messages.create.return_value = mock_response
            with pytest.raises(Exception):
                _llm_analyze("test", "test", "", "", [])

    def test_passes_company_name_in_prompt(self):
        """Il nome dell'azienda deve apparire nel messaggio inviato all'LLM."""
        payload = _make_llm_payload()
        mock_response = _make_llm_response(payload)

        with patch("adh.agents.researcher.client") as mock_client:
            mock_client.messages.create.return_value = mock_response
            _llm_analyze("Studio Bertoli Unico", "test", "", "", [])

        call_args = mock_client.messages.create.call_args
        user_content = call_args[1]["messages"][0]["content"]
        assert "Studio Bertoli Unico" in user_content


# ---------------------------------------------------------------------------
# Test 4 — researcher_node (tutto mockato)
# ---------------------------------------------------------------------------

class TestResearcherNode:
    def test_no_company_returns_error(self):
        """State senza company → errore immediato."""
        state = AgentState(company=None)
        result = researcher_node(state)
        assert result.status == "error"
        assert result.error is not None

    def test_successful_enrichment(self):
        """Flow completo → intel popolato correttamente."""
        state = _make_state()
        payload = _make_llm_payload()
        mock_llm_response = _make_llm_response(payload)

        with patch("adh.agents.researcher.asyncio.get_event_loop") as mock_loop, \
             patch("adh.agents.researcher.client") as mock_client:
            # Mock event loop per le chiamate async
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance
            mock_loop_instance.run_until_complete.side_effect = [
                ("Testo sito web Studio Bertoli", "https://studiobertoli.it"),
                (3.5, 20, []),  # rating, count, snippets
            ]
            mock_client.messages.create.return_value = mock_llm_response

            result = researcher_node(state)

        assert result.status != "error"
        assert result.intel is not None
        assert result.intel.company_name == "Studio Bertoli & Associati"
        assert result.current_step == "qualifier"
        assert len(result.intel.pain_signals) == 1
        assert result.intel.pain_signals[0].signal == "Annuncio Indeed per addetto email"

    def test_llm_error_returns_error_state(self):
        """Se LLM fallisce → stato error con messaggio."""
        state = _make_state()

        with patch("adh.agents.researcher.asyncio.get_event_loop") as mock_loop, \
             patch("adh.agents.researcher.client") as mock_client:
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance
            mock_loop_instance.run_until_complete.side_effect = [
                ("testo", "https://studiobertoli.it"),
                (0.0, 0, []),
            ]
            mock_client.messages.create.side_effect = Exception("Anthropic API down")

            result = researcher_node(state)

        assert result.status == "error"
        assert "LLM" in (result.error or "") or "researcher" in (result.error or "").lower()

    def test_enriches_decision_maker(self):
        """decision_makers nel payload LLM → parsati correttamente."""
        state = _make_state()
        payload = _make_llm_payload()
        mock_llm_response = _make_llm_response(payload)

        with patch("adh.agents.researcher.asyncio.get_event_loop") as mock_loop, \
             patch("adh.agents.researcher.client") as mock_client:
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance
            mock_loop_instance.run_until_complete.side_effect = [
                ("testo", "https://studiobertoli.it"),
                (0.0, 0, []),
            ]
            mock_client.messages.create.return_value = mock_llm_response

            result = researcher_node(state)

        assert len(result.intel.decision_makers) == 1
        dm = result.intel.decision_makers[0]
        assert dm.name == "Marco Bertoli"
        assert dm.role == "Socio fondatore"
        assert dm.email_guessed == "m.bertoli@studiobertoli.it"

    def test_no_website_still_proceeds(self):
        """Company senza website → researcher procede (website_text vuoto)."""
        state = _make_state(website=None, google_place_id=None)
        payload = _make_llm_payload(pain_signals=[], decision_makers=[])
        mock_llm_response = _make_llm_response(payload)

        with patch("adh.agents.researcher.asyncio.get_event_loop") as mock_loop, \
             patch("adh.agents.researcher.client") as mock_client:
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance
            mock_loop_instance.run_until_complete.side_effect = [
                ("", ""),
                (0.0, 0, []),
            ]
            mock_client.messages.create.return_value = mock_llm_response

            result = researcher_node(state)

        assert result.status != "error"
        assert result.intel is not None