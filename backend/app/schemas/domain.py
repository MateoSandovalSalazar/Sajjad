import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


def _clean_domain(v: str) -> str:
    v = v.strip().lower()
    v = v.removeprefix("https://").removeprefix("http://")
    v = v.split("/")[0].strip()
    return v


class DomainCreate(BaseModel):
    fqdn: str

    @field_validator("fqdn")
    @classmethod
    def normalize(cls, v: str) -> str:
        v = _clean_domain(v)
        if not v or "." not in v:
            raise ValueError("Enter a valid domain (e.g. example.com).")
        if len(v) > 255:
            raise ValueError("Domain is too long.")
        return v


class DomainResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    fqdn: str
    is_verified: bool
    verification_token: str
    verified_at: datetime | None
    created_at: datetime


class VerificationInstructions(BaseModel):
    fqdn: str
    verification_token: str
    dns_record_type: str = "TXT"
    dns_record_name: str
    dns_record_value: str
    instructions: str


class VerificationResult(BaseModel):
    verified: bool
    message: str
