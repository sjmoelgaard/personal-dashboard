import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    response = await client.post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_correct_password(client, monkeypatch):
    import app.core.config as cfg
    monkeypatch.setattr(cfg.settings, "owner_password", "testpassword")
    response = await client.post("/api/auth/login", json={"password": "testpassword"})
    assert response.status_code == 200
    assert "access_token" in response.cookies or response.json().get("ok")


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client):
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200
