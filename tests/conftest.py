from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.db.session import Base


@pytest.fixture(scope="session")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine) -> Session:
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionFactory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_claim_data() -> dict:
    return {
        "policy_number": "POL-TEST-001",
        "vehicle_number": "MH01AB1234",
        "incident_date": "2026-01-15",
        "incident_city": "Mumbai",
        "claim_amount": 85000.0,
        "description": "Rear-end collision at signal",
    }


@pytest.fixture
def sample_user_data() -> dict:
    return {
        "email": "adjuster@test.com",
        "full_name": "Test Adjuster",
        "password": "SecurePass123!",
        "role": "adjuster",
    }
