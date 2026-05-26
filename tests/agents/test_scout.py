"""
Test Scout Agent: _in_region, scout_node, scout_single_sector (HTTP mockato).
Nessuna chiamata reale a Google Places.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adh.agents.scout import _in_region, _place_details, scout_node, scout_single_sector
from adh.agents.state import AgentState, CompanyData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(
    *,
    name: str = "Studio Bertoli",
    sector: str = "Studi commercialisti",
    region: str = "Piemonte",
    confidence: float = 0.9,
    company: CompanyData | None = None,
) -> AgentState:
    if company is None:
        company = CompanyData(
            name=name,
            sector=sector,
            region=region,
            city="Torino",
            confidence=confidence,
        )
    return AgentState(company=company)


def _make_places_search_response(results: list[dict]) -> MagicMock:
    """Mock di httpx.Response per la chiamata textsearch."""
    mock = MagicMock()
    mock.json.return_value = {"results": results}
    mock.raise_for_status = MagicMock()
    return mock


def _make_places_details_response(result: dict) -> MagicMock:
    """Mock di httpx.Response per la chiamata details."""
    mock = MagicMock()
    mock.json.return_value = {"result": result}
    mock.raise_for_status = MagicMock()
    return mock


def _make_place(
    name: str = "Studio Bertoli",
    place_id: str = "place_001",
    address: str = "Via Roma 1, Torino, TO, Italia",
    status: str = "OPERATIONAL",
) -> dict:
    """Costruisce un risultato Google Places realistico."""
    return {
        "name": name,
        "place_id": place_id,
        "formatted_address": address,
        "business_status": status,
    }


def _make_details(
    website: str | None = "https://studiobertoli.it",
    phone: str | None = "+39 011 123456",
) -> dict:
    return {
        "website": website,
        "formatted_phone_number": phone,
        "formatted_address": "Via Roma 1, Torino, TO, Italia",
        "business_status": "OPERATIONAL",
    }


# ---------------------------------------------------------------------------
# Test 1 — _in_region (logica pura, zero mock)
# ---------------------------------------------------------------------------

class TestInRegion:
    def test_torino_in_piemonte(self):
        assert _in_region("Via Roma 1, Torino, TO, Italia", "Piemonte") is True

    def test_milano_not_in_piemonte(self):
        assert _in_region("Via Montenapoleone 1, Milano, MI, Italia", "Piemonte") is False

    def test_venezia_in_veneto(self):
        assert _in_region("Piazza San Marco, Venezia, VE, Italia", "Veneto") is True

    def test_bologna_in_emilia(self):
        assert _in_region("Via Indipendenza, Bologna, BO, Italia", "Emilia-Romagna") is True

    def test_case_insensitive(self):
        """Match deve essere case-insensitive."""
        assert _in_region("via roma, TORINO, italia", "Piemonte") is True

    def test_unknown_region_uses_region_name(self):
        """Regione non in REGION_KEYWORDS usa il nome stesso come keyword."""
        assert _in_region("Via Dante, Firenze, FI, Italia", "Firenze") is True

    def test_empty_address(self):
        assert _in_region("", "Piemonte") is False


# ---------------------------------------------------------------------------
# Test 2 — scout_node (logica pura, zero mock)
# ---------------------------------------------------------------------------

class TestScoutNode:
    def test_valid_company_proceeds(self):
        """Company valida → current_step aggiornato a 'researcher'."""
        state = _make_state()
        result = scout_node(state)
        assert result.current_step == "researcher"
        assert result.status != "error"

    def test_no_company_returns_error(self):
        """State senza company → errore."""
        state = AgentState(company=None)
        result = scout_node(state)
        assert result.status == "error"
        assert result.error is not None

    def test_missing_name_returns_error(self):
        """Company senza nome → errore."""
        state = _make_state(name="")
        result = scout_node(state)
        assert result.status == "error"

    def test_missing_sector_returns_error(self):
        """Company senza sector → errore."""
        state = _make_state(sector="")
        result = scout_node(state)
        assert result.status == "error"

    def test_missing_region_returns_error(self):
        """Company senza region → errore."""
        state = _make_state(region="")
        result = scout_node(state)
        assert result.status == "error"

    def test_low_confidence_drops(self):
        """Confidence < 0.6 → status dropped."""
        state = _make_state(confidence=0.5)
        result = scout_node(state)
        assert result.status == "dropped"

    def test_exactly_06_confidence_passes(self):
        """Confidence == 0.6 → non droppata (soglia inclusa)."""
        state = _make_state(confidence=0.6)
        result = scout_node(state)
        assert result.status != "dropped"

    def test_high_confidence_passes(self):
        """Confidence alta → passa sempre."""
        state = _make_state(confidence=0.95)
        result = scout_node(state)
        assert result.current_step == "researcher"


# ---------------------------------------------------------------------------
# Test 3 — _place_details (HTTP mockato)
# ---------------------------------------------------------------------------

class TestPlaceDetails:
    @pytest.mark.asyncio
    async def test_returns_parsed_result(self):
        """_place_details deve ritornare il dict 'result' della risposta."""
        details = _make_details()
        mock_response = _make_places_details_response(details)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("adh.agents.scout.httpx.AsyncClient", return_value=mock_client):
            result = await _place_details("place_001")

        assert result["website"] == "https://studiobertoli.it"
        assert result["formatted_phone_number"] == "+39 011 123456"

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_dict(self):
        """Se Google Places non ha dettagli, ritorna dict vuoto."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("adh.agents.scout.httpx.AsyncClient", return_value=mock_client):
            result = await _place_details("place_001")

        assert result == {}


