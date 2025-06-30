import React, { lazy, Suspense, useCallback } from 'react';

// Lazy-load the Plotly component
const LazyPlotly = lazy(() => import('react-plotly.js'));


const serverImage = "/images/Server.png";
const switchImage = "/images/Switch.png";
const storageImage = "/images/Storage.png";
const backupImage = "/images/Backup.png";

function TopologyViewer({ topologyData, fetchingNewData, initialLoad, error, backendUrl }) {

  // Function to prepare Plotly data and layout
  const generatePlotlyGraph = useCallback(() => {
    if (!topologyData) return { data: [], layout: {} };

    const { servers, network_switches, storage, backup, private_cloud, health_color_map } = topologyData;

    const figData = [];
    const images_to_add = [];
    const node_positions = {};

    const left_x = 0.15;
    const middle_x = 0.5;
    const right_x = 0.85;
    const y_step = 0.15;

    // Helper to add nodes
    const addNodes = (nodes, x_pos, image_src, type_name) => {
      nodes.forEach((node, i) => {
        const y_node = 0.9 - i * y_step; // Base Y position for the node
        node_positions[node.id] = { x: x_pos, y: y_node };

        const hoverText = `
          <b>${node.name}</b><br>
          ID: ${node.id}<br>
          Type: ${node.type || type_name}<br>
          Role: ${node.role || 'N/A'}<br>
          Health: <span style="color:${health_color_map[node.health] || 'gray'};">${node.health}</span><br>
          Power: ${node.power_status || 'N/A'}<br>
          MAC: ${node.mac || 'N/A'}<br>
          Location: ${node.location || 'N/A'}<br>
          ${node.ip_address ? `IP: ${node.ip_address}<br>` : ''}
          ${node.cpu_utilization ? `CPU: ${node.cpu_utilization}%<br>` : ''}
        `;

        const y_text = y_node - 0.05; // Adjusted Y for text: moved down by 0.05 units from node's center
        const y_image = y_node + 0.03; // Image slightly above the center of the node's base Y


        figData.push({
          x: [x_pos],
          y: [y_text], // Use adjusted y for text
          mode: 'markers+text',
          name: node.name,
          text: [node.name],
          textposition: "middle center", // Keeping this as 'middle center' and using `y_text` for vertical positioning
          marker: { size: 30, color: 'rgba(0,0,0,0)' }, // Transparent marker
          hovertext: hoverText,
          hoverinfo: 'text',
          showlegend: false
        });

        images_to_add.push({
          source: image_src,
          xref: "x", yref: "y",
          x: x_pos, y: y_image, // Use adjusted y for image
          sizex: 0.08, sizey: 0.08, // Image size
          xanchor: "center", yanchor: "middle",
          layer: "above"
        });
      });
    };

    // Add Servers
    addNodes(servers, left_x, serverImage, 'Server');

    // Add Switches
    addNodes(network_switches, middle_x, switchImage, 'Switch');

    // Add Storage
    addNodes(storage, right_x, storageImage, 'Storage');

    // Add Backup 
    backup.forEach((node, i) => {
      const y_node = 0.9 - (storage.length + i) * y_step; 
      node_positions[node.id] = { x: right_x, y: y_node };

      const hoverText = `
        <b>${node.name}</b><br>
        ID: ${node.id}<br>
        Type: ${node.type || 'Backup'}<br>
        Role: ${node.role || 'N/A'}<br>
        Health: <span style="color:${health_color_map[node.health] || 'gray'};">${node.health}</span><br>
        Power: ${node.power_status || 'N/A'}<br>
        MAC: ${node.mac || 'N/A'}<br>
        Location: ${node.location || 'N/A'}
      `;

      
      const y_text = y_node - 0.05;
      const y_image = y_node + 0.03;

      figData.push({
        x: [right_x],
        y: [y_text], 
        mode: 'markers+text',
        name: node.name,
        text: [node.name],
        textposition: "middle center",
        marker: { size: 30, color: 'rgba(0,0,0,0)' },
        hovertext: hoverText,
        hoverinfo: 'text',
        showlegend: false
      });

      images_to_add.push({
        source: backupImage,
        xref: "x", yref: "y",
        x: right_x, y: y_image, 
        sizex: 0.08, sizey: 0.08,
        xanchor: "center", yanchor: "middle",
        layer: "above"
      });
    });


    // Helper to add edges
    const addEdges = (components) => {
      components.forEach(comp => {
        comp.connected_switches?.forEach(conn => {
          const switch_id = conn.switch_id;
          if (node_positions[comp.id] && node_positions[switch_id]) {
            const { x: x0, y: y0 } = node_positions[comp.id];
            const { x: x1, y: y1 } = node_positions[switch_id];
            figData.push({
              x: [x0, x1],
              y: [y0, y1],
              mode: 'lines',
              line: { color: health_color_map[comp.health] || 'gray', width: 3 },
              name: `${comp.name} -> ${switch_id}`,
              text: `Port: ${conn.port}`,
              hoverinfo: 'text',
              showlegend: false
            });
          }
        });
      });
    };

    addEdges(servers);
    addEdges(storage);
    addEdges(backup);

    const cloudName = private_cloud?.name || 'Private Cloud';

    const layout = {
      title: `${cloudName} Architecture`,
      showlegend: false,
      hovermode: 'closest',
      xaxis: { showgrid: false, zeroline: false, showticklabels: false, range: [0, 1] },
      yaxis: { showgrid: false, zeroline: false, showticklabels: false, range: [0, 1] },
      margin: { l: 20, r: 20, t: 60, b: 20 },
      plot_bgcolor: '#f8f8f8',
      paper_bgcolor: '#ffffff',
      images: images_to_add,
      height: 700, 
      autosize: true, 
      responsive: true,
      annotations: [
        {
          x: left_x,
          y: 1,
          xref: 'paper',
          yref: 'paper',
          text: 'Servers',
          showarrow: false,
          font: { size: 16, color: '#333' }
        },
        {
          x: middle_x,
          y: 1,
          xref: 'paper',
          yref: 'paper',
          text: 'Network Switches',
          showarrow: false,
          font: { size: 16, color: '#333' }
        },
        {
          x: right_x,
          y: 1,
          xref: 'paper',
          yref: 'paper',
          text: 'Storage & Backup',
          showarrow: false,
          font: { size: 16, color: '#333' }
        }
      ]
    };

    return { data: figData, layout };
  }, [topologyData]); 

  const { data: plotlyData, layout: plotlyLayout } = generatePlotlyGraph();

  return (
    <>
      {/* Loading overlay for the *initial* load only, or if an error prevents displaying anything */}
      {(initialLoad && fetchingNewData) || error ? (
        <div className="flex items-center justify-center p-8 min-h-[600px] flex-col">
          {error ? (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
              <strong className="font-bold">Error!</strong>
              <span className="block sm:inline ml-2">{error}</span>
              <p className="text-sm mt-1">Please ensure your backend server is running and accessible at {backendUrl}.</p>
            </div>
          ) : (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
              <p className="ml-4 text-lg text-gray-600">Loading topology data....</p>
            </>
          )}
        </div>
      ) : null}

      {/* Display the Plotly graph if topologyData exists, wrapped in Suspense for lazy loading */}
      {topologyData && !error && (
        <div className="relative w-full overflow-hidden" style={{ minHeight: '600px' }}>
          <Suspense fallback={
              <div className="flex items-center justify-center p-8 h-full">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
                  <p className="ml-4 text-lg text-gray-600">Loading visualization library...</p>
              </div>
          }>
            <LazyPlotly
              data={plotlyData}
              layout={plotlyLayout}
              config={{
                responsive: true,
                displayModeBar: false // Hide Plotly's default mode bar
              }}
              className="w-full h-full"
            />
          </Suspense>
           {/* Overlay loading indicator if new data is being fetched but old data is visible */}
          {/* {fetchingNewData && !initialLoad && (
            <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10 rounded-lg">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
              <p className="ml-4 text-lg text-gray-600">Updating topology...</p>
            </div>
          )} */}
        </div>
      )}
    </>
  );
}

export default TopologyViewer;
