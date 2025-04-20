import json
import time
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Nginx
from diagrams.onprem.security import Vault
from diagrams.onprem.storage import Ceph
from diagrams.generic.network import Switch, Router
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

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

json_path = "HPE.json"

def generate_topology():
    with open(json_path, "r") as file:
        data = json.load(file)

    # Check if required sections exist
    required_sections = ["private_cloud", "servers", "network_switches", "storage", "backup"]
    for section in required_sections:
        if section not in data:
            print(f"Error: '{section}' section not found in {json_path}. Please check the JSON structure.")
            return  # Exit the function if any required section is missing

    components = {}
    diagram_path = "HPE_topology"
    
    with Diagram(f"{data['private_cloud']['name']} Architecture", filename=diagram_path, show=False, direction="LR", graph_attr={"dpi": "300"}):
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

    print("Topology updated")
    os.system(f"start {diagram_path}.png")  # To open the diagram automatically


class TopologyChangeHandler(FileSystemEventHandler):
    def __init__(self, generate_topology_function):
        super().__init__()
        self.generate_topology = generate_topology_function
        self.timer = None
        self.debounce_time = 1  # Wait 1 second after last modification before updating

    def on_modified(self, event):
        if event.src_path.endswith(json_path):
            if self.timer:
                self.timer.cancel()  # Cancel any existing timer

            # Start a new timer that calls generate_topology() after 1 second
            self.timer = threading.Timer(self.debounce_time, self.generate_topology)
            self.timer.start()

def watch_for_changes():
    path = os.getcwd()  # Current directory
    event_handler = TopologyChangeHandler(generate_topology)
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

generate_topology()
watch_for_changes()