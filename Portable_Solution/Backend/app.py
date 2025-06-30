import os
from flask import Flask, jsonify
from flask_cors import CORS
from data_utils import fetch_data_from_supabase, get_last_sync_timestamp, logger

app = Flask(__name__)

CORS(app) 

@app.route('/api/topology_data', methods=['GET'])
def get_topology_data():
    """
    API endpoint to fetch the latest topology data from Supabase.
    This data is then sent to the frontend for visualization.
    """
    logger.info("Received request for topology data.")
    data = fetch_data_from_supabase()
    if data:
        logger.info("Topology data fetched and ready to send.")
        return jsonify(data), 200
    else:
        logger.error("Failed to retrieve topology data.")
        return jsonify({"error": "Failed to retrieve topology data"}), 500

@app.route('/api/last_sync_timestamp', methods=['GET'])
def get_sync_timestamp():
    """
    API endpoint to fetch only the last sync timestamp from the private_cloud table.
    This is used by the frontend to efficiently check for updates.
    """
    logger.info("Received request for last sync timestamp.")
    timestamp = get_last_sync_timestamp()
    if timestamp is not None:
        return jsonify({"last_sync": timestamp}), 200
    else:
        logger.warning("Could not retrieve last sync timestamp.")
        return jsonify({"last_sync": None, "error": "Could not retrieve timestamp"}), 500


@app.route('/')
def home():
    """
    A simple home route for the Flask app to indicate it's running.
    """
    return "Topology Backend is running. Access /api/topology_data for data or /api/last_sync_timestamp for timestamp.", 200

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000, debug=True)
    logger.info("Flask backend started on http://0.0.0.0:5000")
