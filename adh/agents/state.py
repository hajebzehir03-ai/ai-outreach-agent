from pathlib import Path

from pydantic import BaseModel


def load_prompt(name: str) -> str:
    return (Path(__file__).parent.parent / "prompts" / f"{name}.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Scout output
# ---------------------------------------------------------------------------

class CompanyData(BaseModel):
    name: str
    piva: str | None = None
    website: str | None = None
    sector: str
    subsector: str | None = None
    city: str
    region: str
    employees_estimate: str = "unknown"  # "5-10 | 10-25 | 25-50 | 50-100 | unknown"
    sources: list[str] = []
    confidence: float = 1.0
    notes: str | None = None
    # enriched during pipeline
    phone: str | None = None
    email: str | None = None
    google_place_id: str | None = None
    decision_maker_name: str | None = None
    decision_maker_role: str | None = None
    decision_maker_email: str | None = None


# ---------------------------------------------------------------------------
# Researcher output
# ---------------------------------------------------------------------------

class PainSignal(BaseModel):
    signal: str
    evidence: str
    source_url: str
    weight: int  # 1-10


class DecisionMaker(BaseModel):
    name: str
    role: str
    linkedin: str | None = None
    email_guessed: str | None = None
    email_pattern_confidence: float = 0.0
    source: str


class Buyability(BaseModel):
    score: int  # 0-10
    positive_signals: list[str] = []
    negative_signals: list[str] = []


class TechStack(BaseModel):
    cms: str | None = None
    chatbot: str | None = None
    crm: str | None = None
    other: list[str] = []


class ReviewSnippet(BaseModel):
    rating: int  # 1-5
    text: str
    source: str


class IntelData(BaseModel):
    company_id: str = ""
    company_name: str = ""
    research_date: str = ""
    pain_signals: list[PainSignal] = []
    decision_makers: list[DecisionMaker] = []
    buyability: Buyability = Buyability(score=5)
    tech_stack: TechStack = TechStack()
    review_snippets: list[ReviewSnippet] = []
    summary_for_writer: str = ""  # 3 frasi italiane → input diretto al Writer


# ---------------------------------------------------------------------------
# Qualifier output
# ---------------------------------------------------------------------------

class ScoreBreakdown(BaseModel):
    fit_icp: int = 0
    pain_signals: int = 0
    buyability: int = 0
    reachability: int = 0


class QualificationData(BaseModel):
    company_id: str = ""
    score: int = 0
    score_breakdown: ScoreBreakdown = ScoreBreakdown()
    tier: str = "drop"  # "priority | secondary | drop"
    selected_angle: str = ""
    angle_rationale: str = ""
    evidence_for_writer: list[str] = []  # 3 bullet italiani specifici → Writer
    risk_flags: list[str] = []
    do_not_contact: bool = False
    should_proceed: bool = False


# ---------------------------------------------------------------------------
# Writer output
# ---------------------------------------------------------------------------

class SelfCheck(BaseModel):
    specific_hook_present: bool = False
    banned_words_used: list[str] = []
    cta_concrete: bool = False
    ps_used: bool = False
    estimated_personalization_score: int = 0  # 0-10


class MessageData(BaseModel):
    subject: str = ""
    body: str = ""
    word_count: int = 0
    self_check: SelfCheck = SelfCheck()
    pitch_angle: str = ""
    sequence_step: int = 1
    db_message_id: int | None = None


# ---------------------------------------------------------------------------
# Reply Handler output
# ---------------------------------------------------------------------------

class ReplyExtracted(BaseModel):
    redirected_to: str | None = None
    follow_up_date: str | None = None      # ISO8601
    question: str | None = None
    objection: str | None = None
    meeting_proposal: str | None = None


class ReplyData(BaseModel):
    category: str = ""  # 9 categorie
    confidence: float = 0.0
    extracted: ReplyExtracted = ReplyExtracted()
    recommended_action: str = ""
    draft_response: str | None = None
    urgency: str = "low"  # "high | medium | low"


# ---------------------------------------------------------------------------
# Global pipeline state
# ---------------------------------------------------------------------------

class AgentState(BaseModel):
    # Identificatori
    company_id: int | None = None
    run_id: str | None = None
    sequence_step: int = 1

    # Dati pipeline
    company: CompanyData | None = None
    intel: IntelData | None = None
    qualification: QualificationData | None = None
    message: MessageData | None = None
    reply: ReplyData | None = None

    # Flow control
    current_step: str = "scout"
    status: str = "running"
    error: str | None = None

    # Approval gate
    approval_status: str | None = None   # "approved" | "rejected" | "edited"
    rejection_feedback: str | None = None
    edited_subject: str | None = None
    edited_body: str | None = None

    # Writer retry counter
    writer_attempts: int = 0

    # Sending tracking
    resend_id: str | None = None
