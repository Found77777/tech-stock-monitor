"""Pydantic schemas for API responses."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class SystemStatusResponse(BaseModel):
    app_name: str
    env: str
    data_source: str


class UniverseItem(BaseModel):
    symbol: str
    name: str
    sector: str


class SignalItem(BaseModel):
    symbol: str
    signal: str
    score: float
