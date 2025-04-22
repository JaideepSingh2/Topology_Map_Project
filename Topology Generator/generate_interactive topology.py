import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import plotly.graph_objects as go
import plotly.io as pio
from supabase import create_client

# Supabase configuration
SUPABASE_URL = "https://xpchztgrhfhgtcekazan.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwY2h6dGdyaGZoZ3RjZWthemFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxNTY3MTUsImV4cCI6MjA2MDczMjcxNX0.VUKKlhtXgZdr2G4U-CGOjHH6TgugrPyg0cFzePzC4Q8"

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Health Status Colour Mapping
health_colour_map = {
    "healthy": "green",
    "degraded": "orange",
    "critical": "red",
    "unknown": "gray"
}

output_path = "HPE_topology.html"
check_interval = 30  # Check database for changes every 30 seconds

def fetch_data_from_supabase():
    """Fetch all required data from Supabase database"""
    try:
        # Fetch private cloud data
        private_cloud_response = supabase.table('private_cloud').select('*').execute()
        private_cloud = private_cloud_response.data[0] if private_cloud_response.data else {}
        
        # Fetch servers data
        servers_response = supabase.table('servers').select('*').execute()
        servers = servers_response.data

        # Fetch network switches data
        switches_response = supabase.table('network_switches').select('*').execute()
        network_switches = switches_response.data
        
        # Fetch storage data
        storage_response = supabase.table('storage').select('*').execute()
        storage = storage_response.data
        
        # Fetch backup data
        backup_response = supabase.table('backup').select('*').execute()
        backup = backup_response.data

        # Fetch connection data for servers
        server_connections_response = supabase.table('server_connected_switches').select('*').execute()
        server_connections = server_connections_response.data
        
        # Fetch connection data for storage
        storage_connections_response = supabase.table('storage_connected_switches').select('*').execute()
        storage_connections = storage_connections_response.data
        
        # Fetch connection data for backup
        backup_connections_response = supabase.table('backup_connected_switches').select('*').execute()
        backup_connections = backup_connections_response.data

        # Fetch connection data for network switches
        network_connections_response = supabase.table('network_connected_components').select('*').execute()
        network_connections = network_connections_response.data

        # Process the servers to add their connections
        for server in servers:
            server["connected_switches"] = []
            for conn in server_connections:
                if conn["server_id"] == server["id"]:
                    server["connected_switches"].append({
                        "switch_id": conn["switch_id"],
                        "port": conn["port"]
                    })
        
        # Process the storage to add their connections
        for store in storage:
            store["connected_switches"] = []
            for conn in storage_connections:
                if conn["storage_id"] == store["id"]:
                    store["connected_switches"].append({
                        "switch_id": conn["switch_id"],
                        "port": conn["port"]
                    })
        
        # Process the backup to add their connections
        for bak in backup:
            bak["connected_switches"] = []
            for conn in backup_connections:
                if conn["backup_id"] == bak["id"]:
                    bak["connected_switches"].append({
                        "switch_id": conn["switch_id"],
                        "port": conn["port"]
                    })
        
        # Process the network switches to add their connections
        for switch in network_switches:
            switch["connected_components"] = {}
            for conn in network_connections:
                if conn["switch_id"] == switch["id"]:
                    switch["connected_components"][conn["port"]] = conn["component_id"]

        # Build a data structure similar to the original JSON
        data = {
            "private_cloud": private_cloud,
            "servers": servers,
            "network_switches": network_switches,
            "storage": storage,
            "backup": backup
        }
        
        return data
    
    except Exception as e:
        print(f"Error fetching data from Supabase: {e}")
        return None

def generate_interactive_topology():
    print("Fetching data from Supabase...")
    data = fetch_data_from_supabase()
    
    if not data:
        print("Failed to fetch data from Supabase. Check connection or database structure.")
        return

    # Check if required sections exist
    required_sections = ["private_cloud", "servers", "network_switches", "storage", "backup"]
    for section in required_sections:
        if section not in data or not data[section]:
            print(f"Warning: '{section}' section is empty or not found in database. Continuing anyway.")

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
        Location: {server["location"]}<br>
        IP: {server["ip_address"]}
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
        Location: {storage["location"]}
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
        Location: {switch["location"]}
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
        Location: {backup["location"]}
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
    cloud_name = data['private_cloud'].get('name', 'Private Cloud') if data['private_cloud'] else 'Private Cloud'
    fig.update_layout(
        title=f"{cloud_name} Architecture",
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


class DatabaseMonitor:
    def __init__(self, generate_topology_function, check_interval=30):
        self.generate_topology = generate_topology_function
        self.check_interval = check_interval
        self.last_check_time = None
        self.running = False
        self.thread = None
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        print(f"Database monitoring started. Checking every {self.check_interval} seconds.")
    
    def _monitor_loop(self):
        while self.running:
            try:
                # Get the database last update time
                # This assumes you have a table called 'metadata' with a 'last_updated' field
                # If not, you could add a check on any table's updated_at field
                now = time.time()
                if self.last_check_time is None or (now - self.last_check_time) >= self.check_interval:
                    print("Checking for database changes...")
                    self.last_check_time = now
                    self.generate_topology()
            except Exception as e:
                print(f"Error monitoring database: {e}")
            
            time.sleep(self.check_interval)
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        print("Database monitoring stopped.")


# Install required packages if not already installed
try:
    import plotly
    from supabase import create_client
except ImportError:
    print("Installing required packages...")
    os.system("pip install plotly supabase")
    print("Packages installed successfully.")

# Generate initial topology and start monitoring
print("Generating initial topology...")
generate_interactive_topology()

# Monitor database for changes
db_monitor = DatabaseMonitor(generate_interactive_topology, check_interval)
db_monitor.start()

try:
    while True:
        time.sleep(1)  # Keep the script running
except KeyboardInterrupt:
    db_monitor.stop()
    print("Program terminated by user")