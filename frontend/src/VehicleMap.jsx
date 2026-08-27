import { useEffect } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

const BOSTON_CENTER = [42.3601, -71.0589];

// What each MBTA current_status value actually means, in plain language,
// plus the color we use to represent it consistently between the map
// markers and the Legend component.
export const STATUS_INFO = {
  IN_TRANSIT_TO: { label: "Moving", color: "#2ecc71" },
  STOPPED_AT: { label: "Stopped at a stop", color: "#e67e22" },
  INCOMING_AT: { label: "Approaching a stop", color: "#3498db" },
};
const UNKNOWN_STATUS = { label: "Status unknown", color: "#95a5a6" };

// A small colored circle instead of Leaflet's default pin image: it's what
// lets each marker communicate vehicle status at a glance, and sidesteps a
// well-known Leaflet+bundler issue where the default pin's image paths
// don't resolve correctly once Vite bundles everything.
function vehicleIcon(status) {
  const { color } = STATUS_INFO[status] ?? UNKNOWN_STATUS;
  return L.divIcon({
    className: "vehicle-marker",
    html: `<span style="background:${color}"></span>`,
    iconSize: [16, 16],
  });
}

const stopIcon = L.divIcon({
  className: "stop-marker",
  html: "<span></span>",
  iconSize: [20, 20],
});

// A selected stop should visibly move the map to where it is, not just add
// a marker somewhere the user may not be looking. react-leaflet's map
// instance is only reachable via this hook, from a component rendered
// inside <MapContainer> — it can't be done from VehicleMap's own props.
function FlyToStop({ stop }) {
  const map = useMap();

  useEffect(() => {
    if (stop) {
      map.flyTo([stop.latitude, stop.longitude], 16);
    }
  }, [stop, map]);

  return null;
}

// Same idea as FlyToStop, but for a single isolated vehicle. Depends only
// on vehicle_id (not the vehicle object itself, which gets a new reference
// on every ~5s position update) — otherwise the map would re-fly and jump
// every time that vehicle's position refreshed, instead of just once when
// it's first selected.
function FlyToVehicle({ vehicle }) {
  const map = useMap();

  useEffect(() => {
    if (vehicle) {
      map.flyTo([vehicle.latitude, vehicle.longitude], 16);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle?.vehicle_id, map]);

  return null;
}

export function VehicleMap({ vehiclesById, selectedStop, highlightedRouteIds, selectedVehicleId }) {
  const allVehicles = Object.values(vehiclesById);
  const isolatedVehicle = selectedVehicleId ? vehiclesById[selectedVehicleId] : null;

  // Isolating one specific vehicle (clicked from a prediction) takes
  // priority over the broader route-level filter; falling back to the
  // route filter if the vehicle isn't found (e.g. not yet live-tracked)
  // avoids the map going misleadingly blank.
  const vehicles = isolatedVehicle
    ? [isolatedVehicle]
    : highlightedRouteIds
      ? allVehicles.filter((vehicle) => highlightedRouteIds.has(vehicle.route_id))
      : allVehicles;

  return (
    <MapContainer center={BOSTON_CENTER} zoom={12} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FlyToStop stop={selectedStop} />
      <FlyToVehicle vehicle={isolatedVehicle} />
      <MarkerClusterGroup chunkedLoading maxClusterRadius={60}>
        {vehicles.map((vehicle) => (
          <Marker
            key={vehicle.vehicle_id}
            position={[vehicle.latitude, vehicle.longitude]}
            icon={vehicleIcon(vehicle.current_status)}
          >
            <Popup>
              <strong>Vehicle {vehicle.vehicle_id}</strong>
              <br />
              Route: {vehicle.route_id ?? "unknown"}
              <br />
              {(STATUS_INFO[vehicle.current_status] ?? UNKNOWN_STATUS).label}
            </Popup>
          </Marker>
        ))}
      </MarkerClusterGroup>
      {selectedStop && (
        <Marker
          position={[selectedStop.latitude, selectedStop.longitude]}
          icon={stopIcon}
          zIndexOffset={1000}
        >
          <Popup>{selectedStop.name}</Popup>
        </Marker>
      )}
    </MapContainer>
  );
}
