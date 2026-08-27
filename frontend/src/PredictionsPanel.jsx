import { formatArrival, routeColor } from "./predictionFormat";

export function PredictionsPanel({ predictions, isLoading }) {
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
