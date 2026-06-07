import pytest


@pytest.mark.asyncio
async def test_list_sources_requires_auth(client):
    r = await client.get("/api/admin/calendar-sources")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_source_requires_auth(client):
    r = await client.post(
        "/api/admin/calendar-sources",
        json={"name": "Test", "ical_url": "https://example.com/cal.ics", "color": "#3b82f6"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_delete_source_requires_auth(client):
    r = await client.delete("/api/admin/calendar-sources/1")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_sources_returns_list(client, monkeypatch):
    import app.core.config as cfg
    monkeypatch.setattr(cfg.settings, "owner_password", "testpass")
    login = await client.post("/api/auth/login", json={"password": "testpass"})
    client.cookies.set("access_token", login.cookies["access_token"])

    r = await client.get("/api/admin/calendar-sources")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
