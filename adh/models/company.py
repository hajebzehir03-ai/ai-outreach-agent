from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Text
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from adh.models.intel import CompanyIntel
    from adh.models.message import OutreachMessage


class CompanyStatus(StrEnum):
    discovered = "discovered"
    enriched = "enriched"
    qualified = "qualified"
    approved = "approved"
    contacted = "contacted"
    replied = "replied"
    meeting_booked = "meeting_booked"
    not_interested = "not_interested"
    blacklisted = "blacklisted"
    dropped = "dropped"


class Company(SQLModel, table=True):
    __tablename__ = "companies"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    piva: str | None = Field(default=None, unique=True, index=True)
    website: str | None = Field(default=None)
    sector: str
    region: str
    city: str | None = Field(default=None)
    employees_est: int | None = Field(default=None)
    phone: str | None = Field(default=None)
    email: str | None = Field(default=None)
    decision_maker_name: str | None = Field(default=None)
    decision_maker_role: str | None = Field(default=None)
    decision_maker_email: str | None = Field(default=None)
    linkedin_url: str | None = Field(default=None)
    google_place_id: str | None = Field(default=None, unique=True)
    sources: list = Field(default=[], sa_column=Column(JSON))
    status: CompanyStatus = Field(default=CompanyStatus.discovered, index=True)
    qualification_score: int | None = Field(default=None)
    qualification_reasoning: str | None = Field(default=None, sa_column=Column(Text))
    pain_signals: list = Field(default=[], sa_column=Column(JSON))
    pitch_angle: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    blacklisted_until: datetime | None = Field(default=None)

    intel: list["CompanyIntel"] = Relationship(back_populates="company")
    messages: list["OutreachMessage"] = Relationship(back_populates="company")
