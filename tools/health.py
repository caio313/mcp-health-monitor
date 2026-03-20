"""
tools/health.py
Lógica de health checks para MCP servers.
"""

import asyncio
import httpx
import time
from datetime import datetime, timedelta
from core.db import get_uptime_history, save_check_result
from models.schemas import HealthResult, HealthSummary


def parse_sse_response(text: str) -> dict:
    """Parsea respuesta SSE y devuelve el JSON del campo 'data'."""
    import json as json_module
    for line in text.strip().split('\n'):
        if line.startswith('data: '):
            return json_module.loads(line[6:])
    return {}


async def check_mcp_health(server_url: str, auth_headers: dict = None) -> dict:
    """
    Hace un health check real contra un MCP server.
    Intenta streamable-http primero, luego SSE si falla.
    Mide latencia, verifica disponibilidad y lista tools disponibles.
    
    Args:
        server_url: URL del MCP server a chequear
        auth_headers: Headers de autenticación opcionales para el target
    """
    start_time = time.time()
    result = {
        "url": server_url,
        "checked_at": datetime.utcnow().isoformat(),
        "status": "unknown",
        "latency_ms": None,
        "tools_available": [],
        "last_error": None,
        "uptime_24h": None,
    }

    tools = None
    extra_headers = auth_headers or {}

    # Intento 1: streamable-http
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Initialize para obtener session
            init_response = await client.post(
                server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "health-check", "version": "1.0"}
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    **extra_headers
                }
            )

            if init_response.status_code == 200:
                session_id = init_response.headers.get("mcp-session-id")

                # Parsear respuesta SSE
                init_data = parse_sse_response(init_response.text)

                if session_id:
                    # tools/list con session
                    tools_response = await client.post(
                        server_url,
                        json={
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/list",
                            "params": {}
                        },
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json, text/event-stream",
                            "mcp-session-id": session_id,
                            **extra_headers
                        }
                    )

                    if tools_response.status_code == 200:
                        tools_data = parse_sse_response(tools_response.text)
                        tools = tools_data.get("result", {}).get("tools", [])

            elif init_response.status_code == 401:
                result["status"] = "unhealthy"
                result["last_error"] = "Autenticación requerida. Pasá auth_headers con las credenciales del target."

    except httpx.TimeoutException:
        result["status"] = "unhealthy"
        result["last_error"] = "Timeout después de 10s"
    except httpx.ConnectError:
        result["status"] = "unreachable"
        result["last_error"] = "No se pudo conectar al servidor"
    except Exception as e:
        if result["status"] == "unknown":
            result["status"] = "error"
            result["last_error"] = str(e)

    # Intento 2: SSE legacy
    if tools is None and result["status"] not in ("unreachable", "unhealthy", "error"):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Algunos servers SSE exponen /sse como endpoint
                sse_url = server_url.rstrip("/").replace("/mcp", "") + "/sse"
                sse_response = await client.get(
                    sse_url,
                    headers={
                        "Accept": "text/event-stream",
                        **extra_headers
                    },
                    timeout=5.0
                )
                if sse_response.status_code == 200:
                    # Si responde en SSE, intentar tools/list
                    tools_response = await client.post(
                        server_url,
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/list",
                            "params": {}
                        },
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "text/event-stream",
                            **extra_headers
                        }
                    )
                    if tools_response.status_code == 200:
                        tools_data = parse_sse_response(tools_response.text)
                        tools = tools_data.get("result", {}).get("tools", [])
        except Exception:
            pass

    # Calcular latencia
    latency_ms = round((time.time() - start_time) * 1000, 2)
    result["latency_ms"] = latency_ms

    # Procesar resultado
    if tools is not None:
        result["status"] = "healthy"
        result["tools_available"] = [t["name"] for t in tools]

        if latency_ms > 2000:
            result["status"] = "degraded"
            result["last_error"] = f"Alta latencia: {latency_ms}ms"
    elif result["status"] == "unknown":
        result["status"] = "incompatible_protocol"
        result["last_error"] = "No se pudo obtener tools con ningún protocolo"

    # Guardar resultado en histórico y calcular uptime
    await save_check_result(server_url, result["status"], result["latency_ms"])
    result["uptime_24h"] = await get_uptime_history(server_url, hours=24)

    return result


async def get_health_summary(server_urls: list[str], auth_headers: dict = None) -> dict:
    """
    Checkea múltiples servers en paralelo y devuelve un resumen.
    
    Args:
        server_urls: Lista de URLs a chequear
        auth_headers: Headers de autenticación opcionales compartidos para todos los targets
    """
    # Ejecutar todos los checks en paralelo
    tasks = [check_mcp_health(url, auth_headers=auth_headers) for url in server_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summary = {
        "checked_at": datetime.utcnow().isoformat(),
        "total": len(server_urls),
        "healthy": 0,
        "degraded": 0,
        "unhealthy": 0,
        "unreachable": 0,
        "servers": []
    }

    for result in results:
        if isinstance(result, Exception):
            summary["unhealthy"] += 1
            continue

        status = result.get("status", "unknown")
        if status == "healthy":
            summary["healthy"] += 1
        elif status == "degraded":
            summary["degraded"] += 1
        elif status in ("unhealthy", "error", "incompatible_protocol"):
            summary["unhealthy"] += 1
        elif status == "unreachable":
            summary["unreachable"] += 1

        summary["servers"].append({
            "url": result["url"],
            "status": status,
            "latency_ms": result.get("latency_ms"),
            "tools_count": len(result.get("tools_available", [])),
            "uptime_24h": result.get("uptime_24h")
        })

    # Calcular health score general del ecosistema
    if summary["total"] > 0:
        summary["ecosystem_health_score"] = round(
            (summary["healthy"] / summary["total"]) * 100, 1
        )
    else:
        summary["ecosystem_health_score"] = 0

    return summary
