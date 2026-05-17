from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum
from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy import Text, JSON

if TYPE_CHECKING:
    from adh.models.company import Company


class MessageStatus(str, Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    sent = "sent"
    opened = "opened"
    clicked = "clicked"
    replied = "replied"
    failed = "failed"


class ReplyIntent(str, Enum):
    interested = "interested"
    not_now = "not_now"
    not_interested = "not_interested"
    unsubscribe = "unsubscribe"
    out_of_office = "out_of_office"
    question = "question"


class OutreachMessage(SQLModel, table=True):
    __tablename__ = "outreach_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)

    # Email content
    subject: str
    body: str = Field(sa_column=Column(Text))
    pitch_angle: str
    pain_signal_used: str
    sequence_step: int = Field(default=1)

    # Status tracking
    status: MessageStatus = Field(default=MessageStatus.draft, index=True)
    resend_message_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None

    # Approval flow
    rejection_feedback: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Reply handling
    reply_received_at: Optional[datetime] = None
    reply_intent: Optional[ReplyIntent] = None
    reply_body: Optional[str] = Field(default=None, sa_column=Column(Text))
    reply_draft: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Metadata
    writer_model: Optional[str] = None
    generation_context: dict = Field(default={}, sa_column=Column(JSON))

    company: Optional["Company"] = Relationship(back_populates="messages")


class ProcessingLog(SQLModel, table=True):
    """GDPR compliance: traccia ogni trattamento dati."""

    __tablename__ = "processing_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id")
    message_id: Optional[int] = Field(default=None, foreign_key="outreach_messages.id")
    action: str
    legal_basis: str = Field(default="legittimo_interesse_gdpr_6_1_f")
    data_processed: list = Field(default=[], sa_column=Column(JSON))
    performed_at: datetime = Field(default_factory=datetime.utcnow)
    retention_until: Optional[datetime] = None
    notes: Optional[str] = None
