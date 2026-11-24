"""Guest-session ownership and compatibility integration tests."""

import base64
import hashlib
import sqlite3

import pytest
import pytest_asyncio
import httpx2

from src.api.app import app
from src.api import routes
from src.conversations.store import ConversationStore

ORIGIN = "http://127.0.0.1:5173"


@pytest.fixture
def store(tmp_path, monkeypatch):
    store = ConversationStore(str(tmp_path / "conversations.sqlite3"))
    monkeypatch.setattr(routes, "conversation_store", store)
    monkeypatch.setattr(routes, "_ATTACHMENTS_DIR", tmp_path / "attachments")
    monkeypatch.setenv("BRANDMIND_ADMIN_TOKEN", "integration-admin-secret")
    monkeypatch.setenv("BRANDMIND_CORS_ORIGINS", ORIGIN)
    return store


@pytest_asyncio.fixture
async def client():
    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://testserver") as session:
        yield session


async def start_session(client):
    response = await client.post("/api/v1/customer/session", headers={"Origin": ORIGIN})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def write_headers(csrf):
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf}


@pytest.mark.asyncio
async def test_customer_session_is_httponly_and_reused_after_refresh(store, client):
    first = await client.post("/api/v1/customer/session", headers={"Origin": ORIGIN})
    assert first.status_code == 200
    cookie = first.cookies.get(routes.CUSTOMER_COOKIE)
    assert cookie and len(cookie) > 30
    assert routes.CUSTOMER_COOKIE not in first.text
    cookie_header = first.headers["set-cookie"].lower()
    assert "httponly" in cookie_header and "path=/api/v1" in cookie_header
    assert "samesite=lax" in cookie_header and "secure" not in cookie_header
    session_hash = hashlib.sha256(cookie.encode()).hexdigest()
    persisted = routes.conversation_store.get_customer_session(session_hash)
    assert persisted and persisted["csrf_token"] == first.json()["csrf_token"]

    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://testserver") as refreshed:
        refreshed.cookies.set(routes.CUSTOMER_COOKIE, cookie, path="/api/v1")
        second = await refreshed.post("/api/v1/customer/session", headers={"Origin": ORIGIN})
    assert second.status_code == 200
    assert second.json() == first.json()
    assert second.cookies.get(routes.CUSTOMER_COOKIE) == cookie


@pytest.mark.asyncio
async def test_conversation_is_owned_and_rejected_for_other_session(store, client):
    owner = client
    csrf = await start_session(owner)
    assert (await owner.post("/api/v1/conversations", headers=write_headers("wrong-csrf"), json={})).status_code == 403
    created = await owner.post("/api/v1/conversations", headers=write_headers(csrf), json={"customer_name": "Guest"})
    assert created.status_code == 200
    conv = created.json()
    assert "customer_session_id" not in conv
    assert store.belongs_to_customer_session(conv["id"], hashlib.sha256(owner.cookies.get(routes.CUSTOMER_COOKIE).encode()).hexdigest())

    sent = await owner.post(f"/api/v1/conversations/{conv['id']}/messages", headers=write_headers(csrf), json={"content": "Hello"})
    assert sent.status_code == 200
    assert sent.json()["reply"]
    assert (await owner.get(f"/api/v1/conversations/{conv['id']}")).status_code == 200
    assert len((await owner.get(f"/api/v1/conversations/{conv['id']}/messages")).json()) == 2
    owned_history = (await owner.get("/api/v1/customer/conversations")).json()
    assert [item["id"] for item in owned_history] == [conv["id"]]

    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://testserver") as other:
        other_csrf = await start_session(other)
        assert (await other.get("/api/v1/customer/conversations")).json() == []
        assert (await other.get(f"/api/v1/conversations/{conv['id']}")).status_code == 404
        assert (await other.get(f"/api/v1/conversations/{conv['id']}/messages")).status_code == 404
        assert (await other.post(f"/api/v1/conversations/{conv['id']}/messages", headers=write_headers(other_csrf), json={"content": "Intrude"})).status_code == 404


@pytest.mark.asyncio
async def test_attachment_access_requires_owner(store, client):
    owner = client
    csrf = await start_session(owner)
    conv = (await owner.post("/api/v1/conversations", headers=write_headers(csrf), json={})).json()
    admin = {"Authorization": "Bearer integration-admin-secret"}
    assert (await owner.post(f"/api/v1/admin/conversations/{conv['id']}/takeover", headers=admin)).status_code == 200
    image = {"name": "test.png", "media_type": "image/png", "data": base64.b64encode(b"image-bytes").decode()}
    response = await owner.post(f"/api/v1/conversations/{conv['id']}/messages", headers=write_headers(csrf), json={"attachments": [image]})
    assert response.status_code == 200
    message = (await owner.get(f"/api/v1/conversations/{conv['id']}/messages")).json()[0]
    attachment_path = message["attachments"][0]["url"]
    assert (await owner.get(f"/api/v1{attachment_path}")).status_code == 200
    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://testserver") as other:
        await start_session(other)
        assert (await other.get(f"/api/v1{attachment_path}")).status_code == 404


