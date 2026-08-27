import "./App.css";
import { VehicleMap } from "./VehicleMap";
import { Legend } from "./Legend";
import { useVehicleWebSocket } from "./useVehicleWebSocket";

function App() {
  const { vehiclesById, isConnected } = useVehicleWebSocket();
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
          Live positions of every MBTA bus, train, and shuttle currently running in the Boston
          area — updated automatically every few seconds. Currently tracking{" "}
          <strong>{vehicleCount}</strong> vehicles.
        </p>
      </header>
      <div className="map-container">
        <VehicleMap vehiclesById={vehiclesById} />
        <Legend />
      </div>
    </div>
  );
}

export default App;
