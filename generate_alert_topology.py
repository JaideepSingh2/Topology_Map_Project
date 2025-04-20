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
import smtplib
from email.message import EmailMessage
import ssl

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

# Track alerted components to avoid duplicate alerts
alerted_components = set()

def send_email_alert_async(subject, body):
    def _send_email():
        # Gmail SMTP settings
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587  # Using TLS port
        EMAIL_ADDRESS = "dm409@snu.edu.in"
        # Create an App Password in Gmail settings and use it here
        # Go to Google Account -> Security -> 2-Step Verification -> App Passwords
        APP_PASSWORD = "mdsrfmvmwjhdznkd"  # Replace with your Gmail App Password

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_ADDRESS
        msg.set_content(body)

        try:
            # Create secure SSL/TLS context
            context = ssl.create_default_context()
            
            # Connect to Gmail using TLS
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(EMAIL_ADDRESS, APP_PASSWORD)
                server.send_message(msg)
                print("✅ Email alert sent successfully")
                
        except smtplib.SMTPAuthenticationError:
            print("❌ Authentication failed. Please check your email and app password.")
        except smtplib.SMTPException as e:
            print(f"❌ SMTP error occurred: {e}")
        except TimeoutError:
            print("❌ Connection timed out. Check your internet connection.")
        except Exception as e:
            print(f"❌ An error occurred: {e}")

    # Run email sending in a separate thread
    threading.Thread(target=_send_email, daemon=True).start()

def generate_topology():
    print("Starting topology generation...")
    start_time = time.time()
    
    with open(json_path, "r") as file:
        data = json.load(file)

    required_sections = ["private_cloud", "servers", "network_switches", "storage", "backup"]
    if not all(section in data for section in required_sections):
        print("Error: Missing required sections in JSON file.")
        return

    components = {}
    diagram_path = "HPE_topology"
    
    with Diagram(
        f"{data['private_cloud']['name']} Architecture", 
        filename=diagram_path, 
        show=False, 
        direction="LR", 
        graph_attr={"dpi": "150"}  # Further reduced DPI for faster rendering
    ):
        print("Creating compute nodes...")
        with Cluster("Compute Nodes"):
            for comp in data["servers"]:
                if comp.get("type") == "KVM":
                    components[comp["id"]] = Server(comp["name"])

        print("Creating storage nodes...")
        with Cluster("Storage"):
            for comp in data["storage"]:
                if comp.get("type") == "Ceph":
                    components[comp["id"]] = Ceph(comp["name"])

        print("Creating network nodes...")
        with Cluster("Network"):
            for comp in data["network_switches"]:
                components[comp["id"]] = Switch(comp["name"])

        print("Creating backup nodes...")
        with Cluster("Backup"):
            for comp in data["backup"]:
                if comp.get("type") == "NAS":
                    components[comp["id"]] = Ceph(comp["name"])

        processed_connections = set()

        def process_connections(items, item_type):
            print(f"Processing {item_type} connections...")
            for item in items:
                item_id = item["id"]
                health_status = item.get("health", "unknown")
                edge_color = health_colour_map.get(health_status, "gray")
                connection_type = item.get("connection_type", "unknown")

                if health_status == "critical" and item_id not in alerted_components:
                    detailed_body = f"""
Critical Component Alert

Time of Detection: {time.strftime('%Y-%m-%d %H:%M:%S')}
Private Cloud: {data['private_cloud']['name']}
Last Sync: {data['private_cloud']['last_sync']}

Component Details:
- Name: {item['name']}
- ID: {item['id']}
- Type: {item.get('type', 'N/A')}
- Role: {item.get('role', 'N/A')}
- Health Status: CRITICAL
- Power Status: {item.get('power_status', 'N/A')}
- Location: {item.get('metadata', {}).get('location', 'N/A')}

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
                                label=f"{connection_type} ({conn['port']})", 
                                color=edge_color
                            ) >> components[switch_id]
                            processed_connections.add(connection_tuple)

        process_connections(data["servers"], "server")
        process_connections(data["storage"], "storage")
        process_connections(data["backup"], "backup")

    end_time = time.time()
    print(f"Topology updated in {end_time - start_time:.2f} seconds")


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

# Start initial topology generation and watch for changes
generate_topology()
watch_for_changes()
