import { STATUS_INFO } from "./VehicleMap";

export function Legend() {
  return (
    <div className="legend">
      <div className="legend-title">Vehicle status</div>
      {Object.values(STATUS_INFO).map(({ label, color }) => (
        <div className="legend-row" key={label}>
          <span className="legend-swatch" style={{ background: color }} />
          {label}
        </div>
      ))}
      <div className="legend-row legend-hint">Numbers = clustered vehicles. Click to zoom in.</div>
    </div>
  );
}
