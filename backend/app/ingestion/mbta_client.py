from datetime import datetime
from typing import Any

import httpx

from app.ingestion.dto import PredictionReading, StopReading, VehicleReading

# Limits the stop sync to subway/light rail (MBTA's own route_type codes:
# 0 = light rail, 1 = heavy rail) instead of the entire system. MBTA's bus
# network alone has thousands of stops; a full unfiltered sync would need
# pagination handling for comparatively little demo value. Easy to widen
# later (e.g. add "2,3" for commuter rail and bus) once that's worth it.
DEFAULT_STOP_ROUTE_TYPES = "0,1"


class MbtaClient:
    """Thin wrapper over MBTA's V3 API. Owns HTTP concerns and JSON:API
    parsing; callers get back plain reading objects and never see the wire
    format.
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
        response = self._http_client.get(f"{self._base_url}/vehicles", headers=self._headers())
        response.raise_for_status()

        payload = response.json()
        parsed = (_parse_vehicle(item) for item in payload.get("data", []))
        return [reading for reading in parsed if reading is not None]

    def get_stops(self, route_types: str = DEFAULT_STOP_ROUTE_TYPES) -> list[StopReading]:
        response = self._http_client.get(
            f"{self._base_url}/stops",
            headers=self._headers(),
            params={"filter[route_type]": route_types, "page[limit]": 500},
        )
        response.raise_for_status()

        payload = response.json()
        parsed = (_parse_stop(item) for item in payload.get("data", []))
        return [reading for reading in parsed if reading is not None]

    def get_predictions(self, stop_id: str) -> list[PredictionReading]:
        if not stop_id or not stop_id.strip():
            raise ValueError("stop_id must be a non-empty string")

        response = self._http_client.get(
            f"{self._base_url}/predictions",
            headers=self._headers(),
            # A busy stop can have 50+ predictions queued; the UI only ever
            # shows the next handful, so there's no reason to transfer more.
            params={"filter[stop]": stop_id, "sort": "arrival_time", "page[limit]": 10},
        )
        response.raise_for_status()

        payload = response.json()
        parsed = (_parse_prediction(item) for item in payload.get("data", []))
        return [reading for reading in parsed if reading is not None]

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self._api_key} if self._api_key else {}


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


def _parse_stop(item: dict[str, Any]) -> StopReading | None:
    try:
        attributes = item["attributes"]
        return StopReading(
            stop_id=item["id"],
            name=attributes["name"],
            latitude=attributes["latitude"],
            longitude=attributes["longitude"],
            wheelchair_boarding=attributes.get("wheelchair_boarding", 0),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _parse_prediction(item: dict[str, Any]) -> PredictionReading | None:
    try:
        attributes = item["attributes"]
        relationships = item.get("relationships", {})
        return PredictionReading(
            route_id=_relationship_id(relationships, "route"),
            trip_id=_relationship_id(relationships, "trip"),
            vehicle_id=_relationship_id(relationships, "vehicle"),
            arrival_time=_parse_optional_datetime(attributes.get("arrival_time")),
            departure_time=_parse_optional_datetime(attributes.get("departure_time")),
            status=attributes.get("status"),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _relationship_id(relationships: dict[str, Any], name: str) -> str | None:
    relationship_data = relationships.get(name, {}).get("data")
    if relationship_data is None:
        return None
    return relationship_data.get("id")
