from datetime import datetime
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy import JSON, Text
import sqlalchemy as sa


class CompanyStatus(str, Enum):
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

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    piva: Optional[str] = Field(default=None, unique=True, index=True)
    website: Optional[str] = None
    sector: str
    region: str
    city: Optional[str] = None
    employees_est: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    decision_maker_name: Optional[str] = None
    decision_maker_role: Optional[str] = None
    decision_maker_email: Optional[str] = None
    linkedin_url: Optional[str] = None
    google_place_id: Optional[str] = Field(default=None, unique=True)
    sources: list = Field(default=[], sa_column=Column(JSON))
    status: CompanyStatus = Field(default=CompanyStatus.discovered, index=True)
    qualification_score: Optional[int] = None
    qualification_reasoning: Optional[str] = Field(default=None, sa_column=Column(Text))
    pain_signals: list = Field(default=[], sa_column=Column(JSON))
    pitch_angle: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    blacklisted_until: Optional[datetime] = None

    intel: list["CompanyIntel"] = Relationship(back_populates="company")
    messages: list["OutreachMessage"] = Relationship(back_populates="company")
