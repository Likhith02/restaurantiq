"""AI advisor. Calls Claude when ANTHROPIC_API_KEY is set; otherwise falls
back to a rule-based answer built from the same insights, so the app always
gives a useful reply."""
import os

try:
    import anthropic
except ImportError:  # SDK not installed — fallback mode still works
    anthropic = None

MODEL = "claude-opus-4-8"

SYSTEM = """You are the friendly advisor inside RestaurantIQ, an app for small
restaurant owners who are not tech-savvy and may not know business terms.

Rules:
- Plain, everyday language. Never use jargon like "labor cost percentage",
  "metrics", "KPI", "margin", "revenue optimization". Talk about money,
  customers, and staff the way a helpful friend would.
- Keep answers short: 3 to 6 sentences, or 2-3 concrete suggestions.
- Always ground your answer in the numbers provided, using the owner's
  currency symbol.
- If the owner writes in a language other than English, reply in that language.
- Be encouraging but honest. If the data doesn't answer the question, say so
  simply and suggest what to record."""


def available() -> bool:
    return anthropic is not None and bool(os.environ.get("ANTHROPIC_API_KEY"))


def build_context(restaurant: dict, summary: dict, insight_list: list[dict], entries: list[dict]) -> str:
    cur = restaurant.get("currency") or "₹"
    lines = [
        f"Restaurant: {restaurant.get('name')} ({restaurant.get('rtype') or 'restaurant'}), "
        f"seats: {restaurant.get('seats') or 'unknown'}, currency: {cur}",
        f"Days of data recorded: {summary['n_entries']}",
        f"Last 7 days sales: {cur}{summary['week']['total']:,.0f} "
        f"(previous 7 days: {cur}{summary['week']['prev_total']:,.0f})",
        f"Last 30 days sales: {cur}{summary['month']['total']:,.0f}",
    ]
    if summary["staff_pct"] is not None:
        lines.append(f"Staff pay share of sales (30d): {summary['staff_pct']*100:.1f}% (healthy: ~30%)")
    if summary["food_pct"] is not None:
        lines.append(f"Ingredient cost share of sales (30d): {summary['food_pct']*100:.1f}% (healthy: ~33%)")
    if summary["avg_check"] is not None:
        lines.append(f"Average spend per customer: {cur}{summary['avg_check']:,.0f}")
    day_bits = [
        f"{w['name']}: {cur}{w['avg']:,.0f}" for w in summary["weekdays"] if w["avg"] is not None
    ]
    if day_bits:
        lines.append("Average sales by day of week — " + ", ".join(day_bits))
    if insight_list:
        lines.append("Current findings: " + " | ".join(i["title"] for i in insight_list))
    recent = entries[-14:]
    if recent:
        lines.append("Last 14 days (date, sales, customers, staff on duty):")
        for e in recent:
            lines.append(
                f"  {e['date']}: {cur}{e['sales']:,.0f}, "
                f"{e.get('customers') or '?'} customers, {e.get('staff_count') or '?'} staff"
            )
    return "\n".join(lines)


def ask_claude(question: str, context: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        thinking={"type": "adaptive"},
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Here is the restaurant's data:\n{context}\n\nThe owner asks: {question}",
        }],
    )
    return next((b.text for b in response.content if b.type == "text"), "").strip()


def fallback_answer(question: str, summary: dict, insight_list: list[dict], cur: str) -> str:
    """No API key: answer from the rule-based insights."""
    parts = ["Here's what I can see from your numbers:"]
    for i in insight_list[:3]:
        parts.append(f"• {i['detail']}")
        if i.get("action"):
            parts.append(f"  What you can do: {i['action']}")
    if len(parts) == 1:
        parts.append(
            "• I don't have enough days recorded yet to answer well. "
            "Add your numbers each evening for a week and I'll have much more to say."
        )
    parts.append(
        "\n(Smart answers are off right now — the app owner needs to add an AI key. "
        "These tips come from your recorded numbers.)"
    )
    return "\n".join(parts)
