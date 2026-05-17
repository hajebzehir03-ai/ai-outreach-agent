"""Scout Agent — trova PMI italiane via Google Places API."""

import json
import httpx
from adh.agents.state import AgentState, CompanyData, load_prompt
from adh.config.settings import settings

PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

REGION_KEYWORDS: dict[str, list[str]] = {
    "Piemonte": ["Torino", "Cuneo", "Asti", "Alessandria", "Novara", "Biella", "Vercelli", "Verbania"],
    "Lombardia": ["Milano", "Bergamo", "Brescia", "Varese", "Como", "Monza", "Lecco", "Lodi", "Cremona", "Mantova", "Pavia", "Sondrio"],
    "Veneto": ["Venezia", "Verona", "Padova", "Vicenza", "Treviso", "Rovigo", "Belluno"],
    "Emilia-Romagna": ["Bologna", "Modena", "Parma", "Reggio Emilia", "Ferrara", "Ravenna", "Forlì", "Rimini", "Piacenza"],
}


def _in_region(address: str, region: str) -> bool:
    keywords = REGION_KEYWORDS.get(region, [region])
    return any(kw.lower() in address.lower() for kw in keywords)


async def _place_details(place_id: str) -> dict:
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,website,formatted_phone_number,business_status",
        "language": "it",
        "key": settings.google_places_api_key,
    }
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(PLACES_DETAILS_URL, params=params)
        r.raise_for_status()
    return r.json().get("result", {})


async def scout_single_sector(sector_name: str, region: str, limit: int = 50) -> list[CompanyData]:
    """Cerca aziende su Google Places per settore e regione."""
    params = {
        "query": f"{sector_name} {region} Italia",
        "language": "it",
        "region": "it",
        "key": settings.google_places_api_key,
    }
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(PLACES_SEARCH_URL, params=params)
        r.raise_for_status()
    raw = r.json().get("results", [])

    results: list[CompanyData] = []
    seen: set[str] = set()  # deduplication by name+city

    for place in raw:
        if len(results) >= limit:
            break
        if place.get("business_status") != "OPERATIONAL":
            continue

        address = place.get("formatted_address", "")
        if not _in_region(address, region):
            continue

        details = await _place_details(place["place_id"])
        city = address.split(",")[0].strip()
        key = f"{place['name'].lower()}|{city.lower()}"

        if key in seen:
            continue
        seen.add(key)

        has_website = bool(details.get("website"))
        confidence = 0.9 if has_website else 0.6

        company = CompanyData(
            name=place["name"],
            website=details.get("website"),
            sector=sector_name,
            city=city,
            region=region,
            phone=details.get("formatted_phone_number"),
            google_place_id=place.get("place_id"),
            sources=["google_places"],
            confidence=confidence,
        )
        results.append(company)

    return results


def scout_node(state: AgentState) -> AgentState:
    """Valida che la company abbia i dati minimi per procedere."""
    c = state.company
    if not c:
        return state.model_copy(update={"status": "error", "error": "Nessuna company nello stato"})
    if not c.name or not c.sector or not c.region:
        return state.model_copy(update={"status": "error", "error": f"Campi obbligatori mancanti per '{c.name}'"})
    if c.confidence < 0.6:
        return state.model_copy(update={"status": "dropped", "error": f"Confidence troppo bassa: {c.confidence}"})
    return state.model_copy(update={"current_step": "researcher"})
