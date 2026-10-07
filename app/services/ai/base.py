from abc import ABC, abstractmethod

from app.schemas.categorization import CategorizationCandidate, CategorizationResult


class CategorizationAIClient(ABC):

    @abstractmethod
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
        ...
