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
        mcc: int,
        mcc_name: str | None,
        amount: int,
        counter_name: str | None,
        candidates: list[CategorizationCandidate],
    ) -> CategorizationResult:
        user_prompt = build_user_prompt(description, mcc, mcc_name, amount, counter_name, candidates)

        response = await self._client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=200,
            temperature=0,
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
            confidence = 0.0

        return CategorizationResult(category_slug=slug or "nevidome", confidence=confidence)
