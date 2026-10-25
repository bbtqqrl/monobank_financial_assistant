import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.assistant import SendMessageRequest
from app.services.assistant.chat_service import _to_chat, _to_event, collect, to_sse
from app.services.assistant.runner import Done, ToolStarted
from app.services.llm.client import TextDelta

NOW = datetime(2026, 10, 22, tzinfo=timezone.utc)


def row(id_, role, content):
    return SimpleNamespace(id=id_, role=role, content=content, created_at=NOW)


def test_chat_hides_context_tools_and_thinking_and_merges_turn():
    messages = [
        row(1, "user", [{"type": "text", "text": "<context>Контекст: ...</context>"}, {"type": "text", "text": "Скільки?"}]),
        row(2, "assistant", [{"type": "thinking", "thinking": "", "signature": "s"}, {"type": "text", "text": "Зараз гляну."},
                             {"type": "tool_use", "id": "t1", "name": "get_spending", "input": {}}]),
        row(3, "user", [{"type": "tool_result", "tool_use_id": "t1", "content": "{}"}]),
        row(4, "assistant", [{"type": "compaction", "content": "summary"}, {"type": "text", "text": "10 000 ₴"}]),
    ]
    chat = _to_chat(messages)
    assert [(m.id, m.role, m.text) for m in chat] == [
        (1, "user", "Скільки?"),
        (4, "assistant", "Зараз гляну.\n\n10 000 ₴"),
    ]


async def events(*items):
    for item in items:
        yield item


async def test_sse_events():
    chunks = [chunk async for chunk in to_sse(events(
        _to_event(TextDelta("Привіт")), _to_event(ToolStarted("get_spending", "Рахую витрати")), _to_event(Done(7, "end_turn")),
    ))]
    assert chunks[0] == 'event: delta\ndata: {"text": "Привіт"}\n\n'
    assert chunks[1].startswith("event: tool\n")
    assert json.loads(chunks[1].split("data: ")[1]) == {"name": "get_spending", "label": "Рахую витрати"}
    assert json.loads(chunks[2].split("data: ")[1]) == {"message_id": 7, "stop_reason": "end_turn"}


async def test_collect_merges_events_into_one_reply():
    reply = await collect(events(
        ("tool", {"name": "get_spending", "label": "Рахую витрати"}),
        ("delta", {"text": "10 "}), ("delta", {"text": "000 ₴"}),
        ("done", {"message_id": 7, "stop_reason": "end_turn"}),
    ))
    assert (reply.text, reply.tools, reply.message_id, reply.error) == ("10 000 ₴", ["get_spending"], 7, None)


async def test_collect_keeps_proposed_actions():
    action = {
        "id": 3, "action_type": "budgets", "preview": {"items": []}, "status": "pending",
        "result": None, "error": None, "expires_at": "2026-10-26T12:00:00Z",
    }
    reply = await collect(events(("action", action), ("delta", {"text": "Підтверди"})))
    assert [item.id for item in reply.actions] == [3] and reply.text == "Підтверди"


async def test_collect_keeps_error():
    reply = await collect(events(("delta", {"text": "10"}), ("error", {"code": "timeout", "detail": "x"})))
    assert reply.text == "10" and reply.error.code == "timeout" and reply.message_id is None


@pytest.mark.parametrize(
    "body",
    [{"text": "   "}, {"text": ""}, {"text": "x" * 4001}, {"text": "ok", "context": {"timezone": "Mars/Base"}}],
)
def test_invalid_messages_are_rejected(body):
    with pytest.raises(ValidationError):
        SendMessageRequest.model_validate(body)


def test_valid_message_with_timezone():
    request = SendMessageRequest.model_validate({"text": "привіт", "context": {"timezone": "Europe/Warsaw"}})
    assert request.context.timezone == "Europe/Warsaw"
