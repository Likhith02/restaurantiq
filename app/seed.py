"""Creates a demo restaurant with 90 days of realistic data so the app can be
explored instantly with the "Try the demo" button."""
import random
from datetime import date, timedelta

from . import db

DEMO_PHONE = "0000000000"

# Base sales by weekday (Mon..Sun) for a small Indian family restaurant, in ₹.
BASE = [22000, 17500, 21000, 23000, 30000, 36000, 33000]
AVG_CHECK = 260  # ₹ per customer


def ensure_demo() -> int:
    existing = db.get_restaurant_by_phone(DEMO_PHONE)
    if existing:
        return existing["id"]

    rid = db.create_restaurant(DEMO_PHONE)
    db.update_restaurant(rid, "Sri Lakshmi Family Restaurant", "Family restaurant", 48, "₹")

    rng = random.Random(42)
    today = date.today()
    for i in range(90, 0, -1):
        d = today - timedelta(days=i)
        wd = d.weekday()
        # mild upward trend over the 90 days + daily noise
        trend = 1 + (90 - i) * 0.0012
        sales = BASE[wd] * trend * rng.uniform(0.85, 1.15)
        customers = max(10, round(sales / (AVG_CHECK * rng.uniform(0.92, 1.08))))
        # deliberately overstaffed on Tuesdays/Wednesdays so the insight fires
        staff = 7 if wd in (1, 2) else (8 if wd >= 4 else 6)
        staff_cost = staff * rng.uniform(850, 950) + sales * 0.11
        food_cost = sales * rng.uniform(0.30, 0.36)
        db.upsert_entry(rid, {
            "date": d.isoformat(),
            "sales": round(sales),
            "customers": customers,
            "staff_count": staff,
            "staff_cost": round(staff_cost),
            "food_cost": round(food_cost),
            "notes": None,
        })
    return rid
