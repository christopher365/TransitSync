import { useState } from "react";
import "./App.css";
import { VehicleMap } from "./VehicleMap";
import { Legend } from "./Legend";
import { StopSearch } from "./StopSearch";
import { PredictionsPanel } from "./PredictionsPanel";
import { useVehicleWebSocket } from "./useVehicleWebSocket";

function App() {
  const { vehiclesById, isConnected } = useVehicleWebSocket();
  const [selectedStop, setSelectedStop] = useState(null);
  const vehicleCount = Object.keys(vehiclesById).length;

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
          Search a stop to see real upcoming arrivals, or watch every MBTA vehicle currently
          running in the Boston area. Tracking <strong>{vehicleCount}</strong> vehicles.
        </p>
      </header>
      <div className="body">
        <aside className="sidebar">
          <StopSearch
            selectedStop={selectedStop}
            onSelectStop={setSelectedStop}
            onClear={() => setSelectedStop(null)}
          />
          {selectedStop && <PredictionsPanel stop={selectedStop} />}
          <Legend />
        </aside>
        <div className="map-container">
          <VehicleMap vehiclesById={vehiclesById} selectedStop={selectedStop} />
        </div>
      </div>
    </div>
  );
}

export default App;
