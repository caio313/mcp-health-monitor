# MCP Health Server

Monitor de integridad para ecosistemas de MCP servers.
Cualquier agente IA puede usar estas tools para conocer
el estado real de su ecosistema en tiempo real.

---

## Tools disponibles

### ✅ check_health
Verifica el estado de un MCP server en tiempo real.
Detecta latencia, disponibilidad y tools expuestas.

```json
check_health("https://mi-server.com/mcp")

→ {
    "status": "healthy",
    "latency_ms": 226,
    "tools_available": ["ping", "get_time", "get_random_metric"],
    "uptime_24h": 99.5
  }
```

---

### ✅ get_summary
Estado de múltiples MCP servers en una sola llamada.
Ejecuta todos los checks en paralelo.

```json
get_summary([
  "https://server-a.com/mcp",
  "https://server-b.com/mcp"
])

→ {
    "total": 2,
    "healthy": 1,
    "degraded": 1,
    "unhealthy": 0,
    "ecosystem_health_score": 50.0
  }
```

---

### ✅ check_drift
Detecta si el comportamiento de un servidor cambió
respecto al baseline histórico. Encuentra degradación
gradual que los alertas tradicionales pierden.

```json
check_drift("https://mi-server.com/mcp", baseline_days=7)

→ {
    "drift_detected": false,
    "baseline_avg_latency_ms": 93.7,
    "current_latency_ms": 93.9,
    "overall_severity": "NONE"
  }
```

---

### ✅ calculate_blast_radius
Calcula el impacto en cascada si un servicio específico cae.
Muestra qué otros servicios se ven afectados directa e indirectamente.

```json
calculate_blast_radius(
  "auth-mcp",
  ["data-mcp", "trading-mcp", "report-mcp"]
)

→ {
    "directly_affected": ["data-mcp", "trading-mcp"],
    "cascade_affected": ["report-mcp"],
    "ecosystem_impact_percent": 100.0,
    "severity": "CRITICAL"
  }
```

---

## 🚧 Tools en desarrollo

| Tool | Descripción |
|---|---|
| `analyze_dependencies` | Grafo de dependencias entre servicios |
| `find_critical_paths` | Servicios más críticos del ecosistema |
| `validate_schema` | Valida que un tool cumple su schema declarado |
| `diff_schemas` | Detecta breaking changes entre versiones |
| `get_drift_report` | Reporte histórico de estabilidad |

---

## Setup local

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/mcp-health-server
cd mcp-health-server

# 2. Crear entorno virtual e instalar dependencias
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Inicializar base de datos
python -c "import asyncio; from core.db import init_db; asyncio.run(init_db())"

# 4. Correr el servidor
python main.py
# Disponible en: http://localhost:8000/mcp
```

---

## Conectar a tu agente

```json
{
  "mcpServers": {
    "mcp-health": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

---

## Compatibilidad

Soporta ambos transportes MCP:
- `streamable-http` (estándar actual)
- `SSE` (Server-Sent Events)

---

## Pricing

| Plan | Precio | Límite |
|---|---|---|
| **Free** | $0 | 5 servers, 100 checks/día |
| **Builder** | $19/mes | 20 servers, 10k checks/día |
| **Team** | $49/mes | Ilimitado + alertas por email |

---

## Deploy

El servidor está disponible en:
https://mcp-health-server.onrender.com/mcp

Agregá al agente con esta configuración:

```json
{
  "mcpServers": {
    "mcp-health": {
      "url": "https://mcp-health-server.onrender.com/mcp"
    }
  }
}
```

---

## Skill para agentes IA

Incluye un SKILL.md optimizado para Claude y OpenCode
que orquesta las tools automáticamente según el contexto.

En lugar de llamar tools una por una, el agente entiende
situaciones como "algo anda lento" y ejecuta el flujo
correcto automáticamente.

Para activarlo en OpenCode copiá SKILL.md a:
~/.config/opencode/skills/mcp-health.md

---

## Stack

- Python 3.11+
- FastMCP
- FastAPI + Uvicorn
- PostgreSQL via Supabase (histórico de métricas)
- httpx (HTTP async)
