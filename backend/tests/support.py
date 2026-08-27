class StubMbtaClient:
    """A test double standing in for MbtaClient across app-level tests —
    returns canned data instead of making real HTTP calls, so building a
    test app never depends on the network being reachable.
    """

    def __init__(self, vehicles=None, stops=None, predictions=None, alerts=None):
        self._vehicles = vehicles or []
        self._stops = stops or []
        self._predictions = predictions or []
        self._alerts = alerts or []

    def get_vehicles(self):
        return self._vehicles

    def get_stops(self):
        return self._stops

    def get_predictions(self, stop_id):
        return self._predictions

    def get_alerts(self, stop_id):
        return self._alerts
