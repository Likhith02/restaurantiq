"""Turns raw daily entries into the numbers the dashboard and insights need."""
from datetime import date, timedelta

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _d(s: str) -> date:
    return date.fromisoformat(s)


def summarize(entries: list[dict]) -> dict:
    """entries: sorted ascending by date, up to ~90 days."""
    today = date.today()
    by_date = {e["date"]: e for e in entries}

    def window(start_days_ago: int, end_days_ago: int) -> list[dict]:
        return [
            e for e in entries
            if end_days_ago <= (today - _d(e["date"])).days < start_days_ago
        ]

    last7 = window(7, 0)
    prev7 = window(14, 7)
    last30 = window(30, 0)

    latest = entries[-1] if entries else None

    def total(rows):
        return sum(r["sales"] for r in rows)

    def pct(rows, field):
        rows = [r for r in rows if r.get(field) and r["sales"]]
        if not rows:
            return None
        return sum(r[field] for r in rows) / sum(r["sales"] for r in rows)

    # average spend per customer over last 30 days
    with_cust = [r for r in last30 if r.get("customers")]
    avg_check = (
        sum(r["sales"] for r in with_cust) / sum(r["customers"] for r in with_cust)
        if with_cust else None
    )

    # weekday averages over the full history
    weekday_rows: dict[int, list[float]] = {i: [] for i in range(7)}
    for e in entries:
        weekday_rows[_d(e["date"]).weekday()].append(e["sales"])
    weekdays = [
        {"name": WEEKDAYS[i], "avg": (sum(v) / len(v)) if v else None, "n": len(v)}
        for i, v in weekday_rows.items()
    ]
    sampled = [w for w in weekdays if w["n"] >= 2]
    overall_avg = (
        sum(w["avg"] * w["n"] for w in sampled) / sum(w["n"] for w in sampled)
        if sampled else None
    )
    worst = min(sampled, key=lambda w: w["avg"]) if sampled else None
    best = max(sampled, key=lambda w: w["avg"]) if sampled else None

    week_total = total(last7)
    prev_total = total(prev7)
    change_pct = ((week_total - prev_total) / prev_total * 100) if prev_total else None

    chart = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        e = by_date.get(d.isoformat())
        chart.append({"date": d.isoformat(), "sales": e["sales"] if e else 0})

    return {
        "latest": latest,
        "week": {"total": week_total, "prev_total": prev_total, "change_pct": change_pct, "days": len(last7)},
        "month": {"total": total(last30), "days": len(last30)},
        "staff_pct": pct(last30, "staff_cost"),
        "food_pct": pct(last30, "food_cost"),
        "avg_check": avg_check,
        "weekdays": weekdays,
        "overall_day_avg": overall_avg,
        "worst_day": worst,
        "best_day": best,
        "chart": chart,
        "n_entries": len(entries),
    }
