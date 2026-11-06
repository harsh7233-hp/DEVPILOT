from fastapi.testclient import TestClient

from app.main import app
from app.services.session import SESSION_COOKIE, create_session, decode_session

client = TestClient(app)

TEST_TOKEN = "gho_test_token_12345"
TEST_USER = {"id": 1, "login": "testuser", "name": "Test User", "avatar_url": ""}


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_ai_status_shape():
    """Reports AI configuration state without ever exposing the API key."""
    response = client.get("/api/health/ai")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["ai_configured"], bool)
    if data["ai_configured"]:
        assert isinstance(data["model"], str) and data["model"]
    else:
        assert data["model"] is None
    assert isinstance(data["embeddings_configured"], bool)
    assert "groq_api_key" not in str(data)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["version"] == "0.1.0"


def test_auth_me_no_cookie():
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_auth_me_invalid_cookie():
    client.cookies.set(SESSION_COOKIE, "invalid.cookie.value")
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    client.cookies.clear()


def test_auth_me_valid_cookie():
    session = create_session(TEST_TOKEN, TEST_USER)
    client.cookies.set(SESSION_COOKIE, session)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["login"] == "testuser"
    client.cookies.clear()


def test_logout():
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_repositories_no_auth():
    response = client.get("/api/repositories")
    assert response.status_code == 401


def test_session_creation_and_decode():
    session = create_session(TEST_TOKEN, TEST_USER)
    decoded = decode_session(session)
    assert decoded is not None
    assert decoded["token"] == TEST_TOKEN
    assert decoded["user"]["login"] == "testuser"


def test_session_invalid_signature():
    session = create_session(TEST_TOKEN, TEST_USER)
    parts = session.rsplit(".", 1)
    tampered = parts[0] + ".invalidsignature"
    decoded = decode_session(tampered)
    assert decoded is None
