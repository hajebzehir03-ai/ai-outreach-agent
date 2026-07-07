"""Qualifier Agent — scoring 0-100 con formula esplicita e 8 angoli di pitch."""

import json
import re

from anthropic import Anthropic

from adh.agents._utils import extract_text
from adh.agents.state import (
    AgentState,
    QualificationData,
    ScoreBreakdown,
    load_prompt,
)
from adh.config.settings import settings

client = Anthropic(api_key=settings.anthropic_api_key)
SYSTEM_PROMPT = load_prompt("qualifier")

ICP_HIGH_SECTORS = {
    "Studi commercialisti", "Studi legali", "Agenzie immobiliari",
    "Agenzie di marketing", "E-commerce moda/arredamento",
}
ICP_PRIORITY_REGIONS = {"Piemonte", "Lombardia", "Veneto", "Emilia-Romagna"}
ICP_PRIORITY_SIZE = {"5-10", "10-25", "25-50"}


def qualifier_node(state: AgentState) -> AgentState:
    """Nodo LangGraph: chiama Claude con il prompt qualifier e parsifica il JSON."""
    company = state.company
    intel = state.intel

    if not company or not intel:
        return state.model_copy(update={"status": "error", "error": "Company o Intel mancante"})

    # Costruiamo l'input per il qualifier LLM
    dm_info = ""
    if intel.decision_makers:
        dm = intel.decision_makers[0]
        email_info = f"email guessed: {dm.email_guessed} (confidence {dm.email_pattern_confidence:.0%})" if dm.email_guessed else "nessuna email"
        dm_info = f"{dm.name} — {dm.role} — {email_info}"

    pain_summary = "\n".join(
        f"- [{ps.weight}/10] {ps.signal}: {ps.evidence[:100]}"
        for ps in intel.pain_signals
    ) or "Nessun segnale trovato."

    user_msg = f"""Company ID: {state.company_id or 'unknown'}
Company: {company.name}
Sector: {company.sector}
Region: {company.region}
Employees estimate: {company.employees_estimate}
Website: {company.website or 'N/A'}

Pain signals from researcher:
{pain_summary}

Buyability score: {intel.buyability.score}/10
Positive: {', '.join(intel.buyability.positive_signals) or 'none'}
Negative: {', '.join(intel.buyability.negative_signals) or 'none'}

Tech stack: cms={intel.tech_stack.cms}, chatbot={intel.tech_stack.chatbot}, crm={intel.tech_stack.crm}

Decision maker: {dm_info or 'Not found'}
Generic email available: {company.email or 'No'}

Researcher summary:
{intel.summary_for_writer}

Produce the full JSON output as specified."""

    try:
        response = client.messages.create(
            model=settings.llm_cheap_model,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = extract_text(response)
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
    except Exception as e:
        return state.model_copy(update={"status": "error", "error": f"Qualifier LLM error: {e}"})

    breakdown_raw = data.get("score_breakdown", {})
    score = int(data.get("score", 0))
    tier = data.get("tier", "drop")
    do_not_contact = bool(data.get("do_not_contact", False))
    evidence = data.get("evidence_for_writer", [])

    # Regola hard: < 3 evidence bullets → drop
    if len(evidence) < 3 and score >= 60:
        score = min(score, 59)
        tier = "drop"

    qualification = QualificationData(
        company_id=str(state.company_id or ""),
        score=score,
        score_breakdown=ScoreBreakdown(
            fit_icp=int(breakdown_raw.get("fit_icp", 0)),
            pain_signals=int(breakdown_raw.get("pain_signals", 0)),
            buyability=int(breakdown_raw.get("buyability", 0)),
            reachability=int(breakdown_raw.get("reachability", 0)),
        ),
        tier=tier,
        selected_angle=data.get("selected_angle", ""),
        angle_rationale=data.get("angle_rationale", ""),
        evidence_for_writer=evidence,
        risk_flags=data.get("risk_flags", []),
        do_not_contact=do_not_contact,
        should_proceed=score >= 60 and not do_not_contact and tier != "drop",
    )

    return state.model_copy(
        update={
            "qualification": qualification,
            "current_step": "writer" if qualification.should_proceed else "drop",
        }
    )
