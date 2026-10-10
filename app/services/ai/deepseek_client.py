import json
import logging

from openai import AsyncOpenAI

from app.core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from app.schemas.categorization import CategorizationCandidate, CategorizationResult
from app.services.ai.base import CategorizationAIClient
from app.services.ai.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class DeepSeekCategorizationAIClient(CategorizationAIClient):

    def __init__(self):
        self._client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    async def classify(
        self,
        description: str,
        mcc: int | None,
        mcc_name: str | None,
        amount: int,
        currency: int,
        operation_amount: int,
        operation_currency: int,
        counter_name: str | None,
        hints: list[str],
        candidates: list[CategorizationCandidate],
    ) -> CategorizationResult:
        user_prompt = build_user_prompt(
            description=description,
            mcc_name=mcc_name,
            amount=amount,
            currency=currency,
            operation_amount=operation_amount,
            operation_currency=operation_currency,
            counter_name=counter_name,
            hints=hints,
            candidates=candidates,
        )

        response = await self._client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=300,
            temperature=0,
            extra_body={"thinking": {"type": "disabled"}},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("DeepSeek returned empty content")

        data = json.loads(content)
        slug = data.get("category_slug")
        confidence = float(data.get("confidence", 0.0))

        candidate_slugs = {c.slug for c in candidates}
        if slug not in candidate_slugs:
            logger.warning("DeepSeek returned a slug not in the candidate list: %r", slug)
            return CategorizationResult(category_slug=None, confidence=0.0)

        return CategorizationResult(category_slug=slug, confidence=confidence)
