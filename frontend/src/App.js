import React, { useState } from "react";
import "./App.css";

function App() {
  const [fromInput, setFromInput] = useState("");
  const [from, setFrom] = useState("");
  const [toInput, setToInput] = useState("");
  const [to, setTo] = useState("");

  const [fromOptions, setFromOptions] = useState([]);
  const [toOptions, setToOptions] = useState([]);
  const [journeys, setJourneys] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showFromDropdown, setShowFromDropdown] = useState(false);
  const [showToDropdown, setShowToDropdown] = useState(false);

  // Simple debounce function
  const debounce = (func, delay) => {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => func(...args), delay);
    };
  };

  // Fetch stations from TfL Search API
  const fetchStations = async (query, type) => {
    if (!query || query.length < 2) {
      if (type === "from") {
        setFromOptions([]);
        setShowFromDropdown(false);
      } else {
        setToOptions([]);
        setShowToDropdown(false);
      }
      return;
    }

    try {
      const apiUrl = `https://api.tfl.gov.uk/StopPoint/Search/${encodeURIComponent(query)}?modes=tube,dlr,overground,tram,national-rail,bus&maxResults=8`;
      
      const response = await fetch(apiUrl);
      const data = await response.json();

      if (data.matches && data.matches.length > 0) {
        const results = data.matches.map((match) => ({
          id: match.icsId || match.id,
          name: match.name || match.commonName,
        }));

        if (type === "from") {
          setFromOptions(results);
          setShowFromDropdown(true);
        } else {
          setToOptions(results);
          setShowToDropdown(true);
        }
      } else {
        if (type === "from") {
          setFromOptions([]);
          setShowFromDropdown(false);
        } else {
          setToOptions([]);
          setShowToDropdown(false);
        }
      }
    } catch (err) {
      console.error("Error fetching stations:", err);
      if (type === "from") {
        setFromOptions([]);
        setShowFromDropdown(false);
      } else {
        setToOptions([]);
        setShowToDropdown(false);
      }
    }
  };

  const debouncedFetchFrom = debounce((q) => fetchStations(q, "from"), 300);
  const debouncedFetchTo = debounce((q) => fetchStations(q, "to"), 300);

  // Handle input changes
  const handleFromInputChange = (e) => {
    const value = e.target.value;
    setFromInput(value);
    setFrom("");
    
    if (value.length >= 2) {
      debouncedFetchFrom(value);
    } else {
      setFromOptions([]);
      setShowFromDropdown(false);
    }
  };

  const handleToInputChange = (e) => {
    const value = e.target.value;
    setToInput(value);
    setTo("");
    
    if (value.length >= 2) {
      debouncedFetchTo(value);
    } else {
      setToOptions([]);
      setShowToDropdown(false);
    }
  };

  // Handle station selection
  const handleFromSelect = (stationName) => {
    setFrom(stationName);
    setFromInput(stationName);
    setShowFromDropdown(false);
  };

  const handleToSelect = (stationName) => {
    setTo(stationName);
    setToInput(stationName);
    setShowToDropdown(false);
  };

  // Close dropdowns when clicking outside
  const handleClickOutside = () => {
    setShowFromDropdown(false);
    setShowToDropdown(false);
  };

  // Fetch journey from backend
  const fetchJourney = async () => {
    if (!from || !to) {
      setError("Please select both origin and destination from the dropdown.");
      return;
    }

    setLoading(true);
    setError("");
    setJourneys([]);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/journey?from_=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`
      );
      const data = await response.json();

      if (data.error) {
        setError(data.error);
      } else {
        setJourneys(data.journeys || []);
      }
    } catch (err) {
      setError("Error fetching journey data. Make sure your backend server is running.");
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App" onClick={handleClickOutside}>
      <h2>London Commute Dashboard</h2>

      <div className="inputs">
        {/* FROM input */}
        <div className="input-container">
          <input
            type="text"
            placeholder="From (e.g. East Croydon, Paddington, etc.)"
            value={fromInput}
            onChange={handleFromInputChange}
            onFocus={() => fromOptions.length > 0 && setShowFromDropdown(true)}
          />
          {showFromDropdown && fromOptions.length > 0 && (
            <div className="dropdown" onClick={(e) => e.stopPropagation()}>
              {fromOptions.map((opt, index) => (
                <div
                  key={opt.id || index}
                  className="dropdown-option"
                  onClick={() => handleFromSelect(opt.name)}
                >
                  {opt.name}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* TO input */}
        <div className="input-container">
          <input
            type="text"
            placeholder="To (e.g. Oxford Circus, Victoria, etc.)"
            value={toInput}
            onChange={handleToInputChange}
            onFocus={() => toOptions.length > 0 && setShowToDropdown(true)}
          />
          {showToDropdown && toOptions.length > 0 && (
            <div className="dropdown" onClick={(e) => e.stopPropagation()}>
              {toOptions.map((opt, index) => (
                <div
                  key={opt.id || index}
                  className="dropdown-option"
                  onClick={() => handleToSelect(opt.name)}
                >
                  {opt.name}
                </div>
              ))}
            </div>
          )}
        </div>

        <button onClick={fetchJourney} disabled={loading}>
          {loading ? "Loading..." : "Get Journey"}
        </button>
      </div>

      {loading && <p>Loading journey information...</p>}
      {error && <p className="error-message">{error}</p>}

      {journeys.length > 0 && (
        <div className="results">
          <h3>Available Journeys:</h3>
          {journeys.map((j, idx) => (
            <div key={idx} className="journey-card">
              <strong>Duration:</strong> {j.duration} minutes<br />
              <strong>Departure:</strong> {new Date(j.startTime).toLocaleTimeString()}<br />
              <strong>Arrival:</strong> {new Date(j.arrivalTime).toLocaleTimeString()}
              <div className="legs">
                <strong>Route:</strong>
                <ul>
                  {j.legs.map((leg, i) => (
                    <li key={i}>
                      <span className="mode">{leg.mode}</span>: {leg.departure} → {leg.arrival}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;