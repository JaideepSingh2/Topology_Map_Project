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
    "Gateway": Router
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

    components = {}
    diagram_path = "HPE_topology"
    

    with Diagram("Private Cloud Architecture", filename=diagram_path, show=False, direction="LR", graph_attr={"dpi": "300"}):
        # Create clusters
        with Cluster("Compute Nodes"):
            for comp in data["components"]:
                if comp["type"] == "KVM":
                    components[comp["id"]] = Server(comp["name"])

        with Cluster("Storage"):
            for comp in data["components"]:
                if comp["type"] == "Ceph":
                    components[comp["id"]] = Ceph(comp["name"])

        with Cluster("Network"):
            for comp in data["components"]:
                if comp["type"] in ["Switch", "Gateway"]:
                    components[comp["id"]] = component_map[comp["type"]](comp["name"])

        with Cluster("Security"):
            for comp in data["components"]:
                if comp["type"] == "Firewall":
                    components[comp["id"]] = Vault(comp["name"])

        with Cluster("Load Balancers"):
            for comp in data["components"]:
                if comp["type"] == "HAProxy":
                    components[comp["id"]] = Nginx(comp["name"])

        # Track processed connections
        processed_connections = set()

        # Create directed connections
        for comp in data["components"]:
            id = comp["id"]
            health_status = comp.get("health", "unknown")
            edge_color = health_colour_map.get(health_status, "gray")

            for conn in comp["connected_to"]:
                if conn in components and id in components:
                    connection_tuple = tuple(sorted([id, conn]))

                    if connection_tuple not in processed_connections:
                        reverse_exists = any(
                            c for c in data["components"] if c["id"] == conn and id in c["connected_to"]
                        )

                        if reverse_exists:
                            components[id] << Edge(color=edge_color) >> components[conn]
                        else:
                            components[id] >> Edge(color=edge_color) >> components[conn]

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