# RestaurantIQ

Simple restaurant analytics that anyone can use — no computer skills needed.
Phone-number login (OTP), 30-second daily entry, plain-language insights,
and an AI advisor powered by Claude.

## Run it

```
cd restaurantiq
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8010
```

Then open **http://localhost:8010** (or double-click `run.bat`).

Click **"Just show me a demo"** to explore with 90 days of realistic sample
data, or log in with any phone number — the OTP is shown on screen in demo
mode (in production it would arrive by SMS).

## Smart AI answers (optional)

Set your Claude API key before starting the server and the **Ask** tab uses
Claude (claude-opus-4-8) for real conversational answers:

```
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python -m uvicorn app.main:app --port 8010
```

Without a key the Ask tab still works — it answers from the built-in
rule-based insights.

## What's inside

| Piece | File(s) |
|---|---|
| API server (FastAPI) | `app/main.py` |
| Phone + OTP login, JWT sessions | `app/auth.py` |
| SQLite storage | `app/db.py` |
| Metrics engine (weekly/monthly, weekday patterns) | `app/metrics.py` |
| Plain-language insights + traffic lights | `app/insights.py` |
| Claude integration + rule-based fallback | `app/ai.py` |
| Demo data (90 days) | `app/seed.py` |
| Mobile-first frontend | `frontend/` |

## Design principles

- **Usable by everyone.** Phone + OTP, no email or passwords. Every label is
  plain language ("How much did you earn?" not "Revenue"). Traffic lights
  instead of percentages wherever possible.
- **Value without learning the app.** One daily 30-second entry is enough;
  the home screen shows one big number, one headline insight, one action.
- **Manual entry first, POS later.** Local restaurants often have no POS —
  the daily form is the primary data source. Square/Toast/Clover sync can be
  added later feeding the same `entries` table.

## Next steps (production)

- Real SMS OTP (Twilio / MSG91) — swap into `auth.py` / `request_otp`.
- WhatsApp daily digest + reply-to-ask (WhatsApp Business API).
- Local-language UI + voice input for the Ask tab.
- POS integrations (webhooks → same entries/metrics pipeline).
- Postgres + proper secret management when moving off a single machine.

