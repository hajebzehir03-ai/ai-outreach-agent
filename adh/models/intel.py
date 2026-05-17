from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy import Text, JSON

if TYPE_CHECKING:
    from adh.models.company import Company


class CompanyIntel(SQLModel, table=True):
    __tablename__ = "company_intel"

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", index=True)

    # Website analysis
    website_title: Optional[str] = None
    website_description: Optional[str] = Field(default=None, sa_column=Column(Text))
    website_tech_stack: list = Field(default=[], sa_column=Column(JSON))
    website_has_chatbot: bool = False
    website_has_contact_form: bool = False
    website_has_autoresponder: bool = False
    website_last_modified: Optional[datetime] = None
    website_age_years: Optional[float] = None

    # Google reviews
    google_rating: Optional[float] = None
    google_review_count: Optional[int] = None
    google_pain_reviews: list = Field(default=[], sa_column=Column(JSON))

    # Job listings (pain signals)
    job_listings: list = Field(default=[], sa_column=Column(JSON))

    # LinkedIn
    linkedin_last_post_days: Optional[int] = None
    linkedin_followers: Optional[int] = None

    # Recent news
    recent_news: list = Field(default=[], sa_column=Column(JSON))

    # Raw text for embedding (concatenation of all intel)
    raw_intel_text: Optional[str] = Field(default=None, sa_column=Column(Text))

    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    company: Optional["Company"] = Relationship(back_populates="intel")
