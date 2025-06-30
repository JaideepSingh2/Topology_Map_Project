import React, { useState, useEffect, useCallback } from 'react';
import TopologyViewer from './components/TopologyViewer.js'; 
import Legend from './components/Legend.js'; 

function App() {
  const [topologyData, setTopologyData] = useState(null); // Data currently being displayed
  const [fetchingNewData, setFetchingNewData] = useState(false); // Indicates if a new fetch is in progress
  const [error, setError] = useState(null);
  const [backendUrl, setBackendUrl] = useState('http://localhost:5000'); // Default backend URL
  const [initialLoad, setInitialLoad] = useState(true); // Flag for the very first load

  // Function to fetch the full topology data from the backend
  const fetchTopologyData = useCallback(async () => {
    if (!topologyData) {
      setInitialLoad(true);
    }
    setFetchingNewData(true);
    setError(null);

    try {
      const response = await fetch(`${backendUrl}/api/topology_data`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setTopologyData(data);
    } catch (e) {
      console.error("Failed to fetch topology data:", e);
      setError("Failed to load topology data. Please ensure the backend is running and accessible.");
    } finally {
      setFetchingNewData(false);
      setInitialLoad(false);
    }
  }, [backendUrl, topologyData]);

  // Set up interval for periodic updates
  useEffect(() => {
    fetchTopologyData(); // Fetch immediately on component mount

    const intervalId = setInterval(fetchTopologyData, 5000); // Refresh every 5 seconds

    // Clear interval on component unmount
    return () => clearInterval(intervalId);
  }, [fetchTopologyData]);

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center p-4 font-inter">
      <h1 className="text-3xl font-bold text-gray-800 mb-6 rounded-md p-3 shadow-lg bg-white">
        Cloud Architecture Topology Viewer
      </h1>

      <div className="w-full max-w-6xl bg-white rounded-lg shadow-xl p-6 mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-700">Topology Overview</h2>
          <div className="flex items-center space-x-4">
            <input
              type="text"
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              placeholder="Backend URL (e.g., http://localhost:5000)"
              className="p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={fetchTopologyData}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105"
              disabled={fetchingNewData}
            >
              {fetchingNewData ? 'Fetching New Data...' : 'Refresh Now'}
            </button>
          </div>
        </div>

        <TopologyViewer
          topologyData={topologyData}
          fetchingNewData={fetchingNewData}
          initialLoad={initialLoad}
          error={error}
          backendUrl={backendUrl} // Pass backendUrl if images were dependent on it (though now they are static)
        />
      </div>

      {/* Render the Legend component */}
      <Legend healthColorMap={topologyData?.health_color_map} />
    </div>
  );
}

export default App;
