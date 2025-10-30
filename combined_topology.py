import os
import time
import threading
import logging
import base64  # Added for base64 encoding
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Nginx
from diagrams.onprem.security import Vault
from diagrams.onprem.storage import Ceph
from diagrams.generic.network import Switch, Router
import smtplib
from email.message import EmailMessage
import ssl
import requests
import plotly.graph_objects as go
import plotly.io as pio
import webbrowser

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = "https://xpchztgrhfhgtcekazan.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwY2h6dGdyaGZoZ3RjZWthemFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxNTY3MTUsImV4cCI6MjA2MDczMjcxNX0.VUKKlhtXgZdr2G4U-CGOjHH6TgugrPyg0cFzePzC4Q8"

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "" #placeholder
APP_PASSWORD = ""  #placeholder

INTERVAL_TIME = 3

# Health Status Colour Mapping
health_colour_map = {
    "healthy": "green",
    "degraded": "orange",
    "critical": "red",
    "unknown": "gray"
}

alerted_components = set()

# --- Utility Functions for Image Handling ---
def get_default_image_data_uri():
    """Return a simple default image as data URI if no image is found"""
    # A simple gray box as fallback
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAAGYktHRAD/AP8A/6C9p5MAAAAJcEhZcwAALiMAAC4jAXilP3YAAAAHdElNRQfnBQ4WNzd6B8JvAAABQ0lEQVRo3u2ZMU7DMBSGv1Q9QcUBygEYWdgZGFkg6tY7VOIOMAGdGZhYWCAxwgVgR0JIUHKADgwsVSwgQUhJ/Ow0wf2W2KrjfK+/5+c3VpAkyX+UDdYrwBOwC4yAe+DBGLNIbjiO433gRRn7SNJW7HpFePQlvEm6qHFuVtKbMjZLWq8TYA8YK+OxpKPKF9BY0LqfTWPMQZTxhccYk3vfZuLedGIjXCfCRoiJEBthJsL/b4Sp3wnOBUkfkqbAYZZlP8aYh5hFQx/gTNJlvh8CZ0AXuAGuYhVMcYDdEfAO3AC7wCmQ5XEa0SZICiHpy26HiW1yGKQcL0mW0ltRo6nHWknPpkLUDRBbChBvQUtVKBYhOkAtLYGoAE5aCuAk9TX6DGzl+y5wGrPYskcrU6Y34BK4A76BAfBojMniVksikWiML4YT3HO+95XBAAAAAElFTkSuQmCC"

def encode_image_to_base64(image_path):
    """Convert an image file to base64 for embedding in HTML"""
    try:
        if not os.path.exists(image_path):
            logger.warning(f"Image not found: {image_path}, using default")
            return get_default_image_data_uri()
        
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        return get_default_image_data_uri()

