from pydantic import BaseModel


class InstitutionProfile(BaseModel):
    name: str
    institution_type: str
    size_notes: str = ""
    services: list[str] = []