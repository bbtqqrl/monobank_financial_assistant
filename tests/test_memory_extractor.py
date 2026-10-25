from contextlib import asynccontextmanager

from pydantic import BaseModel, ConfigDict

from app.services.assistant import memory_extractor
from app.services.assistant.memory_extractor import MemoryExtractor
from app.services.assistant.tools import Tool, ToolRegistry
from tests.test_assistant_runner import TEXT_STEP, FakeLLM, message


class TextArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str


class FakeMemories:

    def __init__(self, db):
        pass

    async def list_for_user(self, user_id):
        return []


@asynccontextmanager
async def no_session():
    yield None


def make_extractor(llm, saved):
    async def remember(ctx, args):
        saved.append((ctx.user_id, ctx.conversation_id, args.text))
        return {"status": "saved"}

    registry = ToolRegistry((Tool("remember", "", "", TextArgs, remember),))
    return MemoryExtractor(5, 7, llm=llm, registry=registry, session_factory=no_session)


async def test_extractor_applies_tool_calls_with_conversation(monkeypatch):
    monkeypatch.setattr(memory_extractor, "MemoryRepository", FakeMemories)
    step = message([
        {"type": "tool_use", "id": "m1", "name": "remember", "input": {"text": "Зарплата 32 000 ₴"}},
        {"type": "tool_use", "id": "m2", "name": "remember", "input": {"bad": 1}},
    ], "tool_use")
    llm, saved = FakeLLM([step]), []
    applied = await make_extractor(llm, saved).run("я заробляю 32", "Окей")

    assert saved == [(5, 7, "Зарплата 32 000 ₴")]
    assert [(name, ok) for name, _, ok in applied] == [("remember", True), ("remember", False)]
    content = llm.calls[0]["messages"][0]["content"]
    assert content.startswith("<memories>\nПоки нічого.") and "<user_message>\nя заробляю 32\n" in content
    assert llm.calls[0]["purpose"] == "memory"


async def test_extractor_does_nothing_without_tool_calls(monkeypatch):
    monkeypatch.setattr(memory_extractor, "MemoryRepository", FakeMemories)
    saved = []
    assert await make_extractor(FakeLLM([TEXT_STEP]), saved).run("скільки на каву?", "500 ₴") == []
    assert saved == []
