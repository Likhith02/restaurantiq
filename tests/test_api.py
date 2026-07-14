"""API tests covering health, auth, entries, dashboard, and the Ask fallback."""


# ---------- health ----------

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["database"] == "sqlite"  # tests always run on the temp SQLite file
    assert body["ai_ready"] is False     # no API key in tests


# ---------- auth ----------

def test_otp_rejects_invalid_phone(client):
    r = client.post("/api/auth/request-otp", json={"phone": "123"})
    assert r.status_code == 400


def test_verify_rejects_wrong_code(client):
    phone = "9998887770"
    client.post("/api/auth/request-otp", json={"phone": phone})
    r = client.post("/api/auth/verify-otp", json={"phone": phone, "code": "000000"})
    assert r.status_code == 400


def test_otp_code_is_single_use(client):
    phone = "9998887771"
    code = client.post("/api/auth/request-otp", json={"phone": phone}).json()["demo_otp"]
    first = client.post("/api/auth/verify-otp", json={"phone": phone, "code": code})
    assert first.status_code == 200
    second = client.post("/api/auth/verify-otp", json={"phone": phone, "code": code})
    assert second.status_code == 400


def test_protected_routes_require_token(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/entries").status_code == 401
    assert client.get("/api/dashboard").status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/me", headers=bad).status_code == 401


def test_demo_login(client):
    r = client.post("/api/auth/demo")
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["needs_setup"] is False


# ---------- profile ----------

def test_setup_rejects_blank_name(client, auth):
    r = client.post("/api/setup", json={"name": "   "}, headers=auth)
    assert r.status_code == 400


def test_setup_then_me(client, auth):
    r = client.post(
        "/api/setup",
        json={"name": "Test Kitchen", "rtype": "Cafe", "seats": 20, "currency": "$"},
        headers=auth,
    )
    assert r.status_code == 200
    me = client.get("/api/me", headers=auth).json()
    assert me["name"] == "Test Kitchen"
    assert me["currency"] == "$"
    assert "phone" not in me  # phone must never leak to the client


# ---------- daily entries ----------

def test_entry_rejects_negative_sales(client, auth):
    r = client.post("/api/entries", json={"sales": -5}, headers=auth)
    assert r.status_code == 400


def test_entry_rejects_bad_date(client, auth):
    r = client.post("/api/entries", json={"sales": 100, "date": "not-a-date"}, headers=auth)
    assert r.status_code == 400


def test_entry_roundtrip_and_upsert(client, auth):
    entry = {"date": "2026-07-01", "sales": 12000, "customers": 40}
    assert client.post("/api/entries", json=entry, headers=auth).status_code == 200

    # Same date again should overwrite, not duplicate.
    entry["sales"] = 15000
    assert client.post("/api/entries", json=entry, headers=auth).status_code == 200

    entries = client.get("/api/entries", headers=auth).json()
    matching = [e for e in entries if e["date"] == "2026-07-01"]
    assert len(matching) == 1
    assert matching[0]["sales"] == 15000


# ---------- dashboard ----------

def test_dashboard_shape(client, auth):
    r = client.get("/api/dashboard", headers=auth)
    assert r.status_code == 200
    body = r.json()
    for key in ("restaurant", "latest", "week", "month", "lights", "insights", "chart", "weekdays"):
        assert key in body
    assert body["restaurant"]["name"] == "Test Kitchen"


def test_demo_dashboard_has_history(client):
    token = client.post("/api/auth/demo").json()["token"]
    r = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["n_entries"] >= 80  # seeded with ~90 days of data


# ---------- AI advisor (rule-based fallback in tests) ----------

def test_ask_rejects_empty_question(client, auth):
    r = client.post("/api/ask", json={"question": "  "}, headers=auth)
    assert r.status_code == 400


def test_ask_falls_back_to_rules_without_api_key(client, auth):
    r = client.post("/api/ask", json={"question": "How can I earn more?"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "rules"
    assert body["answer"]
