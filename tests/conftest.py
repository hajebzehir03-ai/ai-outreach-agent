"""
Fixture condivise tra tutti i test.

Pytest carica automaticamente questo file. Le funzioni decorate con @pytest.fixture
sono disponibili in tutti i test senza import esplicito.
"""

import json
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from anthropic.types import TextBlock
from sqlmodel import Session, SQLModel, create_engine


# ---------------------------------------------------------------------------
# Helpers per costruire mock di risposte LLM
# ---------------------------------------------------------------------------

def make_llm_response(payload: dict | str) -> MagicMock:
    """
    Costruisce un mock di anthropic.Message con un TextBlock reale.

    Accetta sia un dict (verrà serializzato a JSON) sia una stringa raw.
    Compatibile con extract_text() che fa isinstance(block, TextBlock).
    """
    text = json.dumps(payload) if isinstance(payload, dict) else payload
    mock = MagicMock()
    mock.content = [TextBlock(type="text", text=text)]
    return mock


# ---------------------------------------------------------------------------
# Fixture: DB in-memory SQLite per ogni test
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_db() -> Generator:
    """
    Crea un database SQLite in-memory isolato per ogni test.

    Usa StaticPool per forzare tutte le connessioni (incluse quelle
    aperte dal webhook in thread diversi) a condividere la stessa
    connessione sottostante. Senza StaticPool, ogni Session() vede
    un DB vuoto separato.
    """
    from sqlalchemy.pool import StaticPool
    from adh.models import (  # noqa: F401
        Company,
        CompanyIntel,
        OutreachMessage,
        ProcessingLog,
    )

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    yield engine

    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(in_memory_db) -> Generator[Session, None, None]:
    """
    Sessione SQLModel pronta all'uso, già linkata al DB in-memory.

    Usage:
        def test_something(db_session):
            company = Company(name="Test")
            db_session.add(company)
            db_session.commit()
    """
    with Session(in_memory_db) as session:
        yield session


# ---------------------------------------------------------------------------
# Fixture: company di esempio già nel DB
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_company(db_session: Session):
    """Crea una Company di esempio nel DB e ritorna l'oggetto con ID."""
    from adh.models import Company

    company = Company(
        name="Studio Bertoli & Associati",
        sector="Studi commercialisti",
        region="Piemonte",
        city="Torino",
        email="info@studiobertoli.it",
        decision_maker_name="Marco Bertoli",
        decision_maker_role="Socio fondatore",
        decision_maker_email="m.bertoli@studiobertoli.it",
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company