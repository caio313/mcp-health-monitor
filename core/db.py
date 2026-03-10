"""
core/db.py — PostgreSQL centralizado via Supabase

Estrategia de datos:
- server_url: URL real, visible solo para el dueño
- server_url_hash: hash SHA256, usado para benchmarks agregados
  Ningún cliente puede identificar los datos de otro cliente
  en los benchmarks. Mismo modelo que Datadog y New Relic.
"""

import asyncpg
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ANONYMIZE = os.getenv("ANONYMIZE_URLS", "true").lower() == "true"


PLAN_LIMITS = {
    "free": 100,
    "builder": 10000,
    "team": None
}


def utcnow():
    """Retorna datetime UTC aware."""
    return datetime.now(timezone.utc)


def anonymize_url(url: str) -> str:
    """
    Hash SHA256 de la URL para benchmarks anonimizados.
    El cliente ve sus propios datos con URL real.
    Los benchmarks cross-industry usan solo el hash.
    """
    return hashlib.sha256(url.encode()).hexdigest()[:16]


async def get_connection():
    """Conexión a PostgreSQL con SSL requerido para Supabase."""
    return await asyncpg.connect(DATABASE_URL, ssl="require")


async def init_db():
    """Crear tablas e índices en PostgreSQL si no existen."""
    conn = await get_connection()
    try:
        # Tabla principal de health checks
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS health_checks (
                id SERIAL PRIMARY KEY,
                server_url TEXT NOT NULL,
                server_url_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                latency_ms REAL,
                tools_count INTEGER DEFAULT 0,
                client_id TEXT,
                checked_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Tabla de snapshots de schemas
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_snapshots (
                id SERIAL PRIMARY KEY,
                server_url TEXT NOT NULL,
                server_url_hash TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                schema_json TEXT NOT NULL,
                captured_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Índices para queries frecuentes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_url_hash
            ON health_checks(server_url_hash, checked_at DESC)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_checked_at
            ON health_checks(checked_at DESC)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_schema_url_tool
            ON schema_snapshots(server_url_hash, tool_name, captured_at DESC)
        """)

        print("✅ PostgreSQL inicializado correctamente")
        print("✅ Tablas: health_checks, schema_snapshots")
        print("✅ Índices creados")

    finally:
        await conn.close()


async def save_check_result(
    server_url: str,
    status: str,
    latency_ms: float,
    tools_count: int = 0,
    client_id: str = None
):
    """
    Guarda resultado en PostgreSQL central.
    Guarda URL real Y hash para separar datos propios de benchmarks.
    """
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT INTO health_checks
               (server_url, server_url_hash, status, latency_ms, tools_count, client_id)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            server_url,
            anonymize_url(server_url),
            status,
            latency_ms,
            tools_count,
            client_id
        )
    finally:
        await conn.close()


async def get_uptime_history(server_url: str, hours: int = 24) -> float:
    """Calcula uptime de las últimas N horas desde PostgreSQL."""
    conn = await get_connection()
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        rows = await conn.fetch(
            """SELECT status FROM health_checks
               WHERE server_url_hash = $1
               AND checked_at > $2""",
            anonymize_url(server_url),
            since
        )
        if not rows:
            return None
        healthy = sum(1 for r in rows if r["status"] == "healthy")
        return round((healthy / len(rows)) * 100, 2)
    finally:
        await conn.close()


async def save_schema_snapshot(server_url: str, tool_name: str, schema: dict):
    """Guarda snapshot de schema con URL real y hash."""
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT INTO schema_snapshots
               (server_url, server_url_hash, tool_name, schema_json)
               VALUES ($1, $2, $3, $4)""",
            server_url,
            anonymize_url(server_url),
            tool_name,
            json.dumps(schema)
        )
    finally:
        await conn.close()


async def get_schema_baseline(server_url: str, tool_name: str, date_str: str):
    """Recupera el schema guardado más cercano a una fecha específica."""
    conn = await get_connection()
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        next_date = target_date + timedelta(days=1)
        row = await conn.fetchrow(
            """SELECT schema_json, captured_at FROM schema_snapshots
               WHERE server_url_hash = $1
               AND tool_name = $2
               AND captured_at BETWEEN $3 AND $4
               ORDER BY captured_at DESC LIMIT 1""",
            anonymize_url(server_url),
            tool_name,
            target_date,
            next_date
        )
        if not row:
            return None
        return {
            "schema": json.loads(row["schema_json"]),
            "captured_at": str(row["captured_at"])
        }
    finally:
        await conn.close()


async def get_metric_history(server_url: str, days: int = 7) -> list:
    """
    Recupera historial de métricas para drift detection.
    Usa server_url_hash para la query — nunca expone URLs de otros clientes.
    """
    conn = await get_connection()
    try:
        since = datetime.utcnow() - timedelta(days=days)
        rows = await conn.fetch(
            """SELECT status, latency_ms, checked_at
               FROM health_checks
               WHERE server_url_hash = $1
               AND checked_at > $2
               ORDER BY checked_at ASC""",
            anonymize_url(server_url),
            since
        )
        return [
            {
                "status": r["status"],
                "latency_ms": r["latency_ms"],
                "checked_at": str(r["checked_at"])
            }
            for r in rows
        ]
    finally:
        await conn.close()


def hash_api_key(key: str) -> str:
    """Hash SHA-256 de la API key."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    """Genera una API key segura."""
    return f"mcp_{secrets.token_urlsafe(32)}"


async def init_api_keys_table():
    """Crear tabla de API keys."""
    conn = await get_connection()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                key_hash TEXT UNIQUE NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                is_active BOOLEAN DEFAULT true,
                daily_checks_used INTEGER DEFAULT 0,
                last_reset TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_hash
            ON api_keys(key_hash)
        """)
        print("✅ Tabla api_keys creada")
    finally:
        await conn.close()


async def create_api_key(plan: str = "free") -> tuple[str, str]:
    """
    Crea una nueva API key.
    Retorna: (key_plain, key_hash)
    La key en texto plano solo se devuelve una vez.
    """
    key_plain = generate_api_key()
    key_hash = hash_api_key(key_plain)
    
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT INTO api_keys (key_hash, plan) VALUES ($1, $2)""",
            key_hash, plan
        )
        return key_plain, key_hash
    finally:
        await conn.close()


async def validate_api_key(key: str) -> Optional[dict]:
    """
    Valida una API key.
    Retorna el registro si es válida, None si no existe o está inactiva.
    """
    key_hash = hash_api_key(key)
    
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """SELECT id, plan, is_active, daily_checks_used, last_reset
               FROM api_keys WHERE key_hash = $1""",
            key_hash
        )
        if not row:
            return None
        
        if not row["is_active"]:
            return None
        
        if (utcnow() - row["last_reset"]).days >= 1:
            await conn.execute(
                """UPDATE api_keys SET daily_checks_used = 0, last_reset = NOW()
                   WHERE id = $1""",
                row["id"]
            )
            row = dict(row)
            row["daily_checks_used"] = 0
        
        return dict(row)
    finally:
        await conn.close()


async def increment_daily_usage(key_id: str):
    """Incrementa el contador de uso diario."""
    conn = await get_connection()
    try:
        await conn.execute(
            """UPDATE api_keys SET daily_checks_used = daily_checks_used + 1
               WHERE id = $1""",
            key_id
        )
    finally:
        await conn.close()


async def get_rate_limit(plan: str) -> Optional[int]:
    """Obtiene el límite de requests para un plan."""
    return PLAN_LIMITS.get(plan)
