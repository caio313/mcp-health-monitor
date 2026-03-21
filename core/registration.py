"""
core/registration.py
Endpoint para que usuarios generen su API key asociada a su email.
"""

import os
from starlette.requests import Request
from starlette.responses import JSONResponse
from core.db import get_connection, generate_api_key, hash_api_key


async def register_user(request: Request) -> JSONResponse:
    """
    POST /register
    Body: { "email": "usuario@ejemplo.com" }
    
    Crea una API key free asociada al email.
    La key se muestra una sola vez — el usuario debe guardarla.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON"})

    email = body.get("email", "").strip().lower()
    if not email or "@" not in email:
        return JSONResponse(status_code=400, content={"detail": "Email inválido"})

    conn = await get_connection()
    try:
        # Verificar si ya existe una key para este email
        existing = await conn.fetchrow(
            "SELECT id, plan FROM api_keys WHERE email = $1 AND is_active = true",
            email
        )
        if existing:
            return JSONResponse(
                status_code=409,
                content={"detail": "Ya existe una API key para este email. Revisá tu casilla."}
            )

        # Crear nueva key
        key_plain = generate_api_key()
        key_hash = hash_api_key(key_plain)

        await conn.execute(
            """INSERT INTO api_keys (key_hash, plan, email) VALUES ($1, $2, $3)""",
            key_hash, "free", email
        )

        return JSONResponse(
            status_code=201,
            content={
                "api_key": key_plain,
                "plan": "free",
                "email": email,
                "message": "Guardá esta key — no se puede recuperar después.",
                "limits": {
                    "checks_per_day": 100
                }
            }
        )
    finally:
        await conn.close()


async def add_email_column():
    """
    Migración: agrega columna email a api_keys si no existe.
    Ejecutar una sola vez.
    """
    conn = await get_connection()
    try:
        await conn.execute("""
            ALTER TABLE api_keys 
            ADD COLUMN IF NOT EXISTS email TEXT
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_email
            ON api_keys(email)
        """)
        print("✅ Columna email agregada a api_keys")
    finally:
        await conn.close()
