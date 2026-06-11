import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    from app.models.adjuster import Adjuster
    from app.models.audit import AuditLog
    from app.models.claim import Claim
    from app.models.document import ClaimDocument
    from app.models.failed_task import FailedTask
    from app.models.garage import Garage
    from app.models.policy import Policy
    from app.models.repair_estimate import RepairEstimate
    from app.models.settlement import Settlement
    from app.models.user import User

    # Importing the model registers its metadata before create_all runs.
    Adjuster.__table__
    AuditLog.__table__
    Claim.__table__
    ClaimDocument.__table__
    FailedTask.__table__
    Garage.__table__
    Policy.__table__
    RepairEstimate.__table__
    Settlement.__table__
    User.__table__
    Base.metadata.create_all(bind=engine)
    run_schema_migrations()


def run_schema_migrations() -> None:
    """Apply additive schema changes that create_all cannot handle.

    create_all only creates missing tables; columns added to existing
    tables must be ALTERed in. Each migration here must be idempotent.
    """
    inspector = inspect(engine)
    if "claims" not in inspector.get_table_names():
        return

    claim_columns = {column["name"] for column in inspector.get_columns("claims")}
    if "claimant_id" not in claim_columns:
        column_type = "UUID" if engine.dialect.name == "postgresql" else "CHAR(32)"
        with engine.begin() as connection:
            connection.execute(
                text(f"ALTER TABLE claims ADD COLUMN claimant_id {column_type}")
            )
        logger.info("migrated: added claims.claimant_id")


def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
