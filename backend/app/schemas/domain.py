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

    # Declaración explícita de propiedad. Campo OBLIGATORIO y sin
    # valor por defecto a propósito: Pydantic no ejecuta los
    # validadores sobre los defaults, así que con `= False` bastaba
    # con omitir el campo para saltarse la comprobación entera.
    # Un consentimiento no puede tener valor por defecto.
    authorized: bool

    @field_validator("fqdn")
    @classmethod
    def normalize(cls, v: str) -> str:
        v = _clean_domain(v)
        if not v or "." not in v:
            raise ValueError("Enter a valid domain (e.g. example.com).")
        if len(v) > 255:
            raise ValueError("Domain is too long.")
        return v

    @field_validator("authorized")
    @classmethod
    def must_authorize(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Debes declarar que eres el propietario del dominio "
                "o que cuentas con autorización por escrito para "
                "analizarlo."
            )
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
