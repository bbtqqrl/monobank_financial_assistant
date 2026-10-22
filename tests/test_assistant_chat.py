import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.assistant import SendMessageRequest
from app.services.assistant.chat_service import _to_chat, _to_sse
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


def test_sse_events():
    assert _to_sse(TextDelta("Привіт")) == 'event: delta\ndata: {"text": "Привіт"}\n\n'
    tool = _to_sse(ToolStarted("get_spending", "Рахую витрати"))
    assert tool.startswith("event: tool\n") and json.loads(tool.split("data: ")[1]) == {"name": "get_spending", "label": "Рахую витрати"}
    assert json.loads(_to_sse(Done(7, "end_turn")).split("data: ")[1]) == {"message_id": 7, "stop_reason": "end_turn"}


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
