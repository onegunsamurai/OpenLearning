from .base import CamelModel


class JDParseRequest(CamelModel):
    job_description: str


class JDParseResponse(CamelModel):
    skills: list[str]
    summary: str
