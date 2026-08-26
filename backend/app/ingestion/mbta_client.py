from datetime import datetime
from typing import Any

import httpx

from app.ingestion.dto import VehicleReading


class MbtaClient:
    """Thin wrapper over MBTA's V3 API. Owns HTTP concerns and JSON:API
    parsing; callers get back plain VehicleReading objects and never see
    the wire format.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        http_client: httpx.Client | None = None,
    ) -> None:
        if not base_url or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")

        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http_client = http_client or httpx.Client(timeout=10.0)

    def get_vehicles(self) -> list[VehicleReading]:
        headers = {"x-api-key": self._api_key} if self._api_key else {}
        response = self._http_client.get(f"{self._base_url}/vehicles", headers=headers)
        response.raise_for_status()

        payload = response.json()
        parsed = (_parse_vehicle(item) for item in payload.get("data", []))
        return [reading for reading in parsed if reading is not None]


def _parse_vehicle(item: dict[str, Any]) -> VehicleReading | None:
    try:
        attributes = item["attributes"]
        relationships = item.get("relationships", {})
        return VehicleReading(
            vehicle_id=item["id"],
            route_id=_relationship_id(relationships, "route"),
            trip_id=_relationship_id(relationships, "trip"),
            latitude=attributes["latitude"],
            longitude=attributes["longitude"],
            bearing=attributes.get("bearing"),
            speed=attributes.get("speed"),
            current_status=attributes["current_status"],
            updated_at=datetime.fromisoformat(attributes["updated_at"]),
        )
    except (KeyError, TypeError, ValueError):
        # One malformed record from upstream shouldn't take down the whole poll.
        return None


def _relationship_id(relationships: dict[str, Any], name: str) -> str | None:
    relationship_data = relationships.get(name, {}).get("data")
    if relationship_data is None:
        return None
    return relationship_data.get("id")
