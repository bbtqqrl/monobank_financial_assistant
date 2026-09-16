from pydantic import BaseModel


class CategorizationCandidate(BaseModel):
    slug: str
    name: str


class CategorizationResult(BaseModel):
    category_slug: str
    confidence: float
