import { useEffect, useState } from "react";
import { backendOrigin } from "./backendOrigin";

const DEBOUNCE_MS = 300;

export function StopSearch({ selectedStop, onSelectStop, onClear }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return undefined;
    }

    // Waits for typing to pause before firing a request, so searching
    // "Park Street" doesn't fire one request per keystroke.
    const timer = setTimeout(() => {
      fetch(`${backendOrigin()}/api/stops?q=${encodeURIComponent(query)}`)
        .then((response) => response.json())
        .then(setResults)
        .catch(() => setResults([]));
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query]);

  function handleSelect(stop) {
    onSelectStop(stop);
    setQuery(stop.name);
    setResults([]);
  }

  function handleClear() {
    setQuery("");
    setResults([]);
    onClear();
  }

  return (
    <div className="stop-search">
      <label htmlFor="stop-search-input">Find your stop</label>
      <div className="stop-search-input-row">
        <input
          id="stop-search-input"
          type="text"
          placeholder="e.g. Park Street"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {selectedStop && (
          <button className="clear-button" onClick={handleClear} aria-label="Clear selected stop">
            ✕
          </button>
        )}
      </div>
      {results.length > 0 && (
        <ul className="stop-results">
          {results.map((stop) => (
            <li key={stop.id}>
              <button onClick={() => handleSelect(stop)}>{stop.name}</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
