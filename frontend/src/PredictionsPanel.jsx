import { formatArrival, routeColor } from "./predictionFormat";

export function PredictionsPanel({ predictions, isLoading, selectedVehicleId, onSelectVehicle }) {
  return (
    <div className="predictions-panel">
      <div className="predictions-header">Upcoming arrivals</div>
      {isLoading && <p className="predictions-empty">Loading…</p>}
      {!isLoading && predictions.length === 0 && (
        <p className="predictions-empty">No upcoming arrivals right now.</p>
      )}
      <ul className="predictions-list">
        {predictions.map((prediction, index) => {
          // A prediction MBTA hasn't assigned a live vehicle to yet (common
          // for arrivals further in the future) has nothing to isolate.
          const hasVehicle = prediction.vehicle_id != null;
          const isSelected = hasVehicle && prediction.vehicle_id === selectedVehicleId;
          const badge = (
            <span className="route-badge" style={{ background: routeColor(prediction.route_id) }}>
              {prediction.route_id ?? "?"}
            </span>
          );

          return (
            <li
              key={`${prediction.trip_id}-${index}`}
              className={`prediction-row ${isSelected ? "selected" : ""}`}
            >
              {hasVehicle ? (
                <button
                  className="prediction-button"
                  onClick={() => onSelectVehicle(isSelected ? null : prediction.vehicle_id)}
                >
                  {badge}
                  <span className="prediction-time">{formatArrival(prediction)}</span>
                  <span className="prediction-hint">{isSelected ? "Showing ✓" : "Show on map"}</span>
                </button>
              ) : (
                <span className="prediction-static">
                  {badge}
                  <span className="prediction-time">{formatArrival(prediction)}</span>
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
