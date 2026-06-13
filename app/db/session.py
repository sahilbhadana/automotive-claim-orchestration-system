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
    from app.models.fraud_assessment import FraudAssessment
    from app.models.garage import Garage
    from app.models.policy import Policy
    from app.models.repair_estimate import RepairEstimate
    from app.models.settlement import Settlement
    from app.models.survey import Survey
    from app.models.user import User

    # Importing the model registers its metadata before create_all runs.
    Adjuster.__table__
    AuditLog.__table__
    Claim.__table__
    ClaimDocument.__table__
    FailedTask.__table__
    FraudAssessment.__table__
    Garage.__table__
    Policy.__table__
    RepairEstimate.__table__
    Settlement.__table__
    Survey.__table__
    User.__table__
    Base.metadata.create_all(bind=engine)
    run_schema_migrations()


def _add_column_if_missing(
    inspector,
    table: str,
    column: str,
    ddl_type: str,
    default_sql: str | None = None,
) -> None:
    existing = {col["name"] for col in inspector.get_columns(table)}
    if column in existing:
        return
    ddl = f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"
    if default_sql is not None:
        ddl += f" DEFAULT {default_sql}"
    with engine.begin() as connection:
        connection.execute(text(ddl))
    logger.info("migrated: added %s.%s", table, column)


def run_schema_migrations() -> None:
    """Apply additive schema changes that create_all cannot handle.

    create_all only creates missing tables; columns added to existing
    tables must be ALTERed in. Each migration here must be idempotent.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    is_postgres = engine.dialect.name == "postgresql"
    uuid_type = "UUID" if is_postgres else "CHAR(32)"

    if "claims" in tables:
        _add_column_if_missing(inspector, "claims", "claimant_id", uuid_type)
        _add_column_if_missing(
            inspector, "claims", "claim_type", "VARCHAR(20)", "'ACCIDENT'"
        )
        _add_column_if_missing(inspector, "claims", "fir_number", "VARCHAR(50)")
        _add_column_if_missing(inspector, "claims", "idv", "NUMERIC(12, 2)")
        _add_column_if_missing(
            inspector, "claims", "driving_license_number", "VARCHAR(30)"
        )
        _add_column_if_missing(inspector, "claims", "license_expiry_date", "DATE")
        if is_postgres:
            # claim_status is a native pg enum; new workflow states must
            # be added to the type before rows can hold them.
            with engine.begin() as connection:
                for value in (
                    "VEHICLE_INSPECTION",
                    "SURVEY_REPORT_REVIEW",
                    "LEGAL_REVIEW",
                ):
                    connection.execute(
                        text(
                            f"ALTER TYPE claim_status ADD VALUE IF NOT EXISTS '{value}'"
                        )
                    )

    if "settlements" in tables:
        _add_column_if_missing(
            inspector, "settlements", "settlement_mode", "VARCHAR(20)", "'REPAIR'"
        )
        _add_column_if_missing(
            inspector,
            "settlements",
            "settlement_basis",
            "VARCHAR(20)",
            "'REIMBURSEMENT'",
        )
        _add_column_if_missing(inspector, "settlements", "garage_name", "VARCHAR(200)")
        _add_column_if_missing(
            inspector, "settlements", "assessed_amount", "NUMERIC(12, 2)"
        )
        _add_column_if_missing(
            inspector, "settlements", "depreciation_amount", "NUMERIC(12, 2)", "0"
        )
        _add_column_if_missing(
            inspector, "settlements", "excess_amount", "NUMERIC(12, 2)", "0"
        )

    if "surveys" in tables:
        _add_column_if_missing(
            inspector, "surveys", "total_loss_flagged", "BOOLEAN", "FALSE"
        )


def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
