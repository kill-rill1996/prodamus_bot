"""Suppress completed retries; serialize concurrent deliveries of one event.

Only a digest is stored, never a token or the customer's webhook payload.
The existing business operations use their own transactions. This prevents
completed/concurrent replays, but is not an exactly-once Telegram outbox:
a process crash during an external call can still require reconciliation.
"""
import hashlib
import json
from datetime import datetime

from sqlalchemy import text

from database import async_engine
from services import verified_payload


def event_key(payload: dict, mode: str) -> str:
    # Prodamus increments the transport attempt on redelivery. Subscription
    # current_attempt is a different (payment) event and must be retained.
    stable = {key: value for key, value in payload.items() if key != "attempt"}
    encoded = json.dumps([mode, stable], ensure_ascii=False,
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def operation_identity(payload: dict, mode: str):
    sub = payload.get("subscription", {})
    if mode == "purchase" and payload.get("payment_status") == "success":
        kind = "BUY_SUB"
    elif (mode == "auto" and sub.get("type") == "action"
          and sub.get("action_code") == "auto_payment"
          and not sub.get("error")):
        kind = "AUTO_PAY"
    else:
        return None
    try:
        paid_at = datetime.strptime(sub["date_last_payment"], "%Y-%m-%d %H:%M:%S")
        return {"tg_id": str(payload["order_num"]), "kind": kind, "paid_at": paid_at}
    except (KeyError, TypeError, ValueError):
        return None  # Existing schema validation will reject malformed events.


async def process_once(request, mode, handler):
    payload = await verified_payload(request, mode)
    key = event_key(payload, mode)
    lock_id = int.from_bytes(bytes.fromhex(key[:16]), "big", signed=True)
    async with async_engine.begin() as conn:
        await conn.execute(text("SET LOCAL lock_timeout = '30s'"))
        await conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        done = await conn.scalar(text(
            "SELECT 1 FROM webhook_receipts WHERE event_key = :key"), {"key": key})
        if done:
            return {"status": "duplicate"}

        # Also recognize successful payments handled before this deployment.
        identity = operation_identity(payload, mode)
        historical = False
        if identity:
            historical = await conn.scalar(text(
                "SELECT 1 FROM operations WHERE tg_id = :tg_id "
                "AND type = :kind AND date = :paid_at LIMIT 1"), identity)
        result = {"status": "duplicate"} if historical else await handler(request)
        await conn.execute(text(
            "INSERT INTO webhook_receipts (event_key, event_type) VALUES (:key, :mode) "
            "ON CONFLICT (event_key) DO NOTHING"), {"key": key, "mode": mode})
        return result