def ensure_images_directory():
    """Make sure the images directory exists"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(script_dir, "images")
    if not os.path.exists(images_dir):
        logger.info(f"Creating images directory at {images_dir}")
        os.makedirs(images_dir)
    return images_dir

# --- Data Fetching ---
def fetch_table(table_name):
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get(url, headers=headers, params={"select": "*"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Error fetching {table_name} from Supabase: {e}")
        return []

def fetch_data_from_supabase():
    try:
        private_cloud = fetch_table('private_cloud')
        private_cloud = private_cloud[0] if private_cloud else {}
        servers = fetch_table('servers')
        network_switches = fetch_table('network_switches')
        storage = fetch_table('storage')
        backup = fetch_table('backup')
        server_connections = fetch_table('server_connected_switches')
        storage_connections = fetch_table('storage_connected_switches')
        backup_connections = fetch_table('backup_connected_switches')
        network_connections = fetch_table('network_connected_components')

        for server in servers:
            server["connected_switches"] = []
            for conn in server_connections:
                if conn.get("server_id") == server.get("id"):
                    server["connected_switches"].append({"switch_id": conn["switch_id"], "port": conn["port"]})
        for store in storage:
            store["connected_switches"] = []
            for conn in storage_connections:
                if conn.get("storage_id") == store.get("id"):
                    store["connected_switches"].append({"switch_id": conn["switch_id"], "port": conn["port"]})
        for bak in backup:
            bak["connected_switches"] = []
            for conn in backup_connections:
                if conn.get("backup_id") == bak.get("id"):
                    bak["connected_switches"].append({"switch_id": conn["switch_id"], "port": conn["port"]})
        for switch in network_switches:
            switch["connected_components"] = {}
            for conn in network_connections:
                if conn.get("switch_id") == switch.get("id"):
                    switch["connected_components"][conn["port"]] = conn["component_id"]
        return {
            "private_cloud": private_cloud,
            "servers": servers,
            "network_switches": network_switches,
            "storage": storage,
            "backup": backup
        }
    except Exception as e:
        logger.error(f"Error fetching data from Supabase: {e}")
        return None

# --- Email Alert ---
def send_email_alert_async(subject, body):
    def _send_email():
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_ADDRESS
        msg.set_content(body)
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(EMAIL_ADDRESS, APP_PASSWORD)
                server.send_message(msg)
                logger.info("✅ Email alert sent successfully")
        except Exception as e:
            logger.error(f"❌ Failed to send email: {str(e)}")
    threading.Thread(target=_send_email, daemon=True).start()

# --- PNG Diagram Generation (with Alerts) ---
def generate_png_topology(data):
    components = {}
    diagram_path = "HPE_topology"
    with Diagram(
        f"{data['private_cloud'].get('name', 'Private Cloud')} Architecture", 
        filename=diagram_path, 
        show=False, 
        direction="LR", 
        graph_attr={"dpi": "150"}
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
                
                # Check for critical health status and send detailed email alert
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
                                label=f"{connection_type} ({conn['port']})", 
                                color=edge_color
                            ) >> components[switch_id]
                            processed_connections.add(connection_tuple)
        process_connections(data["servers"], "server")
        process_connections(data["storage"], "storage")
        process_connections(data["backup"], "backup")
    logger.info("PNG topology diagram generated.")

# --- Interactive HTML Topology Generation ---
def generate_interactive_topology(data):
    output_path = "HPE_topology.html"
    fig = go.Figure()
    node_positions = {}
    images_to_add = []
    
    # Ensure images directory exists
    images_dir = ensure_images_directory()

    # Define image paths and convert to base64
    server_image = encode_image_to_base64(os.path.join(images_dir, "Server.png"))
    switch_image = encode_image_to_base64(os.path.join(images_dir, "Switch.png"))
    storage_image = encode_image_to_base64(os.path.join(images_dir, "Storage.png"))
    backup_image = encode_image_to_base64(os.path.join(images_dir, "Backup.png"))

    left_x = 0.1
    middle_x = 0.5
    right_x = 0.9
    y_step = 0.15

    # Servers on left
    left_nodes = data["servers"]
    for i, node in enumerate(left_nodes):
        y = 0.9 - i * y_step
        node_positions[node["id"]] = (left_x, y)
        if "cpu_utilization" in node:  # server
            hover_text = f"""
<b>{node['name']}</b><br>ID: {node['id']}<br>Type: {node['type']}<br>Role: {node['role']}<br>Health: {node['health']}<br>Power: {node.get('power_status', 'N/A')}<br>CPU: {node.get('cpu_utilization', 'N/A')}<br>MAC: {node.get('mac', 'N/A')}<br>Location: {node.get('location', 'N/A')}<br>IP: {node.get('ip_address', 'N/A')}"""
        fig.add_trace(go.Scatter(
            x=[left_x], y=[y], mode='markers+text', name=node["name"], text=[node["name"]],
            textposition="bottom center",
            marker=dict(size=30, color='rgba(0,0,0,0)'),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=True
        ))
        images_to_add.append(dict(
            source=server_image,  # Using base64 encoded image
            xref="x", yref="y",
            x=left_x, y=y+0.03,
            sizex=0.06, sizey=0.06,
            xanchor="center", yanchor="middle",
            layer="above"
        ))

    # Switches in the middle
    for i, switch in enumerate(data["network_switches"]):
        y = 0.9 - i * y_step
        node_positions[switch["id"]] = (middle_x, y)
        hover_text = f"""
