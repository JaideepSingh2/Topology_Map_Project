import time
import random
import threading
import logging
import requests
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = "https://xpchztgrhfhgtcekazan.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwY2h6dGdyaGZoZ3RjZWthemFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxNTY3MTUsImV4cCI6MjA2MDczMjcxNX0.VUKKlhtXgZdr2G4U-CGOjHH6TgugrPyg0cFzePzC4Q8"

# Component configurations
COMPONENT_TYPES = ["KVM", "Ceph", "Switch", "NAS"]
HEALTH_STATUSES = ["healthy", "degraded", "critical"]
EVENT_TYPES = ["status_change", "power_cycle", "network_issue", "storage_alert"]

class EventGenerator:
    def __init__(self):
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        logger.info("Successfully initialized event generator")
        self.component_ids = self.fetch_all_component_ids()

    def fetch_all_component_ids(self) -> Dict[str, list]:
        """Fetch all real component IDs from Supabase tables"""
        table_map = {
            "KVM": "servers",
            "Ceph": "storage",
            "Switch": "network_switches",
            "NAS": "backup"
        }
        ids = {key: [] for key in table_map}
        for comp_type, table in table_map.items():
            try:
                url = f"{SUPABASE_URL}/rest/v1/{table}"
                resp = requests.get(url, headers=self.headers, params={"select": "id"})
                resp.raise_for_status()
                data = resp.json()
                ids[comp_type] = [row["id"] for row in data if "id" in row]
            except Exception as e:
                logger.error(f"Error fetching IDs from {table}: {e}")
        logger.info(f"Fetched component IDs: {ids}")
        return ids

    def generate_random_event(self) -> Dict:
        """Generate a random event with realistic component IDs"""
        component_type = random.choice(COMPONENT_TYPES)
        component_id = random.choice(self.component_ids[component_type])
        
        # Generate a new health status with weighted probabilities
        health_weights = {
            "healthy": 0.6,    # 60% chance of healthy
            "degraded": 0.3,   # 30% chance of degraded
            "critical": 0.1    # 10% chance of critical
        }
        health_status = random.choices(
            list(health_weights.keys()),
            weights=list(health_weights.values())
        )[0]
        
        event = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "component_type": component_type,
            "component_id": component_id,
            "event_type": random.choice(EVENT_TYPES),
            "health_status": health_status,
            "details": f"Random event for {component_type} {component_id}"
        }
        return event

    def update_component_status(self, event: Dict) -> None:
        """Update only the health status of an existing component in Supabase. Does NOT change any connections or other fields."""
        try:
            # Map component type to table name
            table_name = self._get_table_name(event["component_type"])
            if table_name:
                url = f"{SUPABASE_URL}/rest/v1/{table_name}"
                # Only update the health field, do not send any other data
                update_data = {
                    "health": event["health_status"]
                }
                component_id = event["component_id"]
                response = requests.patch(
                    f"{url}?id=eq.{component_id}",
                    headers=self.headers,
                    json=update_data
                )
                response.raise_for_status()
                logger.info(f"Updated {event['component_type']} {component_id} status to {event['health_status']}")
        except Exception as e:
            logger.error(f"Error updating Supabase: {str(e)}")

    def _get_table_name(self, component_type: str) -> str:
        """Map component type to table name"""
        table_map = {
            "KVM": "servers",
            "Ceph": "storage",
            "Switch": "network_switches",
            "NAS": "backup"
        }
        return table_map.get(component_type, "")

def event_loop(interval: int = 30):
    """Main event loop that generates and updates events"""
    generator = EventGenerator()
    try:
        while True:
            event = generator.generate_random_event()
            generator.update_component_status(event)
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Event generation stopped by user.")
    except Exception as e:
        logger.error(f"Error in event loop: {str(e)}")

def main():
    """Main entry point"""
    logger.info("Starting random event generator...")
    try:
        event_loop(interval=1)  # Generate events every 10 seconds
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    main() 