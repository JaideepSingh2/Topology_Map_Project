import React from 'react';

function Legend({ healthColorMap }) {
  if (!healthColorMap) {
    return (
      <div className="w-full max-w-6xl bg-white rounded-lg shadow-xl p-6">
        <h2 className="text-xl font-semibold text-gray-700 mb-4">Component Health Status Legend</h2>
        <p className="text-gray-500">No health status legend available.</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl bg-white rounded-lg shadow-xl p-6">
      <h2 className="text-xl font-semibold text-gray-700 mb-4">Component Health Status Legend</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {Object.entries(healthColorMap).map(([status, color]) => (
          <div key={status} className="flex items-center space-x-2 p-2 bg-gray-50 rounded-md shadow-sm">
            <span className="w-4 h-4 rounded-full" style={{ backgroundColor: color }}></span>
            <span className="text-gray-700 capitalize">{status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Legend;
