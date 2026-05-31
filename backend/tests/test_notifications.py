import pytest
import httpx


@pytest.mark.asyncio
async def test_send_notification_builds_correct_request(monkeypatch):
    from app.core.notifications import send_notification
    sent = {}

    async def mock_post(self, url, **kwargs):
        sent["url"] = url
        sent["data"] = kwargs.get("content")
        sent["headers"] = kwargs.get("headers", {})

        class FakeResp:
            status_code = 200
        return FakeResp()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    await send_notification("Test titel", "Test besked")
    assert "mylife" in sent["url"]
    assert sent["data"] == b"Test besked"
    assert sent["headers"].get("Title") == "Test titel"
