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
        mcc: int | None,
        mcc_name: str | None,
        amount: int,
        counter_name: str | None,
        hints: list[str],
        candidates: list[CategorizationCandidate],
    ) -> CategorizationResult:
        return CategorizationResult(category_slug=None, confidence=0.0)
