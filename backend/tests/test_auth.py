import pytest
import app.core.config as cfg


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    response = await client.post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_correct_password(client, monkeypatch):
    monkeypatch.setattr(cfg.settings, "owner_password", "testpassword")
    response = await client.post("/api/auth/login", json={"password": "testpassword"})
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client, monkeypatch):
    monkeypatch.setattr(cfg.settings, "owner_password", "testpassword")
    login = await client.post("/api/auth/login", json={"password": "testpassword"})
    assert "access_token" in login.cookies
    # httpx doesn't forward secure cookies via per-request cookies=; set on the client
    client.cookies.set("access_token", login.cookies["access_token"])
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {"user": "owner"}
    client.cookies.clear()


@pytest.mark.asyncio
async def test_logout_clears_session(client, monkeypatch):
    monkeypatch.setattr(cfg.settings, "owner_password", "testpassword")
    # Log in
    login = await client.post("/api/auth/login", json={"password": "testpassword"})
    assert "access_token" in login.cookies
    # Log out
    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 200
    # /me should now return 401 (no valid cookie)
    me = await client.get("/api/auth/me")
    assert me.status_code == 401
