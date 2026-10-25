import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ASSISTANT_DAILY_MESSAGE_LIMIT, ASSISTANT_REPLY_TIMEOUT_SECONDS
from app.db.models.message import Message
from app.db.models.user import User
from app.db.session import SessionLocal
from app.repositories.analytics import DEFAULT_TIMEZONE
from app.repositories.conversation import ConversationRepository
from app.repositories.memory import MemoryRepository
from app.repositories.message import MessageRepository
from app.schemas.assistant import (
    ClientContext,
    ConversationResponse,
    MemoryResponse,
    MessageListResponse,
    MessageResponse,
    ReplyError,
    ReplyResponse,
)
from app.services.assistant.memory_extractor import MemoryExtractor
from app.services.assistant.prompts import MEMORIES_PREFIX
from app.services.assistant.runner import AgentRunner, Done, ToolStarted
from app.services.errors import ConflictError, NotFoundError, TooManyRequestsError
from app.services.llm.client import TextDelta

logger = logging.getLogger(__name__)

HIDDEN_PREFIXES = ("<context>", MEMORIES_PREFIX)

_busy_conversations: set[int] = set()
_background_tasks: set[asyncio.Task] = set()


class AssistantService:

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.memories = MemoryRepository(db)

    async def create_conversation(self) -> ConversationResponse:
        conversation = await self.conversations.create(self.user_id)
        await self.db.commit()
        await self.db.refresh(conversation)
        return ConversationResponse.model_validate(conversation)

    async def list_conversations(self, limit: int, offset: int) -> list[ConversationResponse]:
        conversations = await self.conversations.list_for_user(self.user_id, limit, offset)
        return [ConversationResponse.model_validate(conversation) for conversation in conversations]

    async def delete_conversation(self, conversation_id: int) -> None:
        conversation = await self._get(conversation_id)
        if conversation.id in _busy_conversations:
            raise ConflictError("Assistant is still answering in this conversation")
        await self.conversations.delete(conversation)
        await self.db.commit()

    async def history(self, conversation_id: int, limit: int, before_id: int | None) -> MessageListResponse:
        conversation = await self._get(conversation_id)
        items = _to_chat(await self.messages.list_for_conversation(conversation.id))
        if before_id is not None:
            items = [item for item in items if item.id < before_id]
        return MessageListResponse(items=items[-limit:], has_more=len(items) > limit)

    async def reply(
        self, conversation_id: int, text: str, context: ClientContext | None,
    ) -> AsyncIterator[tuple[str, dict]]:
        conversation = await self._get(conversation_id)
        timezone = context.timezone if context and context.timezone else DEFAULT_TIMEZONE

        day_start = datetime.now(ZoneInfo(timezone)).replace(hour=0, minute=0, second=0, microsecond=0)
        if await self.messages.count_user_texts_since(self.user_id, day_start) >= ASSISTANT_DAILY_MESSAGE_LIMIT:
            raise TooManyRequestsError("Daily message limit reached")
        if conversation.id in _busy_conversations:
            raise ConflictError("Assistant is still answering in this conversation")

        _busy_conversations.add(conversation.id)
        queue: asyncio.Queue = asyncio.Queue()
        _spawn(_run_agent(self.user_id, conversation.id, text, timezone, queue))
        return _stream(queue)

    async def list_memories(self) -> list[MemoryResponse]:
        return [MemoryResponse.model_validate(memory) for memory in await self.memories.list_for_user(self.user_id)]

    async def delete_memory(self, memory_id: int) -> None:
        memory = await self.memories.get_for_user(memory_id, self.user_id)
        if memory is None:
            raise NotFoundError("Memory not found")
        await self.memories.delete(memory)
        await self.db.commit()

    async def _get(self, conversation_id: int):
        conversation = await self.conversations.get_by_id_for_user(conversation_id, self.user_id)
        if conversation is None:
            raise NotFoundError("Conversation not found")
        return conversation


