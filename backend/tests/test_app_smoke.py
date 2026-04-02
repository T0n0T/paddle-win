from fastapi.testclient import TestClient

from app.main import app


def test_runtime_imports_available():
    import langchain  # noqa: F401
    import langgraph  # noqa: F401
    import openai  # noqa: F401
    import paddlex  # noqa: F401


def test_healthz_returns_ok():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
