from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str | None = None
    target_role: str
    experience_years: float = Field(ge=0, le=50)
    skills: list[str] = []
    locations: list[str] = []
    remote_type: list[str] = []
    posted_within_hours: int = Field(default=24, ge=1)
    min_score: int = Field(default=70, ge=0, le=100)
    experience_tolerance: float = Field(default=1.0, ge=0, le=5)
    max_results: int = Field(default=50, ge=1, le=200)
    sources: list[str] = []
    competition_max: int | None = None


class NaturalSearchRequest(BaseModel):
    query: str = Field(min_length=5, max_length=500)
    max_results: int = Field(default=50, ge=1, le=200)


class SearchResult(BaseModel):
    total: int
    results: list
    search_params: SearchRequest | None = None
    processing_time_ms: int
