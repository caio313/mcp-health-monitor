import httpx
from datetime import datetime
from core.db import get_schema_baseline, save_schema_snapshot


async def validate_tool_schema(server_url: str, tool_name: str) -> dict:
    result = {
        "server_url": server_url,
        "tool_name": tool_name,
        "validated_at": datetime.utcnow().isoformat(),
        "schema_valid": False,
        "issues": [],
        "declared_schema": None,
        "actual_output_sample": None,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            list_response = await client.post(
                server_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            )

            if list_response.status_code != 200:
                result["issues"].append(f"No se pudo listar tools: HTTP {list_response.status_code}")
                return result

            tools = list_response.json().get("result", {}).get("tools", [])
            target_tool = next((t for t in tools if t["name"] == tool_name), None)

            if not target_tool:
                result["issues"].append(f"Tool '{tool_name}' no encontrado en el servidor")
                return result

            result["declared_schema"] = target_tool.get("inputSchema", {})

            await save_schema_snapshot(server_url, tool_name, result["declared_schema"])

            schema = result["declared_schema"]
            if not schema.get("type"):
                result["issues"].append("Schema sin campo 'type' declarado")
            if not schema.get("properties") and schema.get("type") == "object":
                result["issues"].append("Schema tipo 'object' sin 'properties' definidas")

            result["schema_valid"] = len(result["issues"]) == 0

    except Exception as e:
        result["issues"].append(f"Error al validar: {str(e)}")

    return result


async def compare_schemas(server_url: str, tool_name: str, baseline_date: str) -> dict:
    current = await validate_tool_schema(server_url, tool_name)
    baseline = await get_schema_baseline(server_url, tool_name, baseline_date)

    if not baseline:
        return {
            "error": f"No hay baseline guardado para '{tool_name}' en fecha {baseline_date}",
            "suggestion": "Ejecutá validate_schema primero para crear un baseline."
        }

    current_schema = current.get("declared_schema", {})
    baseline_schema = baseline.get("schema", {})

    changes = _diff_schemas(baseline_schema, current_schema)

    return {
        "server_url": server_url,
        "tool_name": tool_name,
        "baseline_date": baseline_date,
        "compared_at": datetime.utcnow().isoformat(),
        "has_breaking_changes": len(changes["breaking"]) > 0,
        "has_additive_changes": len(changes["additive"]) > 0,
        "breaking_changes": changes["breaking"],
        "additive_changes": changes["additive"],
        "severity": "HIGH" if changes["breaking"] else "LOW"
    }


def _diff_schemas(baseline: dict, current: dict) -> dict:
    breaking = []
    additive = []

    baseline_props = set(baseline.get("properties", {}).keys())
    current_props = set(current.get("properties", {}).keys())

    for field in baseline_props - current_props:
        breaking.append(f"Campo '{field}' fue eliminado")

    for field in current_props - baseline_props:
        additive.append(f"Campo '{field}' fue agregado")

    for field in baseline_props & current_props:
        b_type = baseline.get("properties", {}).get(field, {}).get("type")
        c_type = current.get("properties", {}).get(field, {}).get("type")
        if b_type and c_type and b_type != c_type:
            breaking.append(f"Campo '{field}' cambió de tipo: {b_type} → {c_type}")

    return {"breaking": breaking, "additive": additive}
