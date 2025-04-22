import time
import os
import threading
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.network import Nginx
from diagrams.generic.compute import Rack
from diagrams.generic.storage import Storage
from diagrams.generic.network import *
# Firewall, Router, Subnet, Switch, VPN
from diagrams.generic.network import Switch, Router
from supabase import create_client

# Supabase configuration
SUPABASE_URL = "https://xpchztgrhfhgtcekazan.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwY2h6dGdyaGZoZ3RjZWthemFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxNTY3MTUsImV4cCI6MjA2MDczMjcxNX0.VUKKlhtXgZdr2G4U-CGOjHH6TgugrPyg0cFzePzC4Q8"

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Components Mapping
component_map = {
    "KVM": Rack,
    "Ceph": Storage,
    "Switch": Switch,
    "HAProxy": Nginx,
    "Firewall": Firewall,
    "Gateway": Router,
    "NAS": Storage  # Using Storage icon for NAS
}

# Health Status Colour Mapping
health_colour_map = {
    "healthy": "green",
    "degraded": "orange",
    "critical": "red",
    "unknown": "gray"
}

# Database check interval in seconds
check_interval = 5  # Update every 5 seconds

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

        # Convert the database structure to a components format for generic topology generation
        components = []
        
        # Add servers to components
        for server in servers:
            connected_to = []
            for conn in server.get("connected_switches", []):
                connected_to.append(conn["switch_id"])
                
            components.append({
                "id": server["id"],
                "name": server["name"],
                "type": server["type"],
                "health": server["health"],
                "connected_to": connected_to
            })
        
        # Add storage to components
        for storage_item in storage:
            connected_to = []
            for conn in storage_item.get("connected_switches", []):
                connected_to.append(conn["switch_id"])
                
            components.append({
                "id": storage_item["id"],
                "name": storage_item["name"],
                "type": storage_item["type"],
                "health": storage_item["health"],
                "connected_to": connected_to
            })
            
        # Add backup to components
        for backup_item in backup:
            connected_to = []
            for conn in backup_item.get("connected_switches", []):
                connected_to.append(conn["switch_id"])
                
            components.append({
                "id": backup_item["id"],
                "name": backup_item["name"],
                "type": backup_item["type"],
                "health": backup_item["health"],
                "connected_to": connected_to
            })
            
        # Add network switches to components
        for switch in network_switches:
            connected_to = list(switch.get("connected_components", {}).values())
            
            components.append({
                "id": switch["id"],
                "name": switch["name"],
                "type": "Switch",
                "health": switch["health"],
                "connected_to": connected_to
            })
        
        # Build a data structure similar to the original JSON but with components
        data = {
            "private_cloud": private_cloud,
            "components": components
        }
        
        return data
    
    except Exception as e:
        print(f"Error fetching data from Supabase: {e}")
        return None

def generate_topology():
    print("Starting generic topology generation...")
    start_time = time.time()
    
    # Fetch data from Supabase instead of reading from JSON file
    data = fetch_data_from_supabase()
    
    if not data:
        print("Error: Could not fetch data from Supabase.")
        return

    if "components" not in data or not data["components"]:
        print("Error: No components found in data fetched from database.")
        return

    # Create component lookup dictionaries
    id_to_component = {comp["id"]: comp for comp in data["components"]}
    name_to_id = {comp["name"]: comp["id"] for comp in data["components"]}
    components = {}
    diagram_path = "topology"

    # Get cloud name from private_cloud
    cloud_name = data["private_cloud"].get("name", "Private Cloud") if data["private_cloud"] else "Private Cloud"

    with Diagram(f"{cloud_name} Architecture", filename=diagram_path, show=False, direction="LR"):
        # Create clusters
        with Cluster("Compute Nodes"):
            for comp in data["components"]:
                if comp["type"] == "KVM":
                    components[comp["id"]] = Rack(comp["name"])

        with Cluster("Storage"):
            for comp in data["components"]:
                if comp["type"] == "Ceph":
                    components[comp["id"]] = Storage(comp["name"])
                elif comp["type"] == "NAS":
                    components[comp["id"]] = Storage(comp["name"])

        with Cluster("Network"):
            for comp in data["components"]:
                if comp["type"] in ["Switch", "Gateway"]:
                    try:
                        components[comp["id"]] = component_map[comp["type"]](comp["name"])
                    except KeyError:
                        print(f"Warning: Unknown component type '{comp['type']}'")
                        components[comp["id"]] = Switch(comp["name"])  # Default to Switch

        with Cluster("Security"):
            for comp in data["components"]:
                if comp["type"] == "Firewall":
                    components[comp["id"]] = Firewall(comp["name"])

        with Cluster("Load Balancers"):
            for comp in data["components"]:
                if comp["type"] == "HAProxy":
                    components[comp["id"]] = Nginx(comp["name"])

        # Track processed connections
        processed_connections = set()

        # Create directed connections
        for comp in data["components"]:
            comp_id = comp["id"]
            health_status = comp.get("health", "unknown")
            edge_color = health_colour_map.get(health_status, "gray")

            for connected_id in comp.get("connected_to", []):
                if connected_id in components and comp_id in components:
                    connection_tuple = tuple(sorted([comp_id, connected_id]))

                    if connection_tuple not in processed_connections:
                        # Check if the connection is bidirectional
                        reverse_exists = False
                        if connected_id in id_to_component:
                            reverse_exists = comp_id in id_to_component[connected_id].get("connected_to", [])

                        if reverse_exists:
                            components[comp_id] << Edge(color=edge_color) >> components[connected_id]
                        else:
                            components[comp_id] >> Edge(color=edge_color) >> components[connected_id]

                        processed_connections.add(connection_tuple)

    end_time = time.time()
    print(f"Topology updated in {end_time - start_time:.2f} seconds!")


class DatabaseMonitor:
    def __init__(self, generate_topology_function, check_interval=5):
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
                # Update the topology based on the check interval
                now = time.time()
                if self.last_check_time is None or (now - self.last_check_time) >= self.check_interval:
                    print("Checking for database changes...")
                    self.last_check_time = now
                    self.generate_topology()
            except Exception as e:
                print(f"Error monitoring database: {e}")
            
            time.sleep(1)  # Small sleep to prevent CPU hogging
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        print("Database monitoring stopped.")


# Install required packages if not already installed
try:
    from supabase import create_client
except ImportError:
    print("Installing required packages...")
    os.system("pip install supabase-py")
    print("Packages installed successfully.")

# Start monitoring database for changes
monitor = DatabaseMonitor(generate_topology, check_interval)
monitor.start()

try:
    while True:
        time.sleep(1)  # Keep the script running
except KeyboardInterrupt:
    monitor.stop()
    print("Program terminated by user")