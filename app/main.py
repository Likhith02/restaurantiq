"""RestaurantIQ — simple analytics for restaurant owners who aren't techies.

Run with:  python -m uvicorn app.main:app --port 8010
Then open: http://localhost:8010
"""
import time
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, auth, db, insights, metrics, seed

app = FastAPI(title="RestaurantIQ")

db.init_db()
seed.ensure_demo()


# ---------- request bodies ----------

class PhoneBody(BaseModel):
    phone: str


class VerifyBody(BaseModel):
    phone: str
    code: str


class SetupBody(BaseModel):
    name: str
    rtype: str | None = None
    seats: int | None = None
    currency: str = "₹"


class EntryBody(BaseModel):
    date: str | None = None       # defaults to today
    sales: float
    customers: int | None = None
    staff_count: int | None = None
    staff_cost: float | None = None
    food_cost: float | None = None
    notes: str | None = None


class AskBody(BaseModel):
    question: str


# ---------- health ----------

@app.get("/api/health")
def health():
    """Quick status check: is the app up, and is the AI key visible to it?"""
    import os
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return {
        "ok": True,
        "database": "postgres" if db.IS_PG else "sqlite",
        "ai_key_present": bool(key),
        "ai_key_looks_valid": key.startswith("sk-ant-"),
        "ai_ready": ai.available(),
    }


# ---------- auth ----------

@app.post("/api/auth/request-otp")
def request_otp(body: PhoneBody):
    phone = auth.normalize_phone(body.phone)
    code = auth.make_otp()
    db.save_otp(phone, code, time.time() + auth.OTP_TTL_SECONDS)
    # Production: send `code` via SMS/WhatsApp here and DO NOT return it.
    print(f"[RestaurantIQ] OTP for {phone}: {code}")
    return {"ok": True, "demo_otp": code}


@app.post("/api/auth/verify-otp")
def verify_otp(body: VerifyBody):
    phone = auth.normalize_phone(body.phone)
    saved = db.pop_otp(phone)
    if not saved or saved["expires_at"] < time.time():
        raise HTTPException(400, "That code has expired. Please ask for a new one.")
    if saved["code"] != body.code.strip():
        raise HTTPException(400, "That code isn't right. Please check and try again.")
    restaurant = db.get_restaurant_by_phone(phone)
    rid = restaurant["id"] if restaurant else db.create_restaurant(phone)
    needs_setup = not (restaurant and restaurant.get("name"))
    return {"token": auth.create_token(rid), "needs_setup": needs_setup}


@app.post("/api/auth/demo")
def demo_login():
    rid = seed.ensure_demo()
    return {"token": auth.create_token(rid), "needs_setup": False}


# ---------- profile ----------

@app.get("/api/me")
def me(rid: int = Depends(auth.current_restaurant_id)):
    restaurant = db.get_restaurant(rid)
    if not restaurant:
        raise HTTPException(401, "Account not found.")
    restaurant.pop("phone", None)
    return restaurant


@app.post("/api/setup")
def setup(body: SetupBody, rid: int = Depends(auth.current_restaurant_id)):
    if not body.name.strip():
        raise HTTPException(400, "Please tell us your restaurant's name.")
    db.update_restaurant(rid, body.name.strip(), body.rtype, body.seats, body.currency)
    return {"ok": True}


# ---------- daily numbers ----------

@app.post("/api/entries")
def add_entry(body: EntryBody, rid: int = Depends(auth.current_restaurant_id)):
    if body.sales < 0:
        raise HTTPException(400, "Sales can't be negative.")
    entry_date = body.date or date.today().isoformat()
    try:
        date.fromisoformat(entry_date)
    except ValueError:
        raise HTTPException(400, "That date doesn't look right.")
    db.upsert_entry(rid, {
        "date": entry_date,
        "sales": body.sales,
        "customers": body.customers,
        "staff_count": body.staff_count,
        "staff_cost": body.staff_cost,
        "food_cost": body.food_cost,
        "notes": body.notes,
    })
    return {"ok": True}


@app.get("/api/entries")
def list_entries(days: int = 30, rid: int = Depends(auth.current_restaurant_id)):
    return db.get_entries(rid, days=min(days, 365))


# ---------- dashboard ----------

@app.get("/api/dashboard")
def dashboard(rid: int = Depends(auth.current_restaurant_id)):
    restaurant = db.get_restaurant(rid)
    cur = restaurant.get("currency") or "₹"
    entries = db.get_entries(rid, days=90)
    summary = metrics.summarize(entries)
    insight_list = insights.build(summary, cur)
    return {
        "restaurant": {"name": restaurant.get("name"), "currency": cur},
        "latest": summary["latest"],
        "week": summary["week"],
        "month": summary["month"],
        "avg_check": summary["avg_check"],
        "lights": insights.lights(summary),
        "insights": insight_list,
        "chart": summary["chart"],
        "weekdays": summary["weekdays"],
        "n_entries": summary["n_entries"],
    }


# ---------- AI advisor ----------

@app.post("/api/ask")
def ask(body: AskBody, rid: int = Depends(auth.current_restaurant_id)):
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Please type a question.")
    restaurant = db.get_restaurant(rid)
    cur = restaurant.get("currency") or "₹"
    entries = db.get_entries(rid, days=90)
    summary = metrics.summarize(entries)
    insight_list = insights.build(summary, cur)

    if ai.available():
        context = ai.build_context(restaurant, summary, insight_list, entries)
        try:
            return {"answer": ai.ask_claude(question, context), "source": "ai"}
        except Exception as exc:
            print(f"[RestaurantIQ] Claude call failed, using fallback: {exc}")
    return {
        "answer": ai.fallback_answer(question, summary, insight_list, cur),
        "source": "rules",
    }


# ---------- frontend ----------

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
