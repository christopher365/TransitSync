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


STOP_PAYLOAD = {
    "data": [
        {
            "id": "place-pktrm",
            "type": "stop",
            "attributes": {
                "name": "Park Street",
                "latitude": 42.3564,
                "longitude": -71.0624,
                "wheelchair_boarding": 1,
            },
        },
        {
            "id": "place-broken",
            "type": "stop",
            "attributes": {
                # missing "name" on purpose: a malformed record to be skipped.
                "latitude": 42.0,
                "longitude": -71.0,
            },
        },
    ]
}


def test_get_stops_parses_well_formed_records_and_filters_by_route_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/stops"
        assert request.url.params["filter[route_type]"] == "0,1"
        return httpx.Response(200, json=STOP_PAYLOAD)

    client = make_client(handler)

    readings = client.get_stops()

    assert len(readings) == 1  # the malformed second record is dropped
    assert readings[0].stop_id == "place-pktrm"
    assert readings[0].name == "Park Street"


PREDICTION_PAYLOAD = {
    "data": [
        {
            "id": "prediction-1",
            "type": "prediction",
            "attributes": {
                "arrival_time": "2026-08-25T12:05:00-04:00",
                "departure_time": "2026-08-25T12:06:00-04:00",
                "status": None,
            },
            "relationships": {
                "route": {"data": {"id": "Red", "type": "route"}},
                "trip": {"data": {"id": "trip-1", "type": "trip"}},
                "vehicle": {"data": {"id": "y1234", "type": "vehicle"}},
            },
        }
    ]
}


def test_get_predictions_parses_well_formed_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/predictions"
        assert request.url.params["filter[stop]"] == "place-pktrm"
        return httpx.Response(200, json=PREDICTION_PAYLOAD)

    client = make_client(handler)

    readings = client.get_predictions("place-pktrm")

    assert len(readings) == 1
    reading = readings[0]
    assert reading.route_id == "Red"
    assert reading.vehicle_id == "y1234"
    assert reading.arrival_time == datetime.fromisoformat("2026-08-25T12:05:00-04:00")


def test_get_predictions_raises_on_empty_stop_id() -> None:
    client = make_client(lambda request: httpx.Response(200, json={"data": []}))

    with pytest.raises(ValueError):
        client.get_predictions("   ")


ALERT_PAYLOAD = {
    "data": [
        {
            "id": "12345",
            "type": "alert",
            "attributes": {
                "header": "Orange Line: delays of up to 10 minutes due to signal problems",
                "effect": "DELAY",
                "severity": 5,
                "cause": "SIGNAL_PROBLEM",
            },
        },
        {
            "id": "67890",
            "type": "alert",
            "attributes": {
                # missing "header" on purpose: a malformed record to be skipped.
                "effect": "ELEVATOR_CLOSURE",
            },
        },
    ]
}


def test_get_alerts_parses_well_formed_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/alerts"
        assert request.url.params["filter[stop]"] == "place-bbsta"
        assert request.url.params["filter[datetime]"] == "NOW"
        return httpx.Response(200, json=ALERT_PAYLOAD)

    client = make_client(handler)

    readings = client.get_alerts("place-bbsta")

    assert len(readings) == 1  # the malformed second record is dropped
    assert readings[0].effect == "DELAY"
    assert readings[0].severity == 5


def test_get_alerts_raises_on_empty_stop_id() -> None:
    client = make_client(lambda request: httpx.Response(200, json={"data": []}))

    with pytest.raises(ValueError):
        client.get_alerts("")
