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

def generate_topology():
    print("Starting topology generation...")
    start_time = time.time()
    
    # Fetch data from Supabase instead of reading from JSON file
    data = fetch_data_from_supabase()
    
    if not data:
        print("Error: Could not fetch data from Supabase.")
        return

    required_sections = ["private_cloud", "servers", "network_switches", "storage", "backup"]
    if not all(section in data for section in required_sections):
        print("Error: Missing required sections in data fetched from database.")
        return

    components = {}
    diagram_path = "HPE_topology"
    
    with Diagram(
        f"{data['private_cloud'].get('name', 'Private Cloud')} Architecture", 
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
Private Cloud: {data['private_cloud'].get('name', 'Unknown')}
Last Sync: {data['private_cloud'].get('last_sync', 'Unknown')}

Component Details:
- Name: {item['name']}
- ID: {item['id']}
- Type: {item.get('type', 'N/A')}
- Role: {item.get('role', 'N/A')}
- Health Status: CRITICAL
- Power Status: {item.get('power_status', 'N/A')}
- Location: {item.get('location', 'N/A')}

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

# Start initial topology generation and database monitoring
print("Generating initial topology...")
generate_topology()

# Monitor database for changes
db_monitor = DatabaseMonitor(generate_topology, check_interval)
db_monitor.start()

try:
    while True:
        time.sleep(1)  # Keep the script running
except KeyboardInterrupt:
    db_monitor.stop()
    print("Program terminated by user")