# ---------------------------------------------------------------------------
# Test 4 — scout_single_sector (HTTP mockato end-to-end)
# ---------------------------------------------------------------------------

class TestScoutSingleSector:
    @pytest.mark.asyncio
    async def test_returns_company_data_list(self):
        """Risultato normale → lista di CompanyData con campi corretti."""
        search_response = _make_places_search_response([
            _make_place("Studio Bertoli", "place_001", "Via Roma 1, Torino, TO, Italia"),
        ])
        details_response = _make_places_details_response(
            _make_details("https://studiobertoli.it", "+39 011 123456")
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=[search_response, details_response])

        with patch("adh.agents.scout.httpx.AsyncClient", return_value=mock_client):
            results = await scout_single_sector("Studi commercialisti", "Piemonte", limit=10)

        assert len(results) == 1
        assert results[0].name == "Studio Bertoli"
        assert results[0].sector == "Studi commercialisti"
        assert results[0].region == "Piemonte"
        assert results[0].website == "https://studiobertoli.it"
        assert results[0].google_place_id == "place_001"
        assert "google_places" in results[0].sources

    @pytest.mark.asyncio
    async def test_skips_non_operational(self):
        """Aziende non OPERATIONAL vengono scartate."""
        search_response = _make_places_search_response([
            _make_place("Studio Chiuso", "place_001", "Via Roma 1, Torino", status="CLOSED_PERMANENTLY"),
            _make_place("Studio Aperto", "place_002", "Via Po 5, Torino, TO, Italia"),
        ])
        details_response = _make_places_details_response(_make_details())

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        # Solo una chiamata details (la seconda place)
        mock_client.get = AsyncMock(side_effect=[search_response, details_response])

        with patch("adh.agents.scout.httpx.AsyncClient", return_value=mock_client):
            results = await scout_single_sector("Studi commercialisti", "Piemonte")

        assert len(results) == 1
        assert results[0].name == "Studio Aperto"

    @pytest.mark.asyncio
    async def test_skips_wrong_region(self):
        """Aziende fuori dalla regione target vengono scartate."""
        search_response = _make_places_search_response([
            _make_place("Studio Milano", "place_001", "Via Montenapoleone 1, Milano, MI, Italia"),
            _make_place("Studio Torino", "place_002", "Via Roma 1, Torino, TO, Italia"),
        ])
        details_response = _make_places_details_response(_make_details())

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=[search_response, details_response])

        with patch("adh.agents.scout.httpx.AsyncClient", return_value=mock_client):
            results = await scout_single_sector("Studi commercialisti", "Piemonte")

        assert len(results) == 1
        assert results[0].name == "Studio Torino"

    @pytest.mark.asyncio
    async def test_deduplicates_same_name_city(self):
        """Due places con stesso nome e città → tenuto solo il primo."""
        search_response = _make_places_search_response([
            _make_place("Studio Bertoli", "place_001", "Via Roma 1, Torino, TO, Italia"),
            _make_place("Studio Bertoli", "place_002", "Via Roma 1, Torino, TO, Italia"),
        ])
        details_response = _make_places_details_response(_make_details())

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=[
            search_response,
            details_response,
            details_response,
        ])

        with patch("adh.agents.scout.httpx.AsyncClient", return_value=mock_client):
            results = await scout_single_sector("Studi commercialisti", "Piemonte")

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        """Il parametro limit deve essere rispettato."""
        places = [
            _make_place(f"Studio {i}", f"place_{i:03d}", f"Via Roma {i}, Torino, TO, Italia")
            for i in range(10)
        ]
        search_response = _make_places_search_response(places)
        details_response = _make_places_details_response(_make_details())

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        # Search + 3 details calls (limit=3)
        mock_client.get = AsyncMock(side_effect=[search_response] + [details_response] * 3)

        with patch("adh.agents.scout.httpx.AsyncClient", return_value=mock_client):
            results = await scout_single_sector("Studi commercialisti", "Piemonte", limit=3)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_list(self):
        """Google Places senza risultati → lista vuota."""
        search_response = _make_places_search_response([])

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=search_response)

        with patch("adh.agents.scout.httpx.AsyncClient", return_value=mock_client):
            results = await scout_single_sector("Studi commercialisti", "Piemonte")

        assert results == []

    @pytest.mark.asyncio
    async def test_no_website_lowers_confidence(self):
        """Azienda senza website → confidence 0.6 invece di 0.9."""
        search_response = _make_places_search_response([
            _make_place("Studio Senza Web", "place_001", "Via Roma 1, Torino, TO, Italia"),
        ])
        details_response = _make_places_details_response(
            _make_details(website=None, phone=None)
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=[search_response, details_response])

        with patch("adh.agents.scout.httpx.AsyncClient", return_value=mock_client):
            results = await scout_single_sector("Studi commercialisti", "Piemonte")

        assert len(results) == 1
        assert results[0].confidence == 0.6

    @pytest.mark.asyncio
    async def test_http_error_propagates(self):
        """Errore HTTP dalla Places API → eccezione propagata."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=Exception("Connection timeout"))

        with patch("adh.agents.scout.httpx.AsyncClient", return_value=mock_client), \
             pytest.raises(Exception, match="Connection timeout"):
            await scout_single_sector("Studi commercialisti", "Piemonte")
