import os
import time
import threading
import logging
import requests
import smtplib
import ssl
import base64
import datetime 
from email.message import EmailMessage


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xpchztgrhfhgtcekazan.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwY2h6dGdyaGZoZ3RjZWthemFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxNTY3MTUsImV4cCI6MjA2MDczMjcxNX0.VUKKlhtXgZdr2G4U-CGOjHH6TgugrPyg0cFzePzC4Q8")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "ENTER_MAIL_ID_HERE")
APP_PASSWORD = os.getenv("APP_PASSWORD", "ENTER_APP_PASSWORD_HERE")

HEALTH_COLOUR_MAP = {
    "healthy": "green",
    "degraded": "orange",
    "critical": "red",
    "unknown": "gray"
}

alerted_components = set()

def get_default_image_data_uri():
    """Return a simple default image as data URI if no image is found"""
    # A simple gray box as fallback
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAAGYktHRAD/AP0A/6C9p5MAAAAJcEhZcwAALiMAAC4jAXilP3YAAAAHdElNRQfnBQ4WNzd6B8JvAAABQ0lEQVRo3u2ZMU7DMBSGv1Q9QcUBygEYWdgZGFkg6tY7VOIOMAGdGZhYWCAxwgVgR0JIUHKADgwsVSwgQUhJ/Ow0wf2W2KrjfK+/5+c3VpAkyX+UDdYrwBOwC4yAe+DBGLNIbjiO433gRRn7SNJW7HpFePQlvEm6qHFuVtKbMjZLWq8TYA8YK+OxpKPKF9BY0LqfTWPMQZTxhccYk3vfZuLedGIjXCfCRoiJEBthJsL/b4Sp3wnOBUkfkqbAYZZlP8aYh5hFQx/gTNJlvh8CZ0AXuAGuYhVMcYDdEfAO3AC7wCmQ5XEa0SZICiHpy26HiW1yGKQcL0mW0ltRo6nHWknPpkLUDRBbChBvQUtVKBYhOkAtLYGoAE5aCuAk9TX6DGzl+y5wGrPYskcrU6Y34BK4A76BAfBojMniVksikWiML4YT3HO+95XBAAAAAElFTkSuQmCC"

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


def fetch_table(table_name, select_cols="*"):
    """Fetches data from a specified Supabase table with selectable columns."""
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get(url, headers=headers, params={"select": select_cols})
        resp.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {table_name} from Supabase: {e}")
        return []

def set_last_sync_timestamp(timestamp):
    """Updates the last_sync timestamp in the private_cloud table in Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/private_cloud"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal" # To get minimal response
    }
    data = {"last_sync": timestamp}
    try:
        resp = requests.patch(url, headers=headers, json=data, params={"id": "eq.1"})
        resp.raise_for_status()
        logger.info(f"Updated private_cloud last_sync to: {timestamp}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating private_cloud last_sync: {e}")

def get_last_sync_timestamp():
    """Fetches only the last_sync timestamp from the private_cloud table."""
    try:
        private_cloud_data = fetch_table('private_cloud', select_cols='last_sync')
        if private_cloud_data and len(private_cloud_data) > 0:
            return private_cloud_data[0].get('last_sync')
        return None
    except Exception as e:
        logger.error(f"Error getting last sync timestamp: {e}")
        return None

def fetch_data_from_supabase():
    """Fetches and processes all relevant data from Supabase for topology."""
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


        all_components = servers + network_switches + storage + backup
        for comp in all_components:
            if comp.get("health") == "critical" and comp["id"] not in alerted_components:
                ip_address = comp.get("ip_address", "N/A")
                mac_address = comp.get("mac", "N/A")
                location = comp.get("location", "N/A")
                
                connected_switches = comp.get("connected_switches", [])
                switch_details = "\n".join(
                    [f"  - Switch ID: {conn['switch_id']}, Port: {conn['port']}" for conn in connected_switches]
                ) if connected_switches else "  - None"

                detailed_body = f"""
Critical Component Alert

Time of Detection: {time.strftime('%Y-%m-%d %H:%M:%S')}
Private Cloud: {private_cloud.get('name', 'Unknown')}
Last Sync: {private_cloud.get('last_sync', 'Unknown')}

Component Details:
- Name: {comp['name']}
- ID: {comp['id']}
- Type: {comp.get('type', 'N/A')}
- Role: {comp.get('role', 'N/A')}
- Health Status: CRITICAL
- Power Status: {comp.get('power_status', 'N/A')}
- MAC Address: {mac_address}
- IP Address: {ip_address}
- Location: {location}
- Connected Switches:
{switch_details}

This is an automated alert from the Topology Monitoring System.
"""
                send_email_alert_async(
                    subject=f"Critical Alert: {comp['name']}",
                    body=detailed_body
                )
                alerted_components.add(comp["id"]) 
            elif comp.get("health") != "critical" and comp["id"] in alerted_components:
                alerted_components.discard(comp["id"])


        current_iso_time = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds') + 'Z'
        set_last_sync_timestamp(current_iso_time)

        return {
            "private_cloud": private_cloud,
            "servers": servers,
            "network_switches": network_switches,
            "storage": storage,
            "backup": backup,
            "health_color_map": HEALTH_COLOUR_MAP
        }
    except Exception as e:
        logger.error(f"Error in fetch_data_from_supabase: {e}")
        return None

# --- Email Alert ---
def send_email_alert_async(subject, body):
    """Sends an email alert in a separate thread."""
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


if __name__ == "__main__":
    logger.info("Fetching initial data and checking for alerts...")
    data = fetch_data_from_supabase()
    if data:
        logger.info("Data fetched successfully.")
    else:
        logger.error("Failed to fetch data.")
