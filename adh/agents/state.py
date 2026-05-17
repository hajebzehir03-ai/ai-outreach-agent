from typing import Optional
from pydantic import BaseModel
from pathlib import Path


def load_prompt(name: str) -> str:
    return (Path(__file__).parent.parent / "prompts" / f"{name}.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Scout output
# ---------------------------------------------------------------------------

class CompanyData(BaseModel):
    name: str
    piva: Optional[str] = None
    website: Optional[str] = None
    sector: str
    subsector: Optional[str] = None
    city: str
    region: str
    employees_estimate: str = "unknown"  # "5-10 | 10-25 | 25-50 | 50-100 | unknown"
    sources: list[str] = []
    confidence: float = 1.0
    notes: Optional[str] = None
    # enriched during pipeline
    phone: Optional[str] = None
    email: Optional[str] = None
    google_place_id: Optional[str] = None


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
    linkedin: Optional[str] = None
    email_guessed: Optional[str] = None
    email_pattern_confidence: float = 0.0
    source: str


class Buyability(BaseModel):
    score: int  # 0-10
    positive_signals: list[str] = []
    negative_signals: list[str] = []


class TechStack(BaseModel):
    cms: Optional[str] = None
    chatbot: Optional[str] = None
    crm: Optional[str] = None
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


# ---------------------------------------------------------------------------
# Reply Handler output
# ---------------------------------------------------------------------------

class ReplyExtracted(BaseModel):
    redirected_to: Optional[str] = None
    follow_up_date: Optional[str] = None      # ISO8601
    question: Optional[str] = None
    objection: Optional[str] = None
    meeting_proposal: Optional[str] = None


class ReplyData(BaseModel):
    category: str = ""  # 9 categorie
    confidence: float = 0.0
    extracted: ReplyExtracted = ReplyExtracted()
    recommended_action: str = ""
    draft_response: Optional[str] = None
    urgency: str = "low"  # "high | medium | low"


# ---------------------------------------------------------------------------
# Global pipeline state
# ---------------------------------------------------------------------------

class AgentState(BaseModel):
    # Identificatori
    company_id: Optional[int] = None
    run_id: Optional[str] = None
    sequence_step: int = 1

    # Dati pipeline
    company: Optional[CompanyData] = None
    intel: Optional[IntelData] = None
    qualification: Optional[QualificationData] = None
    message: Optional[MessageData] = None
    reply: Optional[ReplyData] = None

    # Flow control
    current_step: str = "scout"
    status: str = "running"
    error: Optional[str] = None

    # Approval gate
    approval_status: Optional[str] = None   # "approved" | "rejected" | "edited"
    rejection_feedback: Optional[str] = None
    edited_subject: Optional[str] = None
    edited_body: Optional[str] = None

    # Writer retry counter
    writer_attempts: int = 0