@pytest.mark.asyncio
async def test_csrf_required_and_admin_can_read_legacy_conversation(store, client):
    legacy = store.create(customer_name="Historical")
    store.add_message(legacy["id"], "customer", "Existing history")
    assert (await client.get(f"/api/v1/conversations/{legacy['id']}")).status_code == 401
    assert (await client.post("/api/v1/conversations", headers={"Origin": ORIGIN}, json={})).status_code == 401
    assert (await client.post("/api/v1/chat", headers={"Origin": ORIGIN}, json={"message": "Hello"})).status_code == 401
    assert (await client.post("/api/v1/escalate", headers={"Origin": ORIGIN}, json={"session_id": "caller", "reason": "help", "customer_message": "Help"})).status_code == 401
    admin = {"Authorization": "Bearer integration-admin-secret"}
    listed = await client.get("/api/v1/admin/conversations?status=all", headers=admin)
    assert listed.status_code == 200
    assert any(row["id"] == legacy["id"] for row in listed.json())
    assert (await client.get(f"/api/v1/admin/conversations/{legacy['id']}/messages", headers=admin)).json()[0]["content"] == "Existing history"


@pytest.mark.asyncio
async def test_human_takeover_and_reply_share_customer_conversation(store, client):
    csrf = await start_session(client)
    conv = (await client.post("/api/v1/conversations", headers=write_headers(csrf), json={})).json()
    admin = {"Authorization": "Bearer integration-admin-secret"}
    assert (await client.post(f"/api/v1/admin/conversations/{conv['id']}/takeover", headers=admin)).status_code == 200
    result = await client.post(f"/api/v1/conversations/{conv['id']}/messages", headers=write_headers(csrf), json={"content": "I need a person"})
    assert result.status_code == 200 and result.json()["reply"] is None
    replied = await client.post(f"/api/v1/admin/conversations/{conv['id']}/messages", headers=admin, json={"content": "A teammate is here"})
    assert replied.status_code == 200
    rows = (await client.get(f"/api/v1/conversations/{conv['id']}/messages")).json()
    assert [row["role"] for row in rows] == ["customer", "admin"]


@pytest.mark.asyncio
async def test_shared_support_account_is_required_for_dashboard_api(store, client):
    assert (await client.get("/api/v1/admin/stats")).status_code == 401
    admin = {"Authorization": "Bearer integration-admin-secret"}
    response = await client.get("/api/v1/admin/stats", headers=admin)
    assert response.status_code == 200
    assert set(response.json()) >= {"total", "open", "human_active", "ai_active"}


@pytest.mark.asyncio
async def test_production_guest_cookie_is_secure_and_none_requires_https(store, client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("BRANDMIND_CUSTOMER_COOKIE_SAMESITE", "none")
    response = await client.post("/api/v1/customer/session", headers={"Origin": ORIGIN})
    assert response.status_code == 200
    cookie_header = response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header and "secure" in cookie_header
    assert "samesite=none" in cookie_header and "path=/api/v1" in cookie_header


@pytest.mark.asyncio
async def test_production_without_cors_origins_fails_closed(store, client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("BRANDMIND_CORS_ORIGINS", raising=False)
    response = await client.post("/api/v1/customer/session", headers={"Origin": ORIGIN})
    assert response.status_code == 403


def test_sqlite_ownership_migration_preserves_legacy_rows(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as db:
        db.executescript("""
            CREATE TABLE conversations (
                id TEXT PRIMARY KEY, brand_id TEXT NOT NULL, customer_name TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '', order_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'ai_active', assigned_to TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, archived_at TEXT,
                last_message TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
                role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,
                transparency TEXT, attachments TEXT NOT NULL DEFAULT '[]'
            );
            INSERT INTO conversations(id,brand_id,customer_name,created_at,updated_at,last_message)
                VALUES('legacy-id','rlvnt','Legacy customer','2026-01-01','2026-01-01','Keep me');
            INSERT INTO messages(conversation_id,role,content,created_at)
                VALUES('legacy-id','customer','Keep this message','2026-01-01');
        """)
    migrated = ConversationStore(str(database))
    legacy = migrated.get("legacy-id")
    assert legacy and legacy["last_message"] == "Keep me"
    assert "customer_session_id" not in legacy  # The owner digest is never part of a conversation object.
    assert migrated.messages("legacy-id")[0]["content"] == "Keep this message"
    assert migrated.customer_conversations("nonexistent-session") == []
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT customer_session_id FROM conversations WHERE id='legacy-id'").fetchone()[0] is None
