import httpx
import pytest
from app.main import HospitalRow, process_batch


@pytest.mark.asyncio
async def test_batch_creates_and_activates():
    calls = {"created": 0, "activated": 0}

    def handler(request):
        if request.method == "POST" and request.url.path == "/hospitals/":
            calls["created"] += 1
            return httpx.Response(201, json={"id": calls["created"]})
        if request.method == "PATCH" and request.url.path.endswith("/activate"):
            calls["activated"] += 1
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            self.client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler),
                base_url="https://mock.test",
            )
        async def __aenter__(self):
            return self.client
        async def __aexit__(self, *args):
            await self.client.aclose()

    result = await process_batch([
        HospitalRow(name="Hospital A", address="Address A"),
        HospitalRow(name="Hospital B", address="Address B"),
    ], client_factory=MockAsyncClient)
    assert result["total_hospitals"] == 2
    assert result["failed_hospitals"] == 0
    assert result["batch_activated"] is True
    assert calls["created"] == 2
    assert calls["activated"] == 1


@pytest.mark.asyncio
async def test_batch_is_not_activated_when_creation_fails():
    calls = {"activated": 0}

    def handler(request):
        if request.method == "POST":
            return httpx.Response(500, json={"detail": "simulated failure"})
        if request.method == "PATCH":
            calls["activated"] += 1
            return httpx.Response(200, json={})
        return httpx.Response(404)

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            self.client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler),
                base_url="https://mock.test",
            )
        async def __aenter__(self):
            return self.client
        async def __aexit__(self, *args):
            await self.client.aclose()

    result = await process_batch([
        HospitalRow(name="Hospital A", address="Address A")
    ], client_factory=MockAsyncClient)
    assert result["failed_hospitals"] == 1
    assert result["batch_activated"] is False
    assert calls["activated"] == 0
