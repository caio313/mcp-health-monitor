"""
MCP Health Server
Monitoreo y validación de integridad entre MCP servers.
Construido con FastMCP — el framework estándar para MCP en Python.
"""

import os
from fastmcp import FastMCP
from tools.health import check_mcp_health, get_health_summary
from tools.dependencies import map_dependencies, get_critical_paths
from tools.validation import validate_tool_schema, compare_schemas
from tools.blast_radius import get_blast_radius
from tools.drift import detect_drift, get_drift_history

# ─────────────────────────────────────────
# Configuración de puerto para Railway
# ─────────────────────────────────────────
PORT = int(os.environ.get("PORT", 8000))

# ─────────────────────────────────────────
# Inicializar el servidor MCP
# ─────────────────────────────────────────
mcp = FastMCP(
    name="MCP Health Server",
    instructions="""
    Herramienta de monitoreo y validación de integridad para ecosistemas MCP.
    
    Capacidades:
    - Verificar el estado de cualquier MCP server en tiempo real
    - Mapear dependencias entre servicios y detectar puntos de falla
    - Validar que los schemas de tools no cambiaron sin aviso
    - Calcular el blast radius si un servicio cae
    - Detectar drift de comportamiento vs baseline histórico
    
    Ideal para: developers que orquestan múltiples MCP servers y necesitan
    saber el estado de su ecosistema antes de tomar decisiones.
    """
)


# ─────────────────────────────────────────
# TOOL 1: Health Check
# ─────────────────────────────────────────
@mcp.tool()
async def check_health(server_url: str) -> dict:
    """
    Verifica el estado de un MCP server en tiempo real.
    
    Retorna: status, latencia, uptime 24h, último error, tools disponibles.
    
    Ejemplo: check_health("https://mi-mcp-server.com/mcp")
    """
    return await check_mcp_health(server_url)


@mcp.tool()
async def get_summary(server_urls: list[str]) -> dict:
    """
    Resumen de estado de múltiples MCP servers de una sola vez.
    
    Retorna: tabla con status de cada server, cuántos están caídos,
    cuántos degradados, y cuántos saludables.
    
    Ejemplo: get_summary(["https://server-a.com/mcp", "https://server-b.com/mcp"])
    """
    return await get_health_summary(server_urls)


# ─────────────────────────────────────────
# TOOL 2: Análisis de Dependencias
# ─────────────────────────────────────────
@mcp.tool()
async def analyze_dependencies(service_list: list[str]) -> dict:
    """
    Mapea el grafo de dependencias entre MCP servers.
    
    Detecta:
    - Qué servicio depende de cuál
    - Puntos únicos de falla (single points of failure)
    - Servicios circulares o con dependencias problemáticas
    
    Ejemplo: analyze_dependencies(["auth-mcp", "data-mcp", "trading-mcp"])
    """
    return await map_dependencies(service_list)


@mcp.tool()
async def find_critical_paths(service_list: list[str]) -> dict:
    """
    Identifica los caminos críticos en el ecosistema de servicios.
    
    Retorna los servicios que, si caen, generan el mayor impacto
    en cascada sobre el resto del ecosistema.
    """
    return await get_critical_paths(service_list)


# ─────────────────────────────────────────
# TOOL 3: Validación de Schemas
# ─────────────────────────────────────────
@mcp.tool()
async def validate_schema(server_url: str, tool_name: str) -> dict:
    """
    Valida que un tool MCP devuelve exactamente lo que su schema declara.
    
    Detecta:
    - Campos que el schema declara pero el tool no devuelve
    - Campos extra no declarados en el schema
    - Tipos de datos incorrectos
    - Cambios de schema silenciosos (breaking changes)
    
    Ejemplo: validate_schema("https://mi-server.com/mcp", "get_price")
    """
    return await validate_tool_schema(server_url, tool_name)


