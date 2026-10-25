from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.repositories.analytics import DEFAULT_TIMEZONE
from app.repositories.memory import MemoryRepository
from app.services.assistant.prompts import MEMORY_PROMPT, build_memories
from app.services.assistant.tools import MEMORY_REGISTRY, ToolContext, ToolRegistry
from app.services.llm.client import Completed, LLMClient

MAX_TOKENS = 4096


class MemoryExtractor:

    def __init__(
        self,
        user_id: int,
        conversation_id: int,
        llm: LLMClient | None = None,
        registry: ToolRegistry = MEMORY_REGISTRY,
        session_factory: Callable[[], AsyncSession] = SessionLocal,
    ):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.llm = llm or LLMClient()
        self.registry = registry
        self.session_factory = session_factory

    async def run(self, user_text: str, reply: str) -> list[tuple[str, dict, bool]]:
        async with self.session_factory() as db:
            memories = [(memory.id, memory.text) for memory in await MemoryRepository(db).list_for_user(self.user_id)]
        content = (
            f"{build_memories(memories)}\n"
            f"<user_message>\n{user_text}\n</user_message>\n"
            f"<assistant_reply>\n{reply}\n</assistant_reply>"
        )

        message = None
        async for event in self.llm.stream(
            purpose="memory",
            system=MEMORY_PROMPT,
            messages=[{"role": "user", "content": content}],
            tools=self.registry.definitions,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            max_tokens=MAX_TOKENS,
            effort="medium",
        ):
            if isinstance(event, Completed):
                message = event.message

        applied = []
        for block in message.content if message else []:
            if block.type != "tool_use":
                continue
            async with self.session_factory() as db:
                _, is_error = await self.registry.run(
                    ToolContext(db, self.user_id, DEFAULT_TIMEZONE, self.conversation_id), block.name, block.input,
                )
            applied.append((block.name, block.input, not is_error))
        return applied
