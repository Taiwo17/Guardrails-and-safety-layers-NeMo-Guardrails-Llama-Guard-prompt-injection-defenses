from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["guardrails_enabled"] is True


def test_chat_endpoint_returns_response(monkeypatch):
    async def mock_generate(message: str) -> dict:
        return {
            "response": "Docker containers package applications and dependencies.",
            "security_decision": "ALLOWED"
        }

    monkeypatch.setattr(
        "app.main.generate_guardrailed_response",
        mock_generate
    )

    response = client.post(
        "/chat",
        json={"message": "What are Docker containers"}
    )

    assert response.status_code == 200
    assert response.json()["response"] == (
        "Docker containers package applications and dependencies."
    )
    assert response.json()["security_decision"] == "ALLOWED"


def test_chat_endpoint_rejects_empty_message():
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422


def test_chat_endpoint_handles_processing_error(monkeypatch):
    async def mock_generate(message: str) -> dict:
        raise RuntimeError("Simulated processing failure")

    monkeypatch.setattr(
        "app.main.generate_guardrailed_response",
        mock_generate
    )

    response = client.post(
        "/chat",
        json={"message": "Explain Docker"}
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to process the request."