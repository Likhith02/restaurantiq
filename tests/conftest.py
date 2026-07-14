"""Test setup: point the app at a throwaway SQLite file BEFORE importing it,
so tests never touch the real database (or PostgreSQL, or the Claude API)."""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["RIQ_DB_PATH"] = _tmp.name
os.environ.pop("DATABASE_URL", None)
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def token(client):
    """Log in once via the full OTP flow and reuse the token."""
    r = client.post("/api/auth/request-otp", json={"phone": "9876543210"})
    assert r.status_code == 200
    code = r.json()["demo_otp"]
    r = client.post("/api/auth/verify-otp", json={"phone": "9876543210", "code": code})
    assert r.status_code == 200
    return r.json()["token"]


@pytest.fixture(scope="session")
def auth(token):
    return {"Authorization": f"Bearer {token}"}
