import json
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import plotly.graph_objects as go
import plotly.io as pio

# Health Status Colour Mapping
health_colour_map = {
    "healthy": "green",
    "degraded": "orange",
    "critical": "red",
    "unknown": "gray"
}

json_path = "HPE.json"
output_path = "HPE_topology.html"

def generate_interactive_topology():
    with open(json_path, "r") as file:
        data = json.load(file)

    # Check if required sections exist
    required_sections = ["private_cloud", "servers", "network_switches", "storage", "backup"]
    for section in required_sections:
        if section not in data:
            print(f"Error: '{section}' section not found in {json_path}. Please check the JSON structure.")
            return  

    # Create a figure
    fig = go.Figure()
    node_positions = {}
    
    # Add nodes for each component type
    node_count = 0
    
    # Add compute nodes
    for i, server in enumerate(data["servers"]):
        x = 0.2
        y = 0.8 - (i * 0.15)
        node_positions[server["id"]] = (x, y)
        
        # Create hover text with detailed information
        hover_text = f"""
        <b>{server["name"]}</b><br>
        ID: {server["id"]}<br>
        Type: {server["type"]}<br>
        Role: {server["role"]}<br>
        Health: {server["health"]}<br>
        Power: {server["power_status"]}<br>
        CPU: {server["cpu_utilization"]}<br>
        MAC: {server["mac"]}<br>
        Location: {server["metadata"]["location"]}<br>
        IP: {server["metadata"]["ip_address"]}
        """
        
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode='markers+text',
            name=server["name"],
            text=[server["name"]],
            textposition="bottom center",
            marker=dict(
                size=30,
                symbol='square',
                color=health_colour_map.get(server["health"], "gray")
            ),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=True
        ))
        node_count += 1
    
    # Add storage nodes
    for i, storage in enumerate(data["storage"]):
        x = 0.2
        y = 0.3 - (i * 0.15)
        node_positions[storage["id"]] = (x, y)
        
        hover_text = f"""
        <b>{storage["name"]}</b><br>
        ID: {storage["id"]}<br>
        Type: {storage["type"]}<br>
        Role: {storage["role"]}<br>
        Health: {storage["health"]}<br>
        Power: {storage["power_status"]}<br>
        MAC: {storage["mac"]}<br>
        Location: {storage["metadata"]["location"]}
        """
        
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode='markers+text',
            name=storage["name"],
            text=[storage["name"]],
            textposition="bottom center",
            marker=dict(
                size=30,
                symbol='diamond',
                color=health_colour_map.get(storage["health"], "gray")
            ),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=True
        ))
        node_count += 1
    
    # Add network switches
    for i, switch in enumerate(data["network_switches"]):
        x = 0.5
        y = 0.6 - (i * 0.2)
        node_positions[switch["id"]] = (x, y)
        
        hover_text = f"""
        <b>{switch["name"]}</b><br>
        ID: {switch["id"]}<br>
        Type: {switch["switch_type"]}<br>
        Role: {switch["role"]}<br>
        Health: {switch["health"]}<br>
        Power: {switch["power_status"]}<br>
        MAC: {switch["mac"]}<br>
        Location: {switch["metadata"]["location"]}
        """
        
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode='markers+text',
            name=switch["name"],
            text=[switch["name"]],
            textposition="bottom center",
            marker=dict(
                size=30,
                symbol='circle',
                color=health_colour_map.get(switch["health"], "gray")
            ),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=True
        ))
        node_count += 1
    
    # Add backup nodes
    for i, backup in enumerate(data["backup"]):
        x = 0.2
        y = 0.1 - (i * 0.15)
        node_positions[backup["id"]] = (x, y)
        
        hover_text = f"""
        <b>{backup["name"]}</b><br>
        ID: {backup["id"]}<br>
        Type: {backup["type"]}<br>
        Role: {backup["role"]}<br>
        Health: {backup["health"]}<br>
        Power: {backup["power_status"]}<br>
        MAC: {backup["mac"]}<br>
        Location: {backup["metadata"]["location"]}
        """
        
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode='markers+text',
            name=backup["name"],
            text=[backup["name"]],
            textposition="bottom center",
            marker=dict(
                size=30,
                symbol='hexagon',
                color=health_colour_map.get(backup["health"], "gray")
            ),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=True
        ))
        node_count += 1
    
    # Add edges (connections) with improved hover information
    for server in data["servers"]:
        for conn in server.get("connected_switches", []):
            switch_id = conn["switch_id"]
            port = conn["port"]
            
            if server["id"] in node_positions and switch_id in node_positions:
                x0, y0 = node_positions[server["id"]]
                x1, y1 = node_positions[switch_id]
                
                # Find the switch name
                switch_name = ""
                for switch in data["network_switches"]:
                    if switch["id"] == switch_id:
                        switch_name = switch["name"]
                        break
                
                # Create a more visible connection with hover information
                fig.add_trace(go.Scatter(
                    x=[x0, x1], y=[y0, y1],
                    mode='lines',
                    line=dict(
                        color=health_colour_map.get(server["health"], "gray"),
                        width=3  # Make lines thicker
                    ),
                    name=f"{server['name']} → {switch_name}",
                    text=f"Port: {port}",
                    hovertext=f"<b>Connection Details:</b><br>From: {server['name']}<br>To: {switch_name}<br>Port: {port}<br>Type: {server['connection_type']}",
                    hoverinfo='text',
                    showlegend=False
                ))
                
                # Add a small node in the middle of the connection line
                mid_x = (x0 + x1) / 2
                mid_y = (y0 + y1) / 2
                
                fig.add_trace(go.Scatter(
                    x=[mid_x], y=[mid_y],
                    mode='markers',
                    marker=dict(
                        size=10,
                        symbol='circle',
                        color=health_colour_map.get(server["health"], "gray"),
                        line=dict(color="white", width=1)
                    ),
                    hovertext=f"<b>Connection Details:</b><br>From: {server['name']}<br>To: {switch_name}<br>Port: {port}<br>Type: {server['connection_type']}",
                    hoverinfo='text',
                    showlegend=False
                ))
    
    # Fix storage connections with improved hover information
    for storage in data["storage"]:
        for conn in storage.get("connected_switches", []):
            switch_id = conn["switch_id"]
            port = conn["port"]
            
            if storage["id"] in node_positions and switch_id in node_positions:
                x0, y0 = node_positions[storage["id"]]
                x1, y1 = node_positions[switch_id]
                
                # Find the switch name
                switch_name = ""
                for switch in data["network_switches"]:
                    if switch["id"] == switch_id:
                        switch_name = switch["name"]
                        break
                
                # Create a more visible connection with hover information
                fig.add_trace(go.Scatter(
                    x=[x0, x1], y=[y0, y1],
                    mode='lines',
                    line=dict(
                        color=health_colour_map.get(storage["health"], "gray"),
                        width=3  # Make lines thicker
                    ),
                    name=f"{storage['name']} → {switch_name}",
                    text=f"Port: {port}",
                    hovertext=f"<b>Connection Details:</b><br>From: {storage['name']}<br>To: {switch_name}<br>Port: {port}<br>Type: {storage['connection_type']}",
                    hoverinfo='text',
                    showlegend=False
                ))
                
                # Add a small node in the middle of the connection line
                mid_x = (x0 + x1) / 2
                mid_y = (y0 + y1) / 2
                
                fig.add_trace(go.Scatter(
                    x=[mid_x], y=[mid_y],
                    mode='markers',
                    marker=dict(
                        size=10,
                        symbol='circle',
                        color=health_colour_map.get(storage["health"], "gray"),
                        line=dict(color="white", width=1)
                    ),
                    hovertext=f"<b>Connection Details:</b><br>From: {storage['name']}<br>To: {switch_name}<br>Port: {port}<br>Type: {storage['connection_type']}",
                    hoverinfo='text',
                    showlegend=False
                ))
    
    for backup in data["backup"]:
        for conn in backup.get("connected_switches", []):
            switch_id = conn["switch_id"]
            port = conn["port"]
            
            if backup["id"] in node_positions and switch_id in node_positions:
                x0, y0 = node_positions[backup["id"]]
                x1, y1 = node_positions[switch_id]
                
                # Find the switch name
                switch_name = ""
                for switch in data["network_switches"]:
                    if switch["id"] == switch_id:
                        switch_name = switch["name"]
                        break
                
                # Create a more visible connection with hover information
                fig.add_trace(go.Scatter(
                    x=[x0, x1], y=[y0, y1],
                    mode='lines',
                    line=dict(
                        color=health_colour_map.get(backup["health"], "gray"),
                        width=3  
                    ),
                    name=f"{backup['name']} → {switch_name}",
                    text=f"Port: {port}",
                    hovertext=f"<b>Connection Details:</b><br>From: {backup['name']}<br>To: {switch_name}<br>Port: {port}<br>Type: {backup['connection_type']}",
                    hoverinfo='text',
                    showlegend=False
                ))
                
                # Add a small node in the middle of the connection line
                mid_x = (x0 + x1) / 2
                mid_y = (y0 + y1) / 2
                
                fig.add_trace(go.Scatter(
                    x=[mid_x], y=[mid_y],
                    mode='markers',
                    marker=dict(
                        size=10,
                        symbol='circle',
                        color=health_colour_map.get(backup["health"], "gray"),
                        line=dict(color="white", width=1)
                    ),
                    hovertext=f"<b>Connection Details:</b><br>From: {backup['name']}<br>To: {switch_name}<br>Port: {port}<br>Type: {backup['connection_type']}",
                    hoverinfo='text',
                    showlegend=False
                ))
    
    # Update layout
    fig.update_layout(
        title=f"{data['private_cloud']['name']} Architecture",
        showlegend=True,
        legend=dict(
            yanchor="bottom",
            y=0.01,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="black",
            borderwidth=1
        ),
        hovermode='closest',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='white',
        paper_bgcolor='white',
        width=1000,
        height=800
    )
    
    # Save as HTML
    pio.write_html(fig, file=output_path, auto_open=True)
    print(f"Interactive topology saved to {output_path}")


class TopologyChangeHandler(FileSystemEventHandler):
    def __init__(self, generate_topology_function):
        super().__init__()
        self.generate_topology = generate_topology_function
        self.timer = None
        self.debounce_time = 1  # Wait 1 second after last modification before updating

    def on_modified(self, event):
        if event.src_path.endswith(json_path):
            if self.timer:
                self.timer.cancel() 

            # Start a new timer that calls generate_topology() after 1 second
            self.timer = threading.Timer(self.debounce_time, self.generate_topology)
            self.timer.start()

def watch_for_changes():
    path = os.getcwd()  # Current directory
    event_handler = TopologyChangeHandler(generate_interactive_topology)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    
    print(f"Watching for changes in {json_path}...")

    try:
        while True:
            time.sleep(1)  # Keep the script running
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# Install required packages if not already installed
try:
    import plotly
except ImportError:
    print("Installing required packages...")
    os.system("pip install plotly")
    print("Packages installed successfully.")

generate_interactive_topology()
watch_for_changes() 