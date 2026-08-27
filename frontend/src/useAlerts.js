import { useEffect, useState } from "react";
import { backendOrigin } from "./backendOrigin";

// Alerts change far less often than vehicle positions or predictions, so a
// slower refresh is enough to stay current without polling for no reason.
const REFRESH_INTERVAL_MS = 60000;

export function useAlerts(stopId) {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    if (!stopId) {
      setAlerts([]);
      return undefined;
    }

    let cancelled = false;

    function load() {
      fetch(`${backendOrigin()}/api/stops/${stopId}/alerts`)
        .then((response) => response.json())
        .then((data) => {
          if (!cancelled) setAlerts(data);
        })
        .catch(() => {
          if (!cancelled) setAlerts([]);
        });
    }

    load();
    const interval = setInterval(load, REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [stopId]);

  return { alerts };
}
