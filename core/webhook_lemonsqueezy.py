"""
core/webhook_lemonsqueezy.py
Maneja eventos de Lemon Squeezy para actualizar planes en Supabase.
"""

import hashlib
import hmac
import json
import os
from starlette.requests import Request
from starlette.responses import JSONResponse
from core.db import get_connection

WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET", "")
VARIANT_BUILDER = os.getenv("LEMONSQUEEZY_VARIANT_BUILDER", "")
VARIANT_TEAM = os.getenv("LEMONSQUEEZY_VARIANT_TEAM", "")


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verifica que el webhook viene realmente de Lemon Squeezy."""
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def get_plan_from_variant(variant_id: str) -> str | None:
    """Mapea variant ID de Lemon Squeezy al plan interno."""
    if str(variant_id) == str(VARIANT_BUILDER):
        return "builder"
    if str(variant_id) == str(VARIANT_TEAM):
        return "team"
    return None


async def update_plan_by_email(email: str, plan: str):
    """Actualiza el plan de todas las API keys asociadas a un email."""
    conn = await get_connection()
    try:
        await conn.execute(
            """UPDATE api_keys SET plan = $1 WHERE email = $2 AND is_active = true""",
            plan, email
        )
    finally:
        await conn.close()


async def downgrade_plan_by_email(email: str):
    """Baja el plan a free cuando una suscripción se cancela o expira."""
    conn = await get_connection()
    try:
        await conn.execute(
            """UPDATE api_keys SET plan = 'free' WHERE email = $1 AND is_active = true""",
            email
        )
    finally:
        await conn.close()


async def handle_lemonsqueezy_webhook(request: Request) -> JSONResponse:
    """
    Endpoint principal del webhook.
    Eventos manejados:
    - order_created: nuevo pago único (no aplica a suscripciones pero se maneja igual)
    - subscription_created: nueva suscripción activa
    - subscription_updated: cambio de plan
    - subscription_cancelled: cancelación
    - subscription_expired: expiración
    """
    payload = await request.body()
    signature = request.headers.get("X-Signature", "")

    if not verify_signature(payload, signature):
        return JSONResponse(status_code=401, content={"detail": "Invalid signature"})

    try:
        data = json.loads(payload)
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON"})

    event = data.get("meta", {}).get("event_name", "")
    attrs = data.get("data", {}).get("attributes", {})

    email = attrs.get("user_email") or attrs.get("customer_email", "")
    variant_id = str(attrs.get("variant_id", ""))

    # Suscripción creada o actualizada
    if event in ("subscription_created", "subscription_updated", "order_created"):
        plan = get_plan_from_variant(variant_id)
        if plan and email:
            await update_plan_by_email(email, plan)

    # Suscripción cancelada o expirada → bajar a free
    elif event in ("subscription_cancelled", "subscription_expired"):
        if email:
            await downgrade_plan_by_email(email)

    return JSONResponse(status_code=200, content={"ok": True})
