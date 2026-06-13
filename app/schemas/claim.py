from datetime import date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import computed_field
from pydantic import model_validator

from app.models.claim import ClaimStatus
from app.models.claim import ClaimType

# Driver-operated claim types require a valid driving licence; a parked
# vehicle (theft, natural disaster) has no driver to licence.
DRIVER_OPERATED_TYPES = (ClaimType.ACCIDENT, ClaimType.THIRD_PARTY)


class ClaimCreate(BaseModel):
    policy_number: str = Field(min_length=3, max_length=50)
    vehicle_number: str = Field(min_length=3, max_length=20)
    incident_date: date
    incident_city: str = Field(min_length=2, max_length=100)
    claim_amount: float = Field(gt=0)
    description: str = Field(min_length=10, max_length=1000)
    claim_type: ClaimType = ClaimType.ACCIDENT
    fir_number: str | None = Field(default=None, min_length=3, max_length=50)
    idv: float | None = Field(default=None, gt=0)
    driving_license_number: str | None = Field(
        default=None, min_length=5, max_length=30
    )
    license_expiry_date: date | None = None

    @model_validator(mode="after")
    def enforce_claim_type_requirements(self) -> "ClaimCreate":
        # FIR is mandatory for theft and third-party claims under the
        # standard motor claims procedure.
        if self.claim_type in (ClaimType.THEFT, ClaimType.THIRD_PARTY):
            if not self.fir_number:
                raise ValueError(
                    f"An FIR number is mandatory for {self.claim_type.value} claims"
                )
        # Theft claims settle at the vehicle's Insured Declared Value.
        if self.claim_type == ClaimType.THEFT and self.idv is None:
            raise ValueError(
                "The Insured Declared Value (IDV) is required for theft claims"
            )
        # A driver-operated claim needs the driver's licence on record;
        # its validity on the incident date is checked at policy validation.
        if self.claim_type in DRIVER_OPERATED_TYPES:
            if not self.driving_license_number or self.license_expiry_date is None:
                raise ValueError(
                    "A driving licence number and expiry date are required for "
                    f"{self.claim_type.value} claims"
                )
        return self


class ClaimStatusUpdate(BaseModel):
    status: ClaimStatus


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_number: str
    vehicle_number: str
    incident_date: date
    incident_city: str
    claim_amount: float
    description: str
    claim_type: ClaimType
    fir_number: str | None = None
    idv: float | None = None
    driving_license_number: str | None = None
    license_expiry_date: date | None = None
    adjuster_id: UUID | None = None
    claimant_id: UUID | None = None
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def intimation_delay_days(self) -> int:
        """Days between the incident and the claim being filed. Late
        intimation (commonly beyond 48 hours) is a recognised ground for
        rejection, so it is surfaced for staff scrutiny."""
        filed_on = self.created_at.date()
        return max((filed_on - self.incident_date).days, 0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def delayed_intimation(self) -> bool:
        return self.intimation_delay_days > 2
