async def get_blast_radius(service_id: str, service_registry: list[str]) -> dict:
    from tools.dependencies import map_dependencies

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

    return {
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
    }
