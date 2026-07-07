from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Text
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from adh.models.company import Company


class CompanyIntel(SQLModel, table=True):
    __tablename__ = "company_intel"

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)

    # Website analysis
    website_title: str | None = None
    website_description: str | None = Field(default=None, sa_column=Column(Text))
    website_tech_stack: list = Field(default=[], sa_column=Column(JSON))
    website_has_chatbot: bool = False
    website_has_contact_form: bool = False
    website_has_autoresponder: bool = False
    website_last_modified: datetime | None = None
    website_age_years: float | None = None

    # Google reviews
    google_rating: float | None = None
    google_review_count: int | None = None
    google_pain_reviews: list = Field(default=[], sa_column=Column(JSON))

    # Job listings (pain signals)
    job_listings: list = Field(default=[], sa_column=Column(JSON))

    # LinkedIn
    linkedin_last_post_days: int | None = None
    linkedin_followers: int | None = None

    # Recent news
    recent_news: list = Field(default=[], sa_column=Column(JSON))

    # Raw text for embedding (concatenation of all intel)
    raw_intel_text: str | None = Field(default=None, sa_column=Column(Text))

    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    company: Optional["Company"] = Relationship(back_populates="intel")
