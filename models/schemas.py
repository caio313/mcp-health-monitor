from pydantic import BaseModel
from typing import Optional


class HealthResult(BaseModel):
    url: str
    checked_at: str
    status: str
    latency_ms: Optional[float] = None
    tools_available: list[str] = []
    last_error: Optional[str] = None
    uptime_24h: Optional[float] = None


class HealthSummary(BaseModel):
    checked_at: str
    total: int
    healthy: int
    degraded: int
    unhealthy: int
    unreachable: int
    servers: list
    ecosystem_health_score: float
