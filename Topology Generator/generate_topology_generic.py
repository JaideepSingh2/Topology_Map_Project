import json
import time
import os

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.network import Nginx
from diagrams.generic.compute import Rack
from diagrams.generic.storage import Storage
from diagrams.generic.network import *
# Firewall, Router, Subnet, Switch, VPN
from diagrams.generic.network import Switch, Router

# from diagrams.onprem.compute import Server
# from diagrams.onprem.storage import Ceph
# from diagrams.onprem.security import Vault

# Components Mapping
component_map = {
    "KVM": Rack,
    "Ceph": Storage,
    "Switch": Switch,
    "HAProxy": Nginx,
    "Firewall": Firewall,
    "Gateway": Router
}

# Health Status Colour Mapping
health_colour_map = {
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
                    components[comp["name"]] = Rack(comp["name"])

        with Cluster("Storage"):
            for comp in data["components"]:
                if comp["type"] == "Ceph":
                    components[comp["name"]] = Storage(comp["name"])

        with Cluster("Network"):
            for comp in data["components"]:
                if comp["type"] in ["Switch", "Gateway"]:
                    components[comp["name"]] = component_map[comp["type"]](comp["name"])

        with Cluster("Security"):
            for comp in data["components"]:
                if comp["type"] == "Firewall":
                    components[comp["name"]] = Firewall(comp["name"])

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
            edge_color = health_colour_map.get(health_status, "gray")

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
