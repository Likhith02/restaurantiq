"""Phone number + OTP login. No email, no passwords.

In this prototype the OTP is returned in the API response (demo mode) so it
works without an SMS provider. In production, plug in an SMS gateway
(Twilio / MSG91 / WhatsApp Business) inside send_otp() and stop returning
the code to the client.
"""
import os
import random
import re
import time

import jwt
from fastapi import Header, HTTPException

SECRET = os.environ.get("RIQ_SECRET", "dev-secret-change-me")
OTP_TTL_SECONDS = 5 * 60
TOKEN_TTL_SECONDS = 30 * 24 * 3600


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if not (8 <= len(digits) <= 15):
        raise HTTPException(400, "Please enter a valid phone number.")
    return digits


def make_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def create_token(restaurant_id: int) -> str:
    payload = {"rid": restaurant_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    return jwt.encode(payload, SECRET, algorithm="HS256")


def current_restaurant_id(authorization: str = Header(default=None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not logged in.")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired. Please log in again.")
    return int(payload["rid"])