<b>{switch['name']}</b><br>ID: {switch['id']}<br>Type: {switch.get('switch_type', 'N/A')}<br>Role: {switch.get('role', 'N/A')}<br>Health: {switch['health']}<br>Power: {switch.get('power_status', 'N/A')}<br>MAC: {switch.get('mac', 'N/A')}<br>Location: {switch.get('location', 'N/A')}"""
        fig.add_trace(go.Scatter(
            x=[middle_x], y=[y], mode='markers+text', name=switch["name"], text=[switch["name"]],
            textposition="bottom center",
            marker=dict(size=30, color='rgba(0,0,0,0)'),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=True
        ))
        images_to_add.append(dict(
            source=switch_image,  # Using base64 encoded image
            xref="x", yref="y",
            x=middle_x, y=y+0.03,
            sizex=0.06, sizey=0.06,
            xanchor="center", yanchor="middle",
            layer="above"
        ))


    # Storages on right top
    for i, switch in enumerate(data["storage"]):
        y = 0.9 - i * y_step
        node_positions[switch["id"]] = (right_x, y)
        hover_text = f"""
<b>{switch['name']}</b><br>ID: {switch['id']}<br>Type: {switch['type']}<br>Role: {switch['role']}<br>Health: {switch['health']}<br>Power: {switch.get('power_status', 'N/A')}<br>MAC: {switch.get('mac', 'N/A')}<br>Location: {switch.get('location', 'N/A')}"""
        fig.add_trace(go.Scatter(
            x=[right_x], y=[y], mode='markers+text', name=switch["name"], text=[switch["name"]],
            textposition="bottom center",
            marker=dict(size=30, color='rgba(0,0,0,0)'),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=False
        ))
        images_to_add.append(dict(
            source=storage_image,  # Using base64 encoded image
            xref="x", yref="y",
            x=right_x, y=y+0.03,
            sizex=0.06, sizey=0.06,
            xanchor="center", yanchor="middle",
            layer="above"
        ))


    # Backups on right bottom (below storage)
    for i, switch in enumerate(data["backup"]):
        y = 0.9 - (len(data["storage"]) + i) * y_step
        node_positions[switch["id"]] = (right_x, y)
        hover_text = f"""
<b>{switch['name']}</b><br>ID: {switch['id']}<br>Type: {switch['type']}<br>Role: {switch['role']}<br>Health: {switch['health']}<br>Power: {switch.get('power_status', 'N/A')}<br>MAC: {switch.get('mac', 'N/A')}<br>Location: {switch.get('location', 'N/A')}"""
        fig.add_trace(go.Scatter(
            x=[right_x], y=[y], mode='markers+text', name=switch["name"], text=[switch["name"]],
            textposition="bottom center",
            marker=dict(size=30, color='rgba(0,0,0,0)'),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=True
        ))
        images_to_add.append(dict(
            source=backup_image,  # Using base64 encoded image
            xref="x", yref="y",
            x=right_x, y=y+0.03,
            sizex=0.06, sizey=0.06,
            xanchor="center", yanchor="middle",
            layer="above"
        ))


            # Uncommenting this is adding Backup-1 again (need to look at it again)
    # for i, backup in enumerate(data["backup"]):
    #     x = 0.5  # Backup column (middle)
    #     y = 0.9 - (i * 0.18)
    #     node_positions[backup["id"]] = (x, y)
    #     hover_text = f"""
    # <b>{backup['name']}</b><br>ID: {backup['id']}<br>Type: {backup['type']}<br>Role: {backup['role']}<br>Health: {backup['health']}<br>Power: {backup.get('power_status', 'N/A')}<br>MAC: {backup.get('mac', 'N/A')}<br>Location: {backup.get('location', 'N/A')}"""
    #     fig.add_trace(go.Scatter(
    #         x=[x], y=[y], mode='markers+text', name=backup["name"], text=[backup["name"]],
    #         textposition="bottom center",
    #         marker=dict(
    #             size=30,
    #             color='rgba(0,0,0,0)'
    #         ),
    #         hovertext=hover_text,
    #         hoverinfo='text',
    #         showlegend=True
    #     ))
    #     images_to_add.append(dict(
    #         source="images/Backup.png",
    #         xref="x", yref="y",
    #         x=x, y=y+0.03,
    #         sizex=0.06, sizey=0.06,
    #         xanchor="center", yanchor="middle",
    #         layer="above"
    #     ))

    # Add edges (connections)
    for server in data["servers"]:
        for conn in server.get("connected_switches", []):
            switch_id = conn["switch_id"]
            port = conn["port"]
            if server["id"] in node_positions and switch_id in node_positions:
                x0, y0 = node_positions[server["id"]]
                x1, y1 = node_positions[switch_id]
                fig.add_trace(go.Scatter(
                    x=[x0, x1], y=[y0, y1], mode='lines',
                    line=dict(color=health_colour_map.get(server["health"], "gray"), width=3),
                    name=f"{server['name']} → {switch_id}",
                    text=f"Port: {port}",
                    hoverinfo='text',
                    showlegend=False
                ))

    for storage in data["storage"]:
        for conn in storage.get("connected_switches", []):
            switch_id = conn["switch_id"]
            port = conn["port"]
            if storage["id"] in node_positions and switch_id in node_positions:
                x0, y0 = node_positions[storage["id"]]
                x1, y1 = node_positions[switch_id]
                fig.add_trace(go.Scatter(
                    x=[x0, x1], y=[y0, y1], mode='lines',
                    line=dict(color=health_colour_map.get(storage["health"], "gray"), width=3),
                    name=f"{storage['name']} → {switch_id}",
                    text=f"Port: {port}",
                    hoverinfo='text', showlegend=False))

    for backup in data["backup"]:
        for conn in backup.get("connected_switches", []):
            switch_id = conn["switch_id"]
            port = conn["port"]
            if backup["id"] in node_positions and switch_id in node_positions:
                x0, y0 = node_positions[backup["id"]]
                x1, y1 = node_positions[switch_id]
                fig.add_trace(go.Scatter(
                    x=[x0, x1], y=[y0, y1], mode='lines',
                    line=dict(color=health_colour_map.get(backup["health"], "gray"), width=3),
                    name=f"{backup['name']} → {switch_id}",
                    text=f"Port: {port}",
                    hoverinfo='text', showlegend=False))

    fig.update_layout(images=images_to_add)

    cloud_name = data['private_cloud'].get('name', 'Private Cloud') if data['private_cloud'] else 'Private Cloud'
    fig.update_layout(
        title=f"{cloud_name} Architecture",
        showlegend=False, 
        hovermode='closest',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='white', paper_bgcolor='white', width=1000, height=800
    )
    refresh_interval_seconds = INTERVAL_TIME
    meta_refresh_tag = f'<meta http-equiv="refresh" content="{refresh_interval_seconds}">'
    html_content = pio.to_html(fig, full_html=True, include_plotlyjs='cdn')

    if "<head>" in html_content:
        html_content = html_content.replace("<head>", f"<head>\n    {meta_refresh_tag}", 1)
    elif "<html>" in html_content:
         html_content = html_content.replace("<html>", f"<html>\n<head>\n    {meta_refresh_tag}\n</head>", 1)
    else:
        html_content = f"<html><head>{meta_refresh_tag}</head><body>{html_content}</body></html>"

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Interactive topology saved to {output_path} with auto-refresh ({refresh_interval_seconds}s).")
    except IOError as e:
        logger.error(f"Failed to write HTML file {output_path}: {e}")
        return None
    return os.path.abspath(output_path)