async def _run_agent(user_id: int, conversation_id: int, text: str, timezone: str, queue: asyncio.Queue) -> None:
    reply, completed = "", False
    try:
        async with asyncio.timeout(ASSISTANT_REPLY_TIMEOUT_SECONDS), SessionLocal() as db:
            conversation = await ConversationRepository(db).get_by_id_for_user(conversation_id, user_id)
            user = await db.get(User, user_id)
            memories = [(memory.id, memory.text) for memory in await MemoryRepository(db).list_for_user(user_id)]
            runner = AgentRunner(
                db, user_id, conversation, timezone, owner=user.mono_name if user else None, memories=memories,
            )
            async for event in runner.run(text):
                if isinstance(event, TextDelta):
                    reply += event.text
                queue.put_nowait(_to_event(event))
        completed = True
    except TimeoutError:
        logger.warning("Assistant reply timed out in conversation %s", conversation_id)
        queue.put_nowait(("error", {"code": "timeout", "detail": "Assistant took too long to answer"}))
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError) as e:
        logger.warning("Assistant model unavailable: %s", e)
        queue.put_nowait(("error", {"code": "model_unavailable", "detail": "Assistant is temporarily unavailable"}))
    except Exception:
        logger.exception("Assistant reply failed")
        queue.put_nowait(("error", {"code": "internal", "detail": "Assistant failed to answer"}))
    finally:
        _busy_conversations.discard(conversation_id)
        queue.put_nowait(None)
    if completed:
        _spawn(_update_memories(user_id, conversation_id, text, reply))


async def _update_memories(user_id: int, conversation_id: int, text: str, reply: str) -> None:
    try:
        applied = await MemoryExtractor(user_id, conversation_id).run(text, reply)
        if applied:
            logger.info("Memories updated in conversation %s: %s", conversation_id, [name for name, _, _ in applied])
    except Exception:
        logger.exception("Memory update failed in conversation %s", conversation_id)


def _spawn(coroutine) -> None:
    task = asyncio.create_task(coroutine)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _stream(queue: asyncio.Queue) -> AsyncIterator[tuple[str, dict]]:
    while (item := await queue.get()) is not None:
        yield item


def _to_event(event) -> tuple[str, dict]:
    if isinstance(event, TextDelta):
        return "delta", {"text": event.text}
    if isinstance(event, ToolStarted):
        return "tool", {"name": event.name, "label": event.label}
    if isinstance(event, Done):
        return "done", {"message_id": event.message_id, "stop_reason": event.stop_reason}
    raise TypeError(f"Unknown agent event: {event!r}")


async def to_sse(events: AsyncIterator[tuple[str, dict]]) -> AsyncIterator[str]:
    async for name, data in events:
        yield f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def collect(events: AsyncIterator[tuple[str, dict]]) -> ReplyResponse:
    reply = ReplyResponse(text="", tools=[])
    async for name, data in events:
        if name == "delta":
            reply.text += data["text"]
        elif name == "tool":
            reply.tools.append(data["name"])
        elif name == "done":
            reply.message_id, reply.stop_reason = data["message_id"], data["stop_reason"]
        elif name == "error":
            reply.error = ReplyError(**data)
    return reply


def _to_chat(messages: list[Message]) -> list[MessageResponse]:
    items: list[MessageResponse] = []
    for message in messages:
        texts = [
            block["text"] for block in message.content
            if block.get("type") == "text" and not block["text"].startswith(HIDDEN_PREFIXES)
        ]
        if message.role not in ("user", "assistant") or not texts:
            continue
        text = "\n\n".join(texts)
        if message.role == "assistant" and items and items[-1].role == "assistant":
            text = f"{items[-1].text}\n\n{text}"
            items.pop()
        items.append(MessageResponse(id=message.id, role=message.role, text=text, created_at=message.created_at))
    return items
