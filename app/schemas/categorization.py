from pydantic import BaseModel


class CategorizationCandidate(BaseModel):
    slug: str
    name: str
    kind: str
    parent_name: str | None = None


class CategorizationResult(BaseModel):
    # None when the model gave no usable answer; the caller falls back to the
    # 'unknown' category.
    category_slug: str | None
    confidence: float
