from datetime import datetime
from core.db import get_metric_history


async def detect_drift(server_url: str, baseline_days: int = 7) -> dict:
    from tools.health import check_mcp_health

    current = await check_mcp_health(server_url)
    history = await get_metric_history(server_url, days=baseline_days)

    if not history:
        return {
            "server_url": server_url,
            "drift_detected": False,
            "message": "No hay historial suficiente. Ejecutá checks durante algunos días primero."
        }

    avg_latency = sum(h["latency_ms"] for h in history if h["latency_ms"]) / max(len(history), 1)
    avg_error_rate = sum(1 for h in history if h["status"] != "healthy") / max(len(history), 1)

    current_latency = current.get("latency_ms", 0) or 0
    latency_drift = ((current_latency - avg_latency) / max(avg_latency, 1)) * 100

    drift_signals = []

    if latency_drift > 50:
        drift_signals.append({
            "type": "LATENCY_SPIKE",
            "baseline_avg_ms": round(avg_latency, 1),
            "current_ms": current_latency,
            "increase_pct": round(latency_drift, 1),
            "severity": "HIGH" if latency_drift > 100 else "MEDIUM"
        })

    if current.get("status") != "healthy" and avg_error_rate < 0.1:
        drift_signals.append({
            "type": "NEW_FAILURE",
            "baseline_error_rate": f"{round(avg_error_rate * 100, 1)}%",
            "current_status": current.get("status"),
            "severity": "HIGH"
        })

    return {
        "server_url": server_url,
        "checked_at": datetime.utcnow().isoformat(),
        "drift_detected": len(drift_signals) > 0,
        "drift_signals": drift_signals,
        "baseline_days": baseline_days,
        "baseline_avg_latency_ms": round(avg_latency, 1),
        "current_latency_ms": current_latency,
        "overall_severity": max(
            (s["severity"] for s in drift_signals),
            default="NONE",
            key=lambda x: {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}[x]
        )
    }


async def get_drift_history(server_url: str, days: int = 30) -> dict:
    history = await get_metric_history(server_url, days=days)

    if not history:
        return {"error": "Sin historial disponible para este servidor."}

    latencies = [h["latency_ms"] for h in history if h["latency_ms"]]
    statuses = [h["status"] for h in history]

    return {
        "server_url": server_url,
        "period_days": days,
        "total_checks": len(history),
        "uptime_percent": round(
            (statuses.count("healthy") / max(len(statuses), 1)) * 100, 2
        ),
        "latency_stats": {
            "min_ms": min(latencies) if latencies else None,
            "max_ms": max(latencies) if latencies else None,
            "avg_ms": round(sum(latencies) / max(len(latencies), 1), 1),
            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else None,
        },
        "status_breakdown": {
            status: statuses.count(status)
            for status in set(statuses)
        },
        "stability_score": _calculate_stability(statuses, latencies)
    }


def _calculate_stability(statuses: list, latencies: list) -> str:
    if not statuses:
        return "UNKNOWN"
    uptime = statuses.count("healthy") / len(statuses)
    avg_lat = sum(latencies) / max(len(latencies), 1)
    if uptime >= 0.99 and avg_lat < 500:
        return "EXCELLENT"
    elif uptime >= 0.95 and avg_lat < 1000:
        return "GOOD"
    elif uptime >= 0.90:
        return "FAIR"
    return "POOR"
