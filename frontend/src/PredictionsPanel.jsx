import { useEffect, useState } from "react";
import { backendOrigin } from "./backendOrigin";
import { formatArrival, routeColor } from "./predictionFormat";

const REFRESH_INTERVAL_MS = 15000;

export function PredictionsPanel({ stop }) {
  const [predictions, setPredictions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    function load() {
      fetch(`${backendOrigin()}/api/stops/${stop.id}/predictions`)
        .then((response) => response.json())
        .then((data) => {
          if (!cancelled) {
            setPredictions(data);
            setIsLoading(false);
          }
        })
        .catch(() => {
          if (!cancelled) setIsLoading(false);
        });
    }

    setIsLoading(true);
    load();
    // Predictions are fetched on demand (REST), not streamed — polling on a
    // plain interval is the simplest way to keep them "live" while a rider
    // is actually looking at this one stop, without a dedicated WebSocket
    // channel for something only one viewer at a time typically cares about.
    const interval = setInterval(load, REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [stop.id]);

  return (
    <div className="predictions-panel">
      <div className="predictions-header">Upcoming arrivals</div>
      {isLoading && <p className="predictions-empty">Loading…</p>}
      {!isLoading && predictions.length === 0 && (
        <p className="predictions-empty">No upcoming arrivals right now.</p>
      )}
      <ul className="predictions-list">
        {predictions.map((prediction, index) => (
          <li key={`${prediction.trip_id}-${index}`} className="prediction-row">
            <span className="route-badge" style={{ background: routeColor(prediction.route_id) }}>
              {prediction.route_id ?? "?"}
            </span>
            <span className="prediction-time">{formatArrival(prediction)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
