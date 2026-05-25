"""Researcher Agent — enrichment con prompt caricato da file."""

import json
import re
from datetime import UTC, datetime
from typing import Any, cast

import httpx
from anthropic import Anthropic

from adh.agents._utils import extract_text
from adh.agents.state import (
    AgentState,
    Buyability,
    DecisionMaker,
    IntelData,
    PainSignal,
    ReviewSnippet,
    TechStack,
    load_prompt,
)
from adh.config.settings import settings

client = Anthropic(api_key=settings.anthropic_api_key)
SYSTEM_PROMPT = load_prompt("researcher")

PAIN_KEYWORDS = [
    "attesa", "lento", "nessuno risponde", "impossibile contattare",
    "non rispondono", "tempi lunghi", "disorganizzati", "mai disponibili",
    "non richiamato", "telefono staccato", "non risponde",
]


async def _fetch_text(url: str) -> tuple[str, str]:
    """Ritorna (plain_text, final_url)."""
    if not url:
        return "", ""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            text = re.sub(r"<[^>]+>", " ", r.text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:6000], str(r.url)
    except Exception:
        return "", url


async def _google_reviews(place_id: str) -> tuple[float, int, list[ReviewSnippet]]:
    if not place_id or not settings.google_places_api_key:
        return 0.0, 0, []
    params = {
        "place_id": place_id,
        "fields": "rating,user_ratings_total,reviews",
        "language": "it",
        "key": settings.google_places_api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://maps.googleapis.com/maps/api/place/details/json", params=params)
            data = r.json().get("result", {})
        snippets = [
            ReviewSnippet(
                rating=rev.get("rating", 3),
                text=rev.get("text", "")[:300],
                source="google_maps",
            )
            for rev in data.get("reviews", [])
            if any(kw in rev.get("text", "").lower() for kw in PAIN_KEYWORDS)
        ][:3]
        return data.get("rating", 0.0), data.get("user_ratings_total", 0), snippets
    except Exception:
        return 0.0, 0, []


def _llm_analyze(company_name: str, sector: str, website_text: str, website_url: str, pain_reviews: list[str]) -> dict:
    """Chiama Claude Sonnet con il system prompt del Researcher."""
    user_msg = f"""Company: {company_name}
Sector: {sector}
Website URL: {website_url}
Website text (excerpt):
{website_text[:3000]}

Negative reviews found:
{chr(10).join(f'- {r}' for r in pain_reviews) if pain_reviews else 'None found.'}

Research date: {datetime.now(UTC).isoformat()}

Produce the full JSON output as specified."""

    response = client.messages.create(
        model=settings.llm_reasoning_model,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = extract_text(response)
    # Strip markdown code fences if present
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return cast(dict[Any, Any], json.loads(raw))


async def researcher_node(state: AgentState) -> AgentState:
    """Nodo LangGraph: arricchisce la company con dati da web + LLM analysis."""
    company = state.company
    if not company:
        return state.model_copy(update={"status": "error", "error": "Company mancante"})

    website_text, website_url = await _fetch_text(company.website or "")
    rating, review_count, pain_snippets = await _google_reviews(company.google_place_id or "")

    pain_texts = [s.text for s in pain_snippets]

    try:
        data = _llm_analyze(company.name, company.sector, website_text, website_url, pain_texts)
    except Exception as e:
        return state.model_copy(update={"status": "error", "error": f"LLM researcher error: {e}"})

    # Parse pain_signals
    pain_signals = [
        PainSignal(
            signal=ps.get("signal", ""),
            evidence=ps.get("evidence", ""),
            source_url=ps.get("source_url", website_url),
            weight=int(ps.get("weight", 5)),
        )
        for ps in data.get("pain_signals", [])
    ]

    # Parse decision_makers
    decision_makers = [
        DecisionMaker(
            name=dm.get("name", ""),
            role=dm.get("role", ""),
            linkedin=dm.get("linkedin"),
            email_guessed=dm.get("email_guessed"),
            email_pattern_confidence=float(dm.get("email_pattern_confidence", 0.0)),
            source=dm.get("source", website_url),
        )
        for dm in data.get("decision_makers", [])
    ]

    buyability_raw = data.get("buyability", {})
    tech_raw = data.get("tech_stack", {})

    intel = IntelData(
        company_id=str(state.company_id or ""),
        company_name=company.name,
        research_date=datetime.now(UTC).isoformat(),
        pain_signals=pain_signals,
        decision_makers=decision_makers,
        buyability=Buyability(
            score=int(buyability_raw.get("score", 5)),
            positive_signals=buyability_raw.get("positive_signals", []),
            negative_signals=buyability_raw.get("negative_signals", []),
        ),
        tech_stack=TechStack(
            cms=tech_raw.get("cms"),
            chatbot=tech_raw.get("chatbot"),
            crm=tech_raw.get("crm"),
            other=tech_raw.get("other", []),
        ),
        review_snippets=pain_snippets,
        summary_for_writer=data.get("summary_for_writer", ""),
    )

    return state.model_copy(update={"intel": intel, "current_step": "qualifier"})
