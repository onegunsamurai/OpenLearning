from .base import CamelModel


class HealthResponse(CamelModel):
    status: str
    database: str | None = None
