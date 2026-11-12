from pydantic import BaseModel


class HospitalRow(BaseModel):
    name: str
    address: str
    phone: str | None = None
