import { useState } from "react";
import "./App.css";
import { VehicleMap } from "./VehicleMap";
import { Legend } from "./Legend";
import { StopSearch } from "./StopSearch";
import { PredictionsPanel } from "./PredictionsPanel";
import { useVehicleWebSocket } from "./useVehicleWebSocket";
import { usePredictions } from "./usePredictions";
import { distinctRouteIds } from "./predictionFormat";

function App() {
  const { vehiclesById, isConnected } = useVehicleWebSocket();
  const [selectedStop, setSelectedStop] = useState(null);
  const { predictions, isLoading: predictionsLoading } = usePredictions(selectedStop?.id);
  const vehicleCount = Object.keys(vehiclesById).length;

  // Only start filtering once real predictions have actually loaded —
  // otherwise selecting a stop would flash the map to empty for a moment,
  // or stay empty forever for a stop with no active service right now.
  const highlightedRouteIds =
    selectedStop && !predictionsLoading && predictions.length > 0
      ? distinctRouteIds(predictions)
      : null;

  return (
    <div className="app">
      <header className="header">
        <div className="header-title-row">
          <h1>TransitSync</h1>
          <span className={`status-pill ${isConnected ? "connected" : "disconnected"}`}>
            <span className="status-dot" />
            {isConnected ? "Live" : "Reconnecting…"}
          </span>
        </div>
        <p className="header-subtitle">
          Search a stop to see real upcoming arrivals and single out its vehicles on the map, or
          watch every MBTA vehicle currently running in the Boston area. Tracking{" "}
          <strong>{vehicleCount}</strong> vehicles.
        </p>
      </header>
      <div className="body">
        <aside className="sidebar">
          <StopSearch
            selectedStop={selectedStop}
            onSelectStop={setSelectedStop}
            onClear={() => setSelectedStop(null)}
          />
          {selectedStop && (
            <PredictionsPanel predictions={predictions} isLoading={predictionsLoading} />
          )}
          <Legend />
        </aside>
        <div className="map-container">
          {highlightedRouteIds && (
            <div className="map-filter-banner">
              Showing only {Array.from(highlightedRouteIds).join(", ")} vehicles serving{" "}
              {selectedStop.name}
            </div>
          )}
          <VehicleMap
            vehiclesById={vehiclesById}
            selectedStop={selectedStop}
            highlightedRouteIds={highlightedRouteIds}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
