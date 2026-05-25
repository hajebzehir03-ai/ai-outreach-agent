from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Text
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from adh.models.company import Company


class MessageStatus(StrEnum):
    draft = "draft"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    sent = "sent"
    opened = "opened"
    clicked = "clicked"
    replied = "replied"
    failed = "failed"


class ReplyIntent(StrEnum):
    interested = "interested"
    interested_later = "interested_later"
    not_now = "not_now"
    not_interested = "not_interested"
    unsubscribe = "unsubscribe"
    out_of_office = "out_of_office"
    question = "question"
    wrong_person = "wrong_person"
    other = "other"


class OutreachMessage(SQLModel, table=True):
    __tablename__ = "outreach_messages"

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)

    # Email content
    subject: str
    body: str = Field(sa_column=Column(Text))
    pitch_angle: str
    pain_signal_used: str
    sequence_step: int = Field(default=1)

    # Status tracking
    status: MessageStatus = Field(default=MessageStatus.draft, index=True)
    resend_message_id: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    opened_at: datetime | None = None
    clicked_at: datetime | None = None

    # Approval flow
    rejection_feedback: str | None = Field(default=None, sa_column=Column(Text))

    # Reply handling
    reply_received_at: datetime | None = None
    reply_intent: ReplyIntent | None = None
    reply_body: str | None = Field(default=None, sa_column=Column(Text))
    reply_draft: str | None = Field(default=None, sa_column=Column(Text))

    # Metadata
    writer_model: str | None = None
    generation_context: dict = Field(default={}, sa_column=Column(JSON))

    company: Optional["Company"] = Relationship(back_populates="messages")


class ProcessingLog(SQLModel, table=True):
    """GDPR compliance: traccia ogni trattamento dati."""

    __tablename__ = "processing_log"

    id: int | None = Field(default=None, primary_key=True)
    company_id: int | None = Field(default=None, foreign_key="companies.id")
    message_id: int | None = Field(default=None, foreign_key="outreach_messages.id")
    action: str
    legal_basis: str = Field(default="legittimo_interesse_gdpr_6_1_f")
    data_processed: list = Field(default=[], sa_column=Column(JSON))
    performed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    retention_until: datetime | None = None
    notes: str | None = None
