import time
import os
import threading
import subprocess
import sys
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Nginx
from diagrams.onprem.security import Vault
from diagrams.onprem.storage import Ceph
from diagrams.generic.network import Switch, Router
from supabase import create_client

# Supabase configuration
SUPABASE_URL = "https://xpchztgrhfhgtcekazan.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwY2h6dGdyaGZoZ3RjZWthemFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxNTY3MTUsImV4cCI6MjA2MDczMjcxNX0.VUKKlhtXgZdr2G4U-CGOjHH6TgugrPyg0cFzePzC4Q8"

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Components Mapping
component_map = {
    "KVM": Server,
    "Ceph": Ceph,
    "Switch": Switch,
    "HAProxy": Nginx,
    "Firewall": Vault,
    "Gateway": Router,
    "NAS": Ceph  # Using Ceph icon for NAS
}

# Health Status Colour Mapping
health_colour_map = {
    "healthy": "green",
    "degraded": "orange",
    "critical": "red",
    "unknown": "gray"
}

# Database check interval in seconds
check_interval = 30  # Check for changes every 30 seconds

# Check for Graphviz installation
def check_graphviz_installation():
    try:
        # Try to run the 'dot' command
        subprocess.run(['dot', '-V'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("ERROR: Graphviz is not installed or not in your PATH")
        print("Please install Graphviz:")
        print("  Ubuntu/Debian: sudo apt-get install graphviz")
        print("  Fedora: sudo dnf install graphviz")
        print("  CentOS/RHEL: sudo yum install graphviz")
        print("  macOS: brew install graphviz")
        print("  Windows: Download from https://graphviz.org/download/")
        return False

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

def generate_topology():
    print("Starting topology generation...")
    start_time = time.time()

    # Fetch data from Supabase instead of reading from JSON file
    data = fetch_data_from_supabase()
    
    if not data:
        print("Error: Could not fetch data from Supabase.")
        return

    # Check if required sections exist
    required_sections = ["private_cloud", "servers", "network_switches", "storage", "backup"]
    for section in required_sections:
        if section not in data:
            print(f"Error: '{section}' section not found in data from Supabase. Please check the database structure.")
            return  # Exit the function if any required section is missing

    components = {}
    diagram_path = "HPE_topology"
    
    with Diagram(
        f"{data['private_cloud'].get('name', 'Private Cloud')} Architecture", 
        filename=diagram_path, 
        show=False, 
        direction="LR", 
        graph_attr={"dpi": "300"}
    ):
        # Create clusters
        with Cluster("Compute Nodes"):
            for comp in data["servers"]:
                if "type" in comp and comp["type"] == "KVM":
                    components[comp["id"]] = Server(comp["name"])

        with Cluster("Storage"):
            for comp in data["storage"]:
                if "type" in comp and comp["type"] == "Ceph":
                    components[comp["id"]] = Ceph(comp["name"])

        with Cluster("Network"):
            for comp in data["network_switches"]:
                components[comp["id"]] = Switch(comp["name"])

        with Cluster("Backup"):
            for comp in data["backup"]:
                if "type" in comp and comp["type"] == "NAS":
                    components[comp["id"]] = Ceph(comp["name"])

        # Track processed connections
        processed_connections = set()

        # Create connections from servers to switches
        for server in data["servers"]:
            server_id = server["id"]
            health_status = server.get("health", "unknown")
            edge_color = health_colour_map.get(health_status, "gray")
            connection_type = server.get("connection_type", "unknown")

            for conn in server.get("connected_switches", []):
                switch_id = conn["switch_id"]
                port = conn["port"]
                
                if switch_id in components and server_id in components:
                    connection_tuple = tuple(sorted([server_id, switch_id]))
                    
                    if connection_tuple not in processed_connections:
                        print(f"Creating connection from {server_id} to {switch_id} on port {port}")
                        components[server_id] >> Edge(label=f"{connection_type} ({port})", color=edge_color) >> components[switch_id]
                        processed_connections.add(connection_tuple)

        # Create connections from storage to switches
        for storage in data["storage"]:
            storage_id = storage["id"]
            health_status = storage.get("health", "unknown")
            edge_color = health_colour_map.get(health_status, "gray")
            connection_type = storage.get("connection_type", "unknown")

            for conn in storage.get("connected_switches", []):
                switch_id = conn["switch_id"]
                port = conn["port"]
                
                if switch_id in components and storage_id in components:
                    connection_tuple = tuple(sorted([storage_id, switch_id]))
                    
                    if connection_tuple not in processed_connections:
                        print(f"Creating connection from {storage_id} to {switch_id} on port {port}")
                        components[storage_id] >> Edge(label=f"{connection_type} ({port})", color=edge_color) >> components[switch_id]
                        processed_connections.add(connection_tuple)

        # Create connections from backup to switches
        for backup in data["backup"]:
            backup_id = backup["id"]
            health_status = backup.get("health", "unknown")
            edge_color = health_colour_map.get(health_status, "gray")
            connection_type = backup.get("connection_type", "unknown")

            for conn in backup.get("connected_switches", []):
                switch_id = conn["switch_id"]
                port = conn["port"]
                
                if switch_id in components and backup_id in components:
                    connection_tuple = tuple(sorted([backup_id, switch_id]))
                    
                    if connection_tuple not in processed_connections:
                        print(f"Creating connection from {backup_id} to {switch_id} on port {port}")
                        components[backup_id] >> Edge(label=f"{connection_type} ({port})", color=edge_color) >> components[switch_id]
                        processed_connections.add(connection_tuple)

    end_time = time.time()
    print(f"Topology updated in {end_time - start_time:.2f} seconds")
    
    # Open the diagram based on operating system
    if os.name == 'nt':  # Windows
        os.system(f"start {diagram_path}.png")
    elif os.name == 'posix':  # Linux or macOS
        if sys.platform == 'darwin':  # macOS
            os.system(f"open {diagram_path}.png")
        else:  # Linux
            os.system(f"xdg-open {diagram_path}.png")


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

# Check for Graphviz before starting
if not check_graphviz_installation():
    print("Attempting to install Graphviz...")
    if os.name == 'posix':  # Linux or macOS
        os.system("sudo apt-get update && sudo apt-get install -y graphviz")
    else:
        print("Please install Graphviz manually and add it to your PATH")
        sys.exit(1)

# Generate initial topology
print("Generating initial topology...")
generate_topology()

# Start database monitoring
db_monitor = DatabaseMonitor(generate_topology, check_interval)
db_monitor.start()

try:
    while True:
        time.sleep(1)  # Keep the script running
except KeyboardInterrupt:
    db_monitor.stop()
    print("Program terminated by user")