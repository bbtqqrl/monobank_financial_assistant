from abc import ABC, abstractmethod

from app.schemas.categorization import CategorizationCandidate, CategorizationResult


class CategorizationAIClient(ABC):

    @abstractmethod
    async def classify(
        self,
        description: str,
        mcc: int,
        mcc_name: str | None,
        amount: int,
        counter_name: str | None,
        candidates: list[CategorizationCandidate],
    ) -> CategorizationResult:
        ...
