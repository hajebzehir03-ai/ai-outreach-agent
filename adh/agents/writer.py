"""Writer Agent — email personalizzate con few-shot prompt e self_check JSON."""

import json
import re
from anthropic import Anthropic

from adh.agents.state import AgentState, MessageData, SelfCheck, load_prompt
from adh.config.settings import settings

client = Anthropic(api_key=settings.anthropic_api_key)
SYSTEM_PROMPT = load_prompt("writer")

# Double-check lato Python (safety net indipendente dal self_check LLM)
BANNED_IN_SUBJECT = ["ai", "gpt", "chatgpt", "automazione", "🚀", "💡", "❗", "✅", "🔥"]
BANNED_IN_BODY = [
    "rivoluzionario", "imperdibile", "garantito", "all-in-one", "sinergia",
    "soluzione innovativa", "ai di ultima generazione", "gpt", "chatgpt",
    "intelligenza artificiale generativa", "non perdere", "approfitta", "ti basterà",
    "spero questa email", "spero che questa email",
]
MAX_SUBJECT_CHARS = 60
MAX_BODY_WORDS = 140  # 120 + margine per firma


def _python_validate(subject: str, body: str) -> list[str]:
    violations = []
    if len(subject) > MAX_SUBJECT_CHARS:
        violations.append(f"subject_too_long:{len(subject)}")
    for w in BANNED_IN_SUBJECT:
        if w in subject.lower():
            violations.append(f"banned_in_subject:{w}")
    for w in BANNED_IN_BODY:
        if w in body.lower():
            violations.append(f"banned_in_body:{w}")
    if len(body.split()) > MAX_BODY_WORDS:
        violations.append(f"body_too_long:{len(body.split())}")
    return violations


def _build_user_message(state: AgentState) -> str:
    company = state.company
    intel = state.intel
    qualification = state.qualification

    dm_name = None
    dm_role = "Titolare"
    source_mention = "il vostro sito aziendale"

    if intel and intel.decision_makers:
        dm = intel.decision_makers[0]
        dm_name = dm.name
        dm_role = dm.role

    if intel and intel.pain_signals:
        src = intel.pain_signals[0].source_url
        if "indeed" in src.lower():
            source_mention = "il vostro annuncio su Indeed"
        elif "google" in src.lower():
            source_mention = "il vostro profilo Google e le recensioni recenti"
        elif "linkedin" in src.lower():
            source_mention = "il vostro profilo LinkedIn"

    evidence_bullets = "\n".join(
        f'  - "{b}"' for b in (qualification.evidence_for_writer if qualification else [])
    ) or '  - (nessun evidence disponibile)'

    follow_up_note = ""
    if state.sequence_step == 2:
        follow_up_note = "\nNOTE: This is follow-up email #1. Use a different, more concrete angle than the first email."
    elif state.sequence_step == 3:
        follow_up_note = "\nNOTE: This is the final follow-up. Keep it very short (3-4 lines). Leave the door open without insisting."

    rejection_note = ""
    if state.rejection_feedback:
        rejection_note = f"\nPREVIOUS REJECTION FEEDBACK (do NOT repeat these mistakes): {state.rejection_feedback}"

    return f"""company_name: "{company.name if company else ''}"
decision_maker_name: {f'"{dm_name}"' if dm_name else 'null'}
decision_maker_role: "{dm_role}"
selected_angle: "{qualification.selected_angle if qualification else ''}"
evidence_for_writer:
{evidence_bullets}
source_mention: "{source_mention}"
researcher_summary: "{intel.summary_for_writer if intel else ''}"
{follow_up_note}{rejection_note}

Produce the JSON output. Run self_check before returning. If self_check fails, rewrite."""


def writer_node(state: AgentState) -> AgentState:
    """Nodo LangGraph: genera email con il prompt few-shot, max 2 retry."""
    if not state.company or not state.qualification:
        return state.model_copy(update={"status": "error", "error": "Dati mancanti nel Writer"})

    if state.writer_attempts >= 2:
        return state.model_copy(
            update={"status": "error", "error": "Writer ha esaurito i retry (max 2)"}
        )

    user_msg = _build_user_message(state)

    try:
        response = client.messages.create(
            model=settings.llm_reasoning_model,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
    except Exception as e:
        return state.model_copy(
            update={
                "writer_attempts": state.writer_attempts + 1,
                "status": "error",
                "error": f"Writer LLM/parse error: {e}",
            }
        )

    subject = data.get("subject", "")
    body = data.get("body", "")
    self_check_raw = data.get("self_check", {})

    # Python safety net
    python_violations = _python_validate(subject, body)
    llm_banned = self_check_raw.get("banned_words_used", [])
    all_violations = python_violations + llm_banned

    if all_violations or not self_check_raw.get("specific_hook_present") or not self_check_raw.get("cta_concrete"):
        # Riprova: passa le violazioni come feedback
        feedback = f"Violazioni rilevate: {all_violations}. Self-check failed: {self_check_raw}"
        return state.model_copy(
            update={
                "writer_attempts": state.writer_attempts + 1,
                "rejection_feedback": feedback,
                "current_step": "writer",
            }
        )

    message = MessageData(
        subject=subject,
        body=body,
        word_count=data.get("word_count", len(body.split())),
        self_check=SelfCheck(
            specific_hook_present=bool(self_check_raw.get("specific_hook_present")),
            banned_words_used=llm_banned,
            cta_concrete=bool(self_check_raw.get("cta_concrete")),
            ps_used=bool(self_check_raw.get("ps_used")),
            estimated_personalization_score=int(self_check_raw.get("estimated_personalization_score", 0)),
        ),
        pitch_angle=state.qualification.selected_angle if state.qualification else "",
        sequence_step=state.sequence_step,
    )

    return state.model_copy(
        update={
            "message": message,
            "current_step": "approval_gate",
            "approval_status": None,
            "writer_attempts": 0,
        }
    )
