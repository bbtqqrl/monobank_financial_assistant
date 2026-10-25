import copy
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from anthropic.types.beta import BetaMessage
from pydantic import BaseModel, ConfigDict

from app.services.assistant.prompts import build_context, build_memories, reply_language
from app.services.assistant.runner import (
    INTERRUPTED_TEXT,
    MAX_STEPS,
    AgentRunner,
    Done,
    ToolStarted,
    _since_last_compaction,
)
from app.services.assistant.tools import Tool, ToolRegistry
from app.services.llm.client import Completed, TextDelta, ToolUseStarted


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


async def spending(ctx, args):
    return {"total": 1000000}


REGISTRY = ToolRegistry((Tool("get_spending", "Рахую витрати", "", NoArgs, spending),))


def message(content: list[dict], stop_reason: str) -> BetaMessage:
    return BetaMessage.model_validate({
        "id": "msg", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
        "content": content, "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    })


TOOL_STEP = message([{"type": "tool_use", "id": "t1", "name": "get_spending", "input": {}}], "tool_use")
TEXT_STEP = message([{"type": "text", "text": "10 000 ₴"}], "end_turn")


class FakeLLM:

    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []

    async def stream(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        for block in step.content:
            if block.type == "text":
                yield TextDelta(block.text)
            elif block.type == "tool_use":
                yield ToolUseStarted(block.id, block.name)
        yield Completed(step)


class FakeMessages:

    def __init__(self, stored=None):
        self.stored = stored or []

    async def history(self, conversation_id):
        return copy.deepcopy(self.stored)

    async def add(self, conversation_id, role, content):
        self.stored.append({"role": role, "content": copy.deepcopy(content)})
        return SimpleNamespace(id=len(self.stored))


class FakeDB:

    async def commit(self):
        pass


@asynccontextmanager
async def no_session():
    yield None


def make_runner(llm, stored=None):
    conversation = SimpleNamespace(id=1, title=None, updated_at=None)
    runner = AgentRunner(FakeDB(), 1, conversation, "Europe/Kyiv", llm=llm, registry=REGISTRY, session_factory=no_session)
    runner.messages = FakeMessages(stored)
    return runner


async def collect(runner, text):
    return [event async for event in runner.run(text)]


async def test_tool_loop_runs_tool_and_answers():
    llm = FakeLLM([TOOL_STEP, TEXT_STEP])
    runner = make_runner(llm)
    events = await collect(runner, "Скільки я витратив?")

    assert events == [ToolStarted("get_spending", "Рахую витрати"), TextDelta("10 000 ₴"), Done(4, "end_turn")]
    assert runner.conversation.title == "Скільки я витратив?"
    tool_result = llm.calls[1]["messages"][-1]["content"][0]
    assert tool_result == {"type": "tool_result", "tool_use_id": "t1", "content": '{"total":10000.0}'}


async def test_user_message_carries_context_block():
    llm = FakeLLM([TEXT_STEP])
    await collect(make_runner(llm), "привіт")
    memories_block, first_block, text_block = llm.calls[0]["messages"][0]["content"]
    assert memories_block["text"].startswith("<memories>")
    assert first_block["text"].startswith("<context>") and "Europe/Kyiv" in first_block["text"]
    assert text_block == {"type": "text", "text": "привіт"}


async def test_memories_are_sent_once_until_they_change_and_tools_get_conversation():
    seen = []

    async def spy(ctx, args):
        seen.append(ctx.conversation_id)
        return {}

    memories = "<memories>\n[3] Зарплата 32 000 ₴ на іншу картку\n</memories>"
    llm = FakeLLM([TOOL_STEP, TEXT_STEP, TEXT_STEP, TEXT_STEP])
    runner = make_runner(llm)
    runner.registry = ToolRegistry((Tool("get_spending", "Рахую витрати", "", NoArgs, spy),))
    runner.memories = [(3, "Зарплата 32 000 ₴ на іншу картку")]
    await collect(runner, "привіт")
    await collect(runner, "ще")
    runner.memories = [(3, "Зарплата 38 000 ₴ на іншу картку")]
    await collect(runner, "і ще")

    first, second, third = (call["messages"][-1]["content"] for call in (llm.calls[0], llm.calls[2], llm.calls[3]))
    assert first[0]["text"] == memories and first[1]["text"].startswith("<context>")
    assert second[0]["text"].startswith("<context>")
    assert "38 000" in third[0]["text"]
    assert all(call["system"] == llm.calls[0]["system"] for call in llm.calls)
    assert seen == [1]


def test_empty_memories_block():
    assert build_memories([]) == "<memories>\nПоки нічого.\n</memories>"


async def test_interrupted_tool_call_is_closed_before_next_turn():
    stored = [
        {"role": "user", "content": [{"type": "text", "text": "питання"}]},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t9", "name": "get_spending", "input": {}}]},
    ]
    llm = FakeLLM([TEXT_STEP])
    await collect(make_runner(llm, stored), "ще раз")

    roles = [m["role"] for m in llm.calls[0]["messages"]]
    assert roles == ["user", "assistant", "user", "assistant", "user"]
    assert llm.calls[0]["messages"][2]["content"][0]["tool_use_id"] == "t9"
    assert llm.calls[0]["messages"][3]["content"][0]["text"] == INTERRUPTED_TEXT


async def test_failed_turn_without_answer_gets_placeholder():
    stored = [{"role": "user", "content": [{"type": "text", "text": "питання"}]}]
    llm = FakeLLM([TEXT_STEP])
    await collect(make_runner(llm, stored), "ще раз")
    assert [m["role"] for m in llm.calls[0]["messages"]] == ["user", "assistant", "user"]


async def test_last_step_disables_tools():
    llm = FakeLLM([TOOL_STEP] * (MAX_STEPS - 1) + [TEXT_STEP])
    events = await collect(make_runner(llm), "цикл")
    assert len(llm.calls) == MAX_STEPS
    assert llm.calls[-1]["tool_choice"] == {"type": "none"}
    assert all(call["tool_choice"] is None for call in llm.calls[:-1])
    assert isinstance(events[-1], Done)


def test_history_is_sent_from_last_compaction():
    history = [
        {"role": "user", "content": [{"type": "text", "text": "a"}]},
        {"role": "assistant", "content": [{"type": "compaction", "content": "summary 1"}, {"type": "text", "text": "b"}]},
        {"role": "user", "content": [{"type": "text", "text": "c"}]},
        {"role": "assistant", "content": [{"type": "compaction", "content": "summary 2"}, {"type": "text", "text": "d"}]},
        {"role": "user", "content": [{"type": "text", "text": "e"}]},
    ]
    assert _since_last_compaction(history) == history[3:]


def test_failed_compaction_does_not_trim_history():
    history = [
        {"role": "user", "content": [{"type": "text", "text": "a"}]},
        {"role": "assistant", "content": [{"type": "compaction"}, {"type": "text", "text": "b"}]},
    ]
    assert _since_last_compaction(history) == history


def test_context_uses_user_timezone():
    now = datetime(2026, 10, 22, 23, 30, tzinfo=ZoneInfo("UTC"))
    assert build_context("Europe/Kyiv", "Скільки?", now) == "Now: 2026-10-23 02:30, Friday, user timezone Europe/Kyiv."
    assert build_context("Europe/Kyiv", "Скільки?", now, owner="Іван Петренко").endswith(" Card owner: Іван Петренко.")


@pytest.mark.parametrize(
    ("text", "language"),
    [("Скільки я витратив?", None), ("How much did I spend?", "English"), ("Ile wydałem?", "Polish"),
     ("Скільки на Netflix?", None), ("2026-09?", None)],
)
def test_reply_language_hint(text, language):
    assert reply_language(text) == language
