import httpx
import os


async def get_blast_radius(service_id: str, service_registry: list[str]) -> dict:
    internal_url = os.environ.get("BLAST_RADIUS_INTERNAL_URL")
    
    if not internal_url:
        return {"error": "BLAST_RADIUS_INTERNAL_URL not configured"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            internal_url,
            json={"service_id": service_id, "service_registry": service_registry}
        )
        response.raise_for_status()
        return response.json()
