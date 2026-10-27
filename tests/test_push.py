import json
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from app.schemas.device import RegisterDeviceRequest
from app.services.push import ExpoPushClient, PushService

GOOD = "ExponentPushToken[aaa]"
GONE = "ExponentPushToken[bbb]"


def test_device_token_validation():
    assert RegisterDeviceRequest(push_token=GOOD, platform="ios").platform == "ios"
    assert RegisterDeviceRequest(push_token="ExpoPushToken[x]", platform="android")
    with pytest.raises(ValidationError):
        RegisterDeviceRequest(push_token="fcm-raw-token", platform="ios")
    with pytest.raises(ValidationError):
        RegisterDeviceRequest(push_token=GOOD, platform="web")


async def test_expo_sends_silent_push_and_reports_unregistered():
    sent = []

    def handler(request):
        sent.extend(json.loads(request.content))
        return httpx.Response(200, json={"data": [
            {"status": "ok", "id": "1"},
            {"status": "error", "message": "gone", "details": {"error": "DeviceNotRegistered"}},
        ]})

    unregistered = await ExpoPushClient(httpx.MockTransport(handler)).send_silent([GOOD, GONE], {"type": "location"})
    assert unregistered == [GONE]
    assert sent[0] == {"to": GOOD, "data": {"type": "location"}, "priority": "high", "_contentAvailable": True}


async def test_expo_failure_is_not_fatal():
    client = ExpoPushClient(httpx.MockTransport(lambda request: httpx.Response(500)))
    assert await client.send_silent([GOOD], {}) == []


class FakeClient:
    def __init__(self, unregistered):
        self.unregistered = unregistered

    async def send_silent(self, tokens, data):
        return self.unregistered


def push_service(tokens, unregistered=()):
    deleted, commits = [], []

    async def list_tokens(user_id):
        return tokens

    async def delete_tokens(gone):
        deleted.extend(gone)

    async def commit():
        commits.append(1)

    service = PushService(SimpleNamespace(commit=commit), FakeClient(list(unregistered)))
    service.devices = SimpleNamespace(list_tokens=list_tokens, delete_tokens=delete_tokens)
    return service, deleted


async def test_push_service_drops_dead_tokens():
    service, deleted = push_service([GOOD, GONE], unregistered=[GONE])
    assert await service.send_silent(5, {}) is True
    assert deleted == [GONE]


async def test_push_service_without_devices():
    service, _ = push_service([])
    assert await service.send_silent(5, {}) is False
    service, _ = push_service([GONE], unregistered=[GONE])
    assert await service.send_silent(5, {}) is False
