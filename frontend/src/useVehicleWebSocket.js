import { useEffect, useState } from "react";
import { backendOrigin } from "./backendOrigin";
import { applyVehicleUpdate } from "./vehicleState";

const RECONNECT_DELAY_MS = 3000;

function defaultWsUrl() {
  // Reuses the same host-derivation as REST calls (see backendOrigin), just
  // swapped to the ws(s):// scheme a WebSocket needs.
  return `${backendOrigin().replace(/^http/, "ws")}/ws/vehicles`;
}

export function useVehicleWebSocket(url = import.meta.env.VITE_WS_URL || defaultWsUrl()) {
  const [vehiclesById, setVehiclesById] = useState({});
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let socket;
    let reconnectTimer;
    let cancelled = false;

    function connect() {
      socket = new WebSocket(url);

      socket.onopen = () => setIsConnected(true);

      socket.onmessage = (event) => {
        const position = JSON.parse(event.data);
        setVehiclesById((current) => applyVehicleUpdate(current, position));
      };

      socket.onclose = () => {
        setIsConnected(false);
        // The backend can restart, or a network blip can drop the
        // connection; a dashboard meant to run continuously should recover
        // on its own rather than requiring a manual page refresh.
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      socket.onerror = () => socket.close();
    }

    connect();

    return () => {
      // Prevents a reconnect attempt (and the setState that would follow
      // it) from firing after this component has already unmounted.
      cancelled = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [url]);

  return { vehiclesById, isConnected };
}
