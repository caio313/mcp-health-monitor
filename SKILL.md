---
name: mcp-health
description: Monitorea y diagnostica la salud de ecosistemas de MCP servers. Usa cuando el usuario diga "revisá mis servers", "cómo está mi ecosistema", "algo está fallando", "qué pasa si cae X server", "hay degradación?", "revisá el drift", o cuando un agente necesite verificar el estado de sus dependencias antes de operar. Orquesta check_health, get_summary, check_drift y calculate_blast_radius en secuencias inteligentes según el contexto.
metadata:
  author: MCP Health
  version: 1.0.0
  mcp-server: mcp-health
---

# MCP Health — Guía de uso para Claude

## Cuándo usar cada tool

| Situación | Tool recomendada |
|---|---|
| "¿Cómo está todo?" | `get_summary` con todos los servers |
| "Revisá este server" | `check_health` individual |
| "Algo anda lento desde hace días" | `check_drift` |
| "Voy a hacer deploy / cambio" | `calculate_blast_radius` primero |
| Diagnóstico completo | Flujo secuencial (ver abajo) |

---

## Flujos principales

### Flujo 1: Monitoreo proactivo
Cuando el usuario pregunta por el estado general del ecosistema.

1. Llamar `get_summary` con todos los servers conocidos
2. Si `ecosystem_health_score` < 80: identificar cuál está degradado
3. Para cada server degradado: llamar `check_drift` (baseline_days=7)
4. Reportar: qué está mal, desde cuándo, y qué impacto tiene

```
get_summary([lista de servers])
→ si hay degradados → check_drift por cada uno
→ entregar diagnóstico con severidad y recomendación
```

### Flujo 2: Diagnóstico de fallo
Cuando algo está fallando o el usuario reporta un problema.

1. `check_health` del server sospechoso
2. Si `status != "healthy"`: `check_drift` para ver si es degradación gradual
3. `calculate_blast_radius` para entender el impacto en cascada
4. Recomendar acción: reintentar, escalar, o aislar el server

### Flujo 3: Análisis pre-cambio
Antes de hacer deploy, apagar un server, o cambiar dependencias.

1. `calculate_blast_radius` del server que va a cambiar
2. Si `severity == "CRITICAL"`: advertir y listar servicios afectados
3. Si hay cascade_affected: mapear el impacto completo
4. Recomendar ventana de mantenimiento o rollback plan

---

## Cómo interpretar los resultados

### check_health
- `status: healthy` + latency < 300ms → normal
- `status: degraded` → monitorear, probablemente hacer `check_drift`
- `status: unhealthy` → acción inmediata, hacer `calculate_blast_radius`

### check_drift
- `drift_detected: false` → el comportamiento es estable
- `drift_detected: true` + `overall_severity: LOW` → monitorear
- `drift_detected: true` + `overall_severity: HIGH` → escalar, hay degradación silenciosa

### calculate_blast_radius
- `severity: LOW` → cambio seguro
- `severity: MEDIUM` → coordinar con equipos afectados
- `severity: CRITICAL` → no proceder sin plan de contingencia; `ecosystem_impact_percent` indica qué % del ecosistema se ve afectado

---

## Reglas de comportamiento

- **Siempre empezar por `get_summary`** cuando no se especifica un server particular. Es más eficiente que múltiples `check_health` individuales.
- **Nunca recomendar apagar un server** sin antes calcular el blast radius.
- **Si `drift_detected: true`**: explicar al usuario que esto es degradación gradual — el agente no falla, pero toma peores decisiones. Es el problema central que MCP Health detecta.
- **Cuando `calculate_blast_radius` muestra cascade_affected**: listar explícitamente los servicios afectados de forma indirecta. Muchos usuarios no anticipan el efecto en cascada.

---

## Limitaciones actuales

- `calculate_blast_radius` requiere que el usuario declare las dependencias manualmente. No las auto-descubre todavía.
- No hay alertas automáticas en tiempo real (disponible en plan Team vía email).
- Las tools `analyze_dependencies`, `validate_schema`, `diff_schemas` están en desarrollo.

---

## Ejemplos de uso

**Ejemplo 1: chequeo de rutina**
Usuario: "¿Cómo están mis servers?"
→ `get_summary(["server-a", "server-b", "server-c"])`
→ Si hay degradados: `check_drift` por cada uno
→ Entregar resumen con health score y alertas

**Ejemplo 2: algo falla en producción**
Usuario: "el agente está tomando decisiones raras desde ayer"
→ `check_health` de los servers que usa ese agente
→ `check_drift(server, baseline_days=7)` en los degradados
→ Explicar si es degradación silenciosa y su severidad

**Ejemplo 3: antes de un deploy**
Usuario: "voy a actualizar auth-mcp"
→ `calculate_blast_radius("auth-mcp", [lista del ecosistema])`
→ Si CRITICAL: listar qué se ve afectado y recomendar ventana
