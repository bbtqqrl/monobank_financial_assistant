from app.schemas.categorization import CategorizationCandidate, CategorizationResult
from app.services.ai.base import CategorizationAIClient


class MockCategorizationAIClient(CategorizationAIClient):
    """Placeholder until a real provider (DeepSeek) is wired in.

    Always returns confidence 0.0 so every transaction falls into the
    manual-review path instead of silently caching a wrong AI guess.
    """

    async def classify(
        self,
        description: str,
        mcc: int,
        mcc_name: str | None,
        amount: int,
        counter_name: str | None,
        candidates: list[CategorizationCandidate],
    ) -> CategorizationResult:
        fallback = next((c for c in candidates if c.slug == "nevidome"), candidates[0])
        return CategorizationResult(category_slug=fallback.slug, confidence=0.0)
