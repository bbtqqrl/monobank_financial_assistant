import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from anthropic.types.beta import BetaMessage, BetaToolUseBlock
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ASSISTANT_COMPACTION_TRIGGER_TOKENS
from app.db.models.conversation import Conversation
from app.db.session import SessionLocal
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services.assistant.prompts import SYSTEM_PROMPT, build_context
from app.services.assistant.tools import READ_REGISTRY, ToolContext, ToolRegistry
from app.services.llm.client import Completed, LLMClient, TextDelta, ToolUseStarted

MAX_STEPS = 8
TITLE_LENGTH = 60
INTERRUPTED_TEXT = "Відповідь перервано."
INTERRUPTED_TOOL_RESULT = "Interrupted before the tool finished"


@dataclass(frozen=True)
class ToolStarted:
    name: str
    label: str


@dataclass(frozen=True)
class Done:
    message_id: int
    stop_reason: str | None


AgentEvent = TextDelta | ToolStarted | Done


class AgentRunner:

    def __init__(
        self,
        db: AsyncSession,
        user_id: int,
        conversation: Conversation,
        timezone: str,
        llm: LLMClient | None = None,
        registry: ToolRegistry = READ_REGISTRY,
        session_factory: Callable[[], AsyncSession] = SessionLocal,
    ):
        self.db = db
        self.user_id = user_id
        self.conversation = conversation
        self.timezone = timezone
        self.llm = llm or LLMClient()
        self.registry = registry
        self.session_factory = session_factory
        self.messages = MessageRepository(db)
        self.conversations = ConversationRepository(db)

    async def run(self, text: str) -> AsyncIterator[AgentEvent]:
        history = _since_last_compaction(await self.messages.history(self.conversation.id))
        await self._close_interrupted_turn(history)

        if self.conversation.title is None:
            self.conversation.title = text.strip()[:TITLE_LENGTH]
        await self._append(history, "user", [
            {"type": "text", "text": f"<context>{build_context(self.timezone)}</context>"},
            {"type": "text", "text": text},
        ])
        await self.db.commit()

        for step in range(MAX_STEPS):
            is_last_step = step == MAX_STEPS - 1
            message: BetaMessage | None = None
            async for event in self.llm.stream(
                purpose="chat",
                system=SYSTEM_PROMPT,
                messages=history,
                tools=self.registry.definitions,
                tool_choice={"type": "none"} if is_last_step else None,
                user_id=self.user_id,
                conversation_id=self.conversation.id,
                compaction_trigger=ASSISTANT_COMPACTION_TRIGGER_TOKENS,
            ):
                if isinstance(event, TextDelta):
                    yield event
                elif isinstance(event, ToolUseStarted):
                    yield ToolStarted(event.name, self.registry.label(event.name))
                elif isinstance(event, Completed):
                    message = event.message

            saved = await self._append(history, "assistant", _content(message))
            tool_uses = [block for block in message.content if block.type == "tool_use"]
            if message.stop_reason != "tool_use" or not tool_uses:
                ConversationRepository.touch(self.conversation)
                await self.db.commit()
                yield Done(saved.id, message.stop_reason)
                return

            await self.db.commit()
            results = await asyncio.gather(*(self._run_tool(block) for block in tool_uses))
            await self._append(history, "user", list(results))
            await self.db.commit()

    async def _run_tool(self, block: BetaToolUseBlock) -> dict:
        async with self.session_factory() as db:
            content, is_error = await self.registry.run(
                ToolContext(db, self.user_id, self.timezone), block.name, block.input,
            )
        result = {"type": "tool_result", "tool_use_id": block.id, "content": content}
        if is_error:
            result["is_error"] = True
        return result

    async def _close_interrupted_turn(self, history: list[dict]) -> None:
        if not history:
            return
        last = history[-1]
        if last["role"] == "assistant":
            pending = [block["id"] for block in last["content"] if block.get("type") == "tool_use"]
            if not pending:
                return
            await self._append(history, "user", [
                {"type": "tool_result", "tool_use_id": tool_use_id, "content": INTERRUPTED_TOOL_RESULT, "is_error": True}
                for tool_use_id in pending
            ])
        await self._append(history, "assistant", [{"type": "text", "text": INTERRUPTED_TEXT}])

    async def _append(self, history: list[dict], role: str, content: list[dict]):
        saved = await self.messages.add(self.conversation.id, role, content)
        history.append({"role": role, "content": content})
        return saved


def _since_last_compaction(history: list[dict]) -> list[dict]:
    for index in range(len(history) - 1, -1, -1):
        message = history[index]
        if message["role"] == "assistant" and any(
            block.get("type") == "compaction" and block.get("content") for block in message["content"]
        ):
            return history[index:]
    return history


def _content(message: BetaMessage) -> list[dict]:
    content = [block.model_dump(mode="json", exclude_none=True) for block in message.content]
    return content or [{"type": "text", "text": INTERRUPTED_TEXT}]
