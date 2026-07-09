"""Plain-language insights. Money and people, not jargon.

Every insight: level ("good" | "watch" | "act"), title, detail, action.
Written so a first-time smartphone user understands it in one read.
"""

STAFF_TARGET = 0.30   # healthy staff pay as a share of sales
FOOD_TARGET = 0.33    # healthy groceries/ingredients share of sales


def _money(cur: str, amount: float) -> str:
    return f"{cur}{amount:,.0f}"


def build(s: dict, cur: str) -> list[dict]:
    out: list[dict] = []
    month_sales = s["month"]["total"]

    # --- Staff pay ---
    if s["staff_pct"] is not None and month_sales:
        pct = s["staff_pct"]
        spent = pct * month_sales
        if pct > STAFF_TARGET + 0.04:
            extra = spent - STAFF_TARGET * month_sales
            worst = s["worst_day"]["name"] + "s" if s["worst_day"] else "your quietest days"
            out.append({
                "level": "act",
                "key": "staff",
                "title": "Staff pay is higher than it should be",
                "detail": (
                    f"In the last 30 days you paid {_money(cur, spent)} to staff — "
                    f"that's {pct*100:.0f}% of everything you earned. "
                    f"A healthy level is about 30%. Right now you're spending roughly "
                    f"{_money(cur, extra)} more than that."
                ),
                "action": f"Try one fewer person on {worst}. That alone could save most of the difference.",
            })
        elif pct > STAFF_TARGET + 0.01:
            out.append({
                "level": "watch",
                "key": "staff",
                "title": "Staff pay is slightly high",
                "detail": (
                    f"Staff pay was {pct*100:.0f}% of your sales this month "
                    f"({_money(cur, spent)}). The healthy level is about 30% — you're close, just keep an eye on it."
                ),
                "action": "No urgent change needed. Check again next week.",
            })
        else:
            out.append({
                "level": "good",
                "key": "staff",
                "title": "Staff pay is at a healthy level",
                "detail": f"You paid {pct*100:.0f}% of your sales to staff this month. That's right where it should be.",
                "action": None,
            })

    # --- Food / groceries cost ---
    if s["food_pct"] is not None and month_sales:
        pct = s["food_pct"]
        spent = pct * month_sales
        if pct > FOOD_TARGET + 0.04:
            extra = spent - FOOD_TARGET * month_sales
            out.append({
                "level": "act",
                "key": "food",
                "title": "You're spending too much on ingredients",
                "detail": (
                    f"Groceries and ingredients cost you {_money(cur, spent)} this month — "
                    f"{pct*100:.0f}% of your sales. A healthy level is about 33%. "
                    f"That's roughly {_money(cur, extra)} going out that shouldn't be."
                ),
                "action": "Check for wastage and compare prices with one more supplier this week.",
            })
        elif pct > FOOD_TARGET + 0.01:
            out.append({
                "level": "watch",
                "key": "food",
                "title": "Ingredient costs are a little high",
                "detail": (
                    f"Ingredients were {pct*100:.0f}% of your sales this month. "
                    f"About 33% is healthy — you're slightly above."
                ),
                "action": "Watch wastage for a week and see if it comes down.",
            })
        else:
            out.append({
                "level": "good",
                "key": "food",
                "title": "Ingredient costs look healthy",
                "detail": f"You spent {pct*100:.0f}% of your sales on ingredients. That's a good level.",
                "action": None,
            })

    # --- Quiet day ---
    worst, avg = s["worst_day"], s["overall_day_avg"]
    if worst and avg and worst["avg"] < avg * 0.85:
        gap_pct = (1 - worst["avg"] / avg) * 100
        out.append({
            "level": "watch",
            "key": "quiet_day",
            "title": f"{worst['name']}s are your quietest day",
            "detail": (
                f"On a normal day you earn about {_money(cur, avg)}, but on {worst['name']}s "
                f"it's only {_money(cur, worst['avg'])} — about {gap_pct:.0f}% less."
            ),
            "action": f"A small {worst['name']} special or offer could bring more people in. Even 10 extra customers helps.",
        })

    # --- Week-over-week trend ---
    wk = s["week"]
    if wk["change_pct"] is not None and wk["days"] >= 5:
        if wk["change_pct"] >= 5:
            out.append({
                "level": "good",
                "key": "trend",
                "title": "This week is better than last week",
                "detail": (
                    f"You earned {_money(cur, wk['total'])} in the last 7 days — "
                    f"{wk['change_pct']:.0f}% more than the week before. Whatever you did, it's working."
                ),
                "action": None,
            })
        elif wk["change_pct"] <= -10:
            out.append({
                "level": "watch",
                "key": "trend",
                "title": "This week is slower than last week",
                "detail": (
                    f"You earned {_money(cur, wk['total'])} in the last 7 days — "
                    f"{abs(wk['change_pct']):.0f}% less than the week before. One slow week is normal; two in a row is worth a look."
                ),
                "action": "If next week is also slow, ask a few regulars if anything changed.",
            })

    # Sort: act first, then watch, then good.
    order = {"act": 0, "watch": 1, "good": 2}
    out.sort(key=lambda i: order[i["level"]])
    return out


def lights(s: dict) -> list[dict]:
    """Traffic-light summary cards: green / amber / red, one line each."""
    result = []
    if s["staff_pct"] is not None:
        pct = s["staff_pct"]
        level = "act" if pct > STAFF_TARGET + 0.04 else "watch" if pct > STAFF_TARGET + 0.01 else "good"
        word = {"good": "healthy", "watch": "a little high", "act": "too high"}[level]
        result.append({"key": "staff", "label": "Staff pay", "level": level,
                       "line": f"{pct*100:.0f}% of sales — {word}"})
    if s["food_pct"] is not None:
        pct = s["food_pct"]
        level = "act" if pct > FOOD_TARGET + 0.04 else "watch" if pct > FOOD_TARGET + 0.01 else "good"
        word = {"good": "healthy", "watch": "a little high", "act": "too high"}[level]
        result.append({"key": "food", "label": "Ingredients", "level": level,
                       "line": f"{pct*100:.0f}% of sales — {word}"})
    return result
