from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    results: list[T]
    total: int


class Stop(BaseModel):
    stop_id: int
    stop_name: str | None
    lat: float | None
    lon: float | None


class Community(BaseModel):
    community_num: int
    community_name: str | None


class Route(BaseModel):
    route_name: str
    route_type: str | None
    stop_count: int


class Coverage(BaseModel):
    community_num: int
    community_name: str | None
    population: int
    accessible_population: int
    geographic_coverage: float


class PassengerRow(BaseModel):
    stop_id: int
    month: str
    direction: str
    count: int
    placeholder: bool


class Kpis(BaseModel):
    stops: int
    communities: int
    routes: int
    coverage_avg: float | None
    coverage_median: float | None
    population: int
    accessible_population: int
    passengers_placeholder: bool
