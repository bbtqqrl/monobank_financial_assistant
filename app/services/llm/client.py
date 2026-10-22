import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from anthropic import AsyncAnthropic, omit
from anthropic.types import MessageParam, ToolChoiceParam, ToolParam
from anthropic.types.beta import BetaMessage

from app.core.config import ANTHROPIC_API_KEY, ASSISTANT_MAX_TOKENS, ASSISTANT_MODEL
from app.db.models.llm_usage import LLMUsage
from app.db.session import SessionLocal
from app.repositories.llm_usage import LLMUsageRepository
from app.services.llm.pricing import cost_usd

logger = logging.getLogger(__name__)

CACHE_CONTROL = {"type": "ephemeral"}
COMPACTION_BETA = "compact-2026-01-12"

Effort = Literal["low", "medium", "high", "xhigh", "max"]


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class ToolUseStarted:
    tool_use_id: str
    name: str


@dataclass(frozen=True)
class Completed:
    message: BetaMessage


LLMEvent = TextDelta | ToolUseStarted | Completed


class LLMClient:

    def __init__(self, client: AsyncAnthropic | None = None):
        self._client = client or AsyncAnthropic(api_key=ANTHROPIC_API_KEY, max_retries=2, timeout=60)

    async def stream(
        self,
        *,
        purpose: str,
        system: str,
        messages: list[MessageParam],
        tools: list[ToolParam] | None = None,
        tool_choice: ToolChoiceParam | None = None,
        user_id: int | None = None,
        conversation_id: int | None = None,
        model: str = ASSISTANT_MODEL,
        max_tokens: int = ASSISTANT_MAX_TOKENS,
        effort: Effort = "low",
        compaction_trigger: int | None = None,
    ) -> AsyncIterator[LLMEvent]:
        started = time.monotonic()
        stream = None
        message: BetaMessage | None = None
        context_management = omit
        if compaction_trigger is not None:
            context_management = {"edits": [{
                "type": "compact_20260112",
                "trigger": {"type": "input_tokens", "value": compaction_trigger},
            }]}
        try:
            async with self._client.beta.messages.stream(
                betas=[COMPACTION_BETA],
                context_management=context_management,
                model=model,
                max_tokens=max_tokens,
                system=[{"type": "text", "text": system, "cache_control": CACHE_CONTROL}],
                messages=messages,
                tools=tools or omit,
                tool_choice=tool_choice or omit,
                output_config={"effort": effort},
                cache_control=CACHE_CONTROL,
            ) as stream:
                async for event in stream:
                    if event.type == "text":
                        yield TextDelta(event.text)
                    elif event.type == "content_block_start" and event.content_block.type == "tool_use":
                        yield ToolUseStarted(event.content_block.id, event.content_block.name)
                message = await stream.get_final_message()
        finally:
            await self._record(
                message or _snapshot(stream),
                request_id=stream.request_id if stream else None,
                purpose=purpose,
                model=model,
                user_id=user_id,
                conversation_id=conversation_id,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        yield Completed(message)

    async def _record(
        self,
        message: BetaMessage | None,
        *,
        request_id: str | None,
        purpose: str,
        model: str,
        user_id: int | None,
        conversation_id: int | None,
        duration_ms: int,
    ) -> None:
        if message is None:
            return
        iterations = message.usage.iterations or [message.usage]
        input_tokens = sum(item.input_tokens or 0 for item in iterations)
        output_tokens = sum(item.output_tokens or 0 for item in iterations)
        cache_read = sum(item.cache_read_input_tokens or 0 for item in iterations)
        cache_write = sum(item.cache_creation_input_tokens or 0 for item in iterations)
        cost = sum(
            cost_usd(
                model,
                item.input_tokens or 0,
                item.output_tokens or 0,
                item.cache_read_input_tokens or 0,
                item.cache_creation_input_tokens or 0,
            )
            for item in iterations
        )
        if any(getattr(item, "type", None) == "compaction" for item in iterations):
            logger.info("Conversation %s compacted", conversation_id)
        try:
            async with SessionLocal() as db:
                LLMUsageRepository(db).add(LLMUsage(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    purpose=purpose,
                    model=model,
                    request_id=request_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_tokens=cache_read,
                    cache_write_tokens=cache_write,
                    cost_usd=cost,
                    stop_reason=message.stop_reason,
                    duration_ms=duration_ms,
                ))
                await db.commit()
        except Exception:
            logger.exception("Failed to record LLM usage")


def _snapshot(stream) -> BetaMessage | None:
    if stream is None:
        return None
    try:
        return stream.current_message_snapshot
    except Exception:
        return None
