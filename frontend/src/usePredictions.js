import { useEffect, useState } from "react";
import { backendOrigin } from "./backendOrigin";
import { isStalePrediction } from "./predictionFormat";

const REFRESH_INTERVAL_MS = 15000;

// Centralized here (rather than inside PredictionsPanel) because the
// vehicle map also needs this data, to know which routes to highlight —
// fetching it once and sharing it avoids two components independently
// polling the same endpoint.
export function usePredictions(stopId) {
  const [predictions, setPredictions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!stopId) {
      setPredictions([]);
      setIsLoading(false);
      return undefined;
    }

    let cancelled = false;

    function load() {
      fetch(`${backendOrigin()}/api/stops/${stopId}/predictions`)
        .then((response) => response.json())
        .then((data) => {
          if (!cancelled) {
            // Filtered here, once, so every consumer (the predictions list,
            // and the map's route-highlighting derived from it) only ever
            // sees predictions worth trusting.
            setPredictions(data.filter((prediction) => !isStalePrediction(prediction)));
            setIsLoading(false);
          }
        })
        .catch(() => {
          if (!cancelled) setIsLoading(false);
        });
    }

    setIsLoading(true);
    load();
    const interval = setInterval(load, REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [stopId]);

  return { predictions, isLoading };
}