@mcp.tool()
async def diff_schemas(
    server_url: str,
    tool_name: str,
    baseline_date: str
) -> dict:
    """
    Compara el schema actual de un tool contra un baseline histórico.
    
    Útil para detectar breaking changes entre deployments.
    
    Ejemplo: diff_schemas("https://server.com/mcp", "get_price", "2026-03-01")
    """
    return await compare_schemas(server_url, tool_name, baseline_date)


# ─────────────────────────────────────────
# TOOL 4: Blast Radius
# ─────────────────────────────────────────
@mcp.tool()
async def calculate_blast_radius(
    service_id: str,
    service_registry: list[str]
) -> dict:
    """
    Calcula el impacto en cascada si un servicio específico cae.
    
    Retorna:
    - Lista de servicios afectados directamente
    - Lista de servicios afectados en cascada
    - Porcentaje del ecosistema impactado
    - Severidad: LOW / MEDIUM / HIGH / CRITICAL
    
    Ejemplo: calculate_blast_radius("auth-mcp", ["data-mcp", "trading-mcp", "report-mcp"])
    """
    return await get_blast_radius(service_id, service_registry)


# ─────────────────────────────────────────
# TOOL 5: Detección de Drift
# ─────────────────────────────────────────
@mcp.tool()
async def check_drift(server_url: str, baseline_days: int = 7) -> dict:
    """
    Detecta si el comportamiento de un MCP server cambió respecto al baseline.
    
    Analiza:
    - Cambios en latencia promedio
    - Cambios en tasa de errores
    - Cambios en patrones de respuesta
    - Anomalías estadísticas vs histórico
    
    Ejemplo: check_drift("https://mi-server.com/mcp", baseline_days=7)
    """
    return await detect_drift(server_url, baseline_days)


@mcp.tool()
async def get_drift_report(server_url: str, days: int = 30) -> dict:
    """
    Reporte completo de drift histórico de un servidor.
    
    Útil para entender la estabilidad de un servicio a lo largo del tiempo
    y detectar patrones de degradación gradual.
    """
    return await get_drift_history(server_url, days)


# ─────────────────────────────────────────
# Health check endpoint para Railway
# ─────────────────────────────────────────
from starlette.routing import Route
from starlette.responses import JSONResponse

app = mcp.http_app()


async def health_check(request):
    return JSONResponse({"status": "ok"})


app.router.routes.append(Route("/health", health_check))


async def internal_blast_radius(request):
    import json
    from tools.dependencies import map_dependencies

    body = await request.json()
    service_id = body.get("service_id")
    service_registry = body.get("service_registry", [])

    all_services = list(set([service_id] + service_registry))
    dep_map = await map_dependencies(all_services)

    directly_affected = []
    cascade_affected = []

    for edge in dep_map["edges"]:
        if edge["to"] == service_id:
            directly_affected.append(edge["from"])

    for edge in dep_map["edges"]:
        if edge["to"] in directly_affected and edge["from"] not in directly_affected:
            cascade_affected.append(edge["from"])

    total_affected = len(set(directly_affected + cascade_affected))
    impact_pct = round((total_affected / max(len(service_registry), 1)) * 100, 1)

    severity = (
        "CRITICAL" if impact_pct >= 50
        else "HIGH" if impact_pct >= 25
        else "MEDIUM" if impact_pct >= 10
        else "LOW"
    )

    return JSONResponse({
        "service_id": service_id,
        "directly_affected": directly_affected,
        "cascade_affected": list(set(cascade_affected)),
        "total_services_impacted": total_affected,
        "ecosystem_impact_percent": impact_pct,
        "severity": severity,
        "recommendation": (
            f"Si '{service_id}' cae, {impact_pct}% del ecosistema se ve afectado. "
            f"{'Implementar fallback urgente.' if severity == 'CRITICAL' else 'Monitorear de cerca.'}"
        )
    })


app.router.routes.append(Route("/internal/blast-radius", internal_blast_radius, methods=["POST"]))


# ─────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