_interactive_browser_opened_once = False # a simple flag

def update_all():
    global _interactive_browser_opened_once
    logger.info("Fetching data and regenerating outputs...")
    data = fetch_data_from_supabase()
    if not data:
        logger.error("Could not fetch data from Supabase. Skipping output generation.")
        return

    generate_png_topology(data)
    interactive_html_path = generate_interactive_topology(data)

    if interactive_html_path and not _interactive_browser_opened_once:
        try:
            webbrowser.open(f"file://{interactive_html_path}", new=0, autoraise=True)
            logger.info(f"Opened interactive topology in browser: file://{interactive_html_path}")
            _interactive_browser_opened_once = True
        except Exception as e:
            logger.error(f"Could not open browser for interactive topology: {e}")


class DatabaseMonitor:
    def __init__(self, update_function, check_interval=30):
        self.update_function = update_function
        self.check_interval = check_interval
        self.last_check_time = None
        self.running = False
        self.thread = None
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Database monitoring started. Checking every {self.check_interval} seconds.")
    def _monitor_loop(self):
        while self.running:
            try:
                now = time.time()
                if self.last_check_time is None or (now - self.last_check_time) >= self.check_interval:
                    logger.info("Checking for database changes...")
                    self.last_check_time = now
                    self.update_function()
            except Exception as e:
                logger.error(f"Error monitoring database: {e}")
            time.sleep(1)
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        logger.info("Database monitoring stopped.")

if __name__ == "__main__":
    logger.info("Generating initial topology (PNG + HTML)...")
    update_all()
    db_monitor = DatabaseMonitor(update_all, check_interval=INTERVAL_TIME)
    db_monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        db_monitor.stop()
        logger.info("Program terminated by user.")