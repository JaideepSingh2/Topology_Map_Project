import time
import threading
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Nginx
from diagrams.onprem.security import Vault
from diagrams.onprem.storage import Ceph
from diagrams.generic.network import Switch, Router
import os
import smtplib
from email.message import EmailMessage
import ssl
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

# Track alerted components to avoid duplicate alerts
alerted_components = set()

# Database check interval in seconds
check_interval = 30

def send_email_alert_async(subject, body):
    def _send_email():
        # Gmail SMTP settings
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587  # Using TLS port
        EMAIL_ADDRESS = "dm409@snu.edu.in"
        APP_PASSWORD = "mdsrfmvmwjhdznkd"  # Replace with your Gmail App Password

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_ADDRESS
        msg.set_content(body)

        try:
            # Create secure SSL/TLS context
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(EMAIL_ADDRESS, APP_PASSWORD)
                server.send_message(msg)
                print("✅ Email alert sent successfully")
        except Exception as e:
            print(f"❌ An error occurred: {e}")

    threading.Thread(target=_send_email, daemon=True).start()

def fetch_data_from_supabase():
    """Fetch all required data from Supabase database"""
    try:
        private_cloud = supabase.table('private_cloud').select('*').execute().data[0]
        servers = supabase.table('servers').select('*').execute().data
        network_switches = supabase.table('network_switches').select('*').execute().data
        storage = supabase.table('storage').select('*').execute().data
        backup = supabase.table('backup').select('*').execute().data

        server_connections = supabase.table('server_connected_switches').select('*').execute().data
        storage_connections = supabase.table('storage_connected_switches').select('*').execute().data
        backup_connections = supabase.table('backup_connected_switches').select('*').execute().data
        network_connections = supabase.table('network_connected_components').select('*').execute().data

        for server in servers:
            server["connected_switches"] = [
                {"switch_id": conn["switch_id"], "port": conn["port"]}
                for conn in server_connections if conn["server_id"] == server["id"]
            ]
        for store in storage:
            store["connected_switches"] = [
                {"switch_id": conn["switch_id"], "port": conn["port"]}
                for conn in storage_connections if conn["storage_id"] == store["id"]
            ]
        for bak in backup:
            bak["connected_switches"] = [
                {"switch_id": conn["switch_id"], "port": conn["port"]}
                for conn in backup_connections if conn["backup_id"] == bak["id"]
            ]
        for switch in network_switches:
            switch["connected_components"] = {
                conn["port"]: conn["component_id"]
                for conn in network_connections if conn["switch_id"] == switch["id"]
            }

        return {
            "private_cloud": private_cloud,
            "servers": servers,
            "network_switches": network_switches,
            "storage": storage,
            "backup": backup
        }
    except Exception as e:
        print(f"Error fetching data from Supabase: {e}")
        return None

def generate_topology():
    print("Starting topology generation...")
    data = fetch_data_from_supabase()
    if not data:
        print("Error: Could not fetch data from Supabase.")
        return

    components = {}
    diagram_path = "HPE_topology"
    with Diagram(
        f"{data['private_cloud'].get('name', 'Private Cloud')} Architecture",
        filename=diagram_path, show=False, direction="LR", graph_attr={"dpi": "150"}
    ):
        with Cluster("Compute Nodes"):
            for comp in data["servers"]:
                if comp.get("type") == "KVM":
                    components[comp["id"]] = Server(comp["name"])
        with Cluster("Storage"):
            for comp in data["storage"]:
                if comp.get("type") == "Ceph":
                    components[comp["id"]] = Ceph(comp["name"])
        with Cluster("Network"):
            for comp in data["network_switches"]:
                components[comp["id"]] = Switch(comp["name"])
        with Cluster("Backup"):
            for comp in data["backup"]:
                if comp.get("type") == "NAS":
                    components[comp["id"]] = Ceph(comp["name"])

        processed_connections = set()

        def process_connections(items, item_type):
            for item in items:
                item_id = item["id"]
                health_status = item.get("health", "unknown")
                edge_color = health_colour_map.get(health_status, "gray")
                connection_type = item.get("connection_type", "unknown")

                if health_status == "critical" and item_id not in alerted_components:
                    ip_address = item.get("ip_address", "N/A")
                    mac_address = item.get("mac", "N/A")
                    location = item.get("location", "N/A")
                    connected_switches = item.get("connected_switches", [])
                    switch_details = "\n".join(
                        [f"  - Switch ID: {conn['switch_id']}, Port: {conn['port']}" for conn in connected_switches]
                    ) if connected_switches else "  - None"

                    detailed_body = f"""
Critical Component Alert

Time of Detection: {time.strftime('%Y-%m-%d %H:%M:%S')}
Private Cloud: {data['private_cloud'].get('name', 'Unknown')}
Last Sync: {data['private_cloud'].get('last_sync', 'Unknown')}

Component Details:
- Name: {item['name']}
- ID: {item['id']}
- Type: {item.get('type', 'N/A')}
- Role: {item.get('role', 'N/A')}
- Health Status: CRITICAL
- Power Status: {item.get('power_status', 'N/A')}
- MAC Address: {mac_address}
- IP Address: {ip_address}
- Location: {location}
- Connection Type: {connection_type}
- Connected Switches:
{switch_details}

This is an automated alert from the Topology Monitoring System.
"""
                    send_email_alert_async(
                        subject=f"Critical Alert: {item['name']}",
                        body=detailed_body
                    )
                    alerted_components.add(item_id)

                for conn in item.get("connected_switches", []):
                    switch_id = conn["switch_id"]
                    if switch_id in components and item_id in components:
                        connection_tuple = tuple(sorted([item_id, switch_id]))
                        if connection_tuple not in processed_connections:
                            components[item_id] >> Edge(
                                label=f"{connection_type} ({conn['port']})", color=edge_color
                            ) >> components[switch_id]
                            processed_connections.add(connection_tuple)

        process_connections(data["servers"], "server")
        process_connections(data["storage"], "storage")
        process_connections(data["backup"], "backup")

    print("Topology generation complete.")

class DatabaseMonitor:
    def __init__(self, generate_topology_function, check_interval=30):
        self.generate_topology = generate_topology_function
        self.check_interval = check_interval
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        while self.running:
            self.generate_topology()
            time.sleep(self.check_interval)

    def stop(self):
        self.running = False

print("Generating initial topology...")
generate_topology()

db_monitor = DatabaseMonitor(generate_topology, check_interval)
db_monitor.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    db_monitor.stop()
    print("Program terminated by user.")