import json
import time
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Nginx
from diagrams.onprem.security import Vault
from diagrams.onprem.storage import Ceph
from diagrams.generic.network import Switch, Router
import os

# Components Mapping
component_map = {
    "KVM": Server,
    "Ceph": Ceph,
    "Switch": Switch,
    "HAProxy": Nginx,
    "Firewall": Vault,
    "Gateway": Router
}

# Health Status Color Mapping
health_color_map = {
    "healthy": "green",
    "degraded": "orange",
    "critical": "red",
    "unknown": "gray"
}

def generate_topology():
    with open("cloud_topology.json", "r") as file:
        data = json.load(file)

    components = {}
    diagram_path = "topology"

    with Diagram("Private Cloud Architecture", filename=diagram_path, show=False, direction="LR"):
        # Create clusters
        with Cluster("Compute Nodes"):
            for comp in data["components"]:
                if comp["type"] == "KVM":
                    components[comp["name"]] = Server(comp["name"])

        with Cluster("Storage"):
            for comp in data["components"]:
                if comp["type"] == "Ceph":
                    components[comp["name"]] = Ceph(comp["name"])

        with Cluster("Network"):
            for comp in data["components"]:
                if comp["type"] in ["Switch", "Gateway"]:
                    components[comp["name"]] = component_map[comp["type"]](comp["name"])

        with Cluster("Security"):
            for comp in data["components"]:
                if comp["type"] == "Firewall":
                    components[comp["name"]] = Vault(comp["name"])

        with Cluster("Load Balancers"):
            for comp in data["components"]:
                if comp["type"] == "HAProxy":
                    components[comp["name"]] = Nginx(comp["name"])

        # Track processed connections
        processed_connections = set()

        # Create directed connections
        for comp in data["components"]:
            name = comp["name"]
            health_status = comp.get("health", "unknown")
            edge_color = health_color_map.get(health_status, "gray")

            for conn in comp["connected_to"]:
                if conn in components and name in components:
                    connection_tuple = tuple(sorted([name, conn]))

                    if connection_tuple not in processed_connections:
                        reverse_exists = any(
                            c for c in data["components"] if c["name"] == conn and name in c["connected_to"]
                        )

                        if reverse_exists:
                            components[name] << Edge(color=edge_color) >> components[conn]
                        else:
                            components[name] >> Edge(color=edge_color) >> components[conn]

                        processed_connections.add(connection_tuple)

    print("Topology updated!")
    # os.system(f"start topology.png")  # Uncomment this line to open the diagram automatically

# **Run in a loop for real-time updates**
while True:
    generate_topology()
    time.sleep(5)  # Update every 5 seconds
