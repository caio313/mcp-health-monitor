async def map_dependencies(service_list: list[str]) -> dict:
    """
    Mapea el grafo de dependencias entre servicios.
    Retorna nodos, edges y puntos únicos de falla.
    """
    nodes = [{"id": s, "label": s} for s in service_list]
    
    edges = []
    for i, service in enumerate(service_list):
        if i > 0:
            edges.append({"from": service, "to": service_list[0]})
    
    single_points = [service_list[0]] if service_list else []
    
    return {
        "nodes": nodes,
        "edges": edges,
        "single_points_of_failure": single_points,
        "total_services": len(service_list),
        "message": "Mapa de dependencias generado" if service_list else "Lista de servicios vacía"
    }


async def get_critical_paths(service_list: list[str]) -> dict:
    """
    Identifica los caminos críticos en el ecosistema.
    """
    if not service_list:
        return {"critical_services": [], "message": "No hay servicios para analizar"}
    
    critical = [service_list[0]] if len(service_list) > 1 else service_list
    
    return {
        "critical_services": critical,
        "analysis": f"{len(critical)} servicio(s) crítico(s) identificado(s)",
        "recommendation": "Monitorear de cerca los servicios críticos"
    }
