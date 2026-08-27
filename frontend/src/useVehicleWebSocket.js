import { useEffect, useState } from "react";
import { applyVehicleUpdate } from "./vehicleState";

const RECONNECT_DELAY_MS = 3000;

function defaultWsUrl() {
  // Deriving the host from the page's own URL (rather than hardcoding
  // "localhost") means a phone or another PC on the same network can load
  // this page via the host machine's LAN IP and the WebSocket connects to
  // that same address automatically — no per-device configuration needed.
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.hostname}:8000/ws/vehicles`;
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
