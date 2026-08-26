from datetime import datetime, timezone

import httpx
import pytest

from app.ingestion.mbta_client import MbtaClient

VEHICLE_PAYLOAD = {
    "data": [
        {
            "id": "y1234",
            "type": "vehicle",
            "attributes": {
                "latitude": 42.3564,
                "longitude": -71.0624,
                "bearing": 90,
                "speed": 5.5,
                "current_status": "IN_TRANSIT_TO",
                "updated_at": "2026-08-25T12:00:00-04:00",
            },
            "relationships": {
                "route": {"data": {"id": "Red", "type": "route"}},
                "trip": {"data": {"id": "trip-1", "type": "trip"}},
            },
        },
        {
            "id": "y5678",
            "type": "vehicle",
            "attributes": {
                # missing "current_status" on purpose: simulates a malformed
                # upstream record that should be skipped, not crash the poll.
                "latitude": 42.0,
                "longitude": -71.0,
                "bearing": None,
                "speed": None,
                "updated_at": "2026-08-25T12:00:00-04:00",
            },
            "relationships": {},
        },
    ]
}


def make_client(handler) -> MbtaClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return MbtaClient(base_url="https://api-v3.mbta.com", http_client=http_client)


def test_get_vehicles_parses_well_formed_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/vehicles"
        return httpx.Response(200, json=VEHICLE_PAYLOAD)

    client = make_client(handler)

    readings = client.get_vehicles()

    assert len(readings) == 1  # the malformed second record is dropped
    reading = readings[0]
    assert reading.vehicle_id == "y1234"
    assert reading.route_id == "Red"
    assert reading.trip_id == "trip-1"
    assert reading.current_status == "IN_TRANSIT_TO"
    assert reading.updated_at == datetime.fromisoformat("2026-08-25T12:00:00-04:00")


def test_get_vehicles_returns_empty_list_when_no_data() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    client = make_client(handler)

    assert client.get_vehicles() == []


def test_get_vehicles_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"errors": ["boom"]})

    client = make_client(handler)

    with pytest.raises(httpx.HTTPStatusError):
        client.get_vehicles()


def test_sends_api_key_header_when_configured() -> None:
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    client = MbtaClient(base_url="https://api-v3.mbta.com", api_key="secret", http_client=http_client)

    client.get_vehicles()

    assert seen_headers.get("x-api-key") == "secret"


def test_raises_on_empty_base_url() -> None:
    with pytest.raises(ValueError):
        MbtaClient(base_url="   ")
