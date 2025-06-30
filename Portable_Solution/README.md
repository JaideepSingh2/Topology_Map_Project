# Topology Map Project

This project visualizes cloud architecture topologies with a modern, interactive web interface. It consists of a Python Flask backend (fetching data from Supabase) and a React frontend (using Plotly.js for visualization and Tailwind CSS for styling).

## Features
- **Dynamic Topology Visualization:** Interactive graph of servers, switches, storage, and backup components.
- **Health Status Legend:** Color-coded legend for component health.
- **Live Data Fetching:** Periodic updates from the backend API.
- **Customizable Backend URL:** Easily switch between different backend endpoints.


## Backend Setup (Flask)
1. Ensure Python 3.10+ is installed.
2. Navigate to the backend directory:
   ```bash
   cd Backend
2. Install dependencies:
   ```bash
   pip install flask supabase
3. Configure Supabase credentials in data_utils.py .
4. Run the Flask backend:
   ```bash
   python app.py
   ```
5. Access the backend at http://localhost:5000.

## Frontend Setup (React)
1. Install Node.js and npm.
2. Navigate to the frontend directory:
   ```bash
   cd Frontend
3. Install dependencies:
   ```bash
   npm install
4. Configure the backend URL in src/App.js . (Can skip this step)
5. Start the React frontend:
   ```bash
   npm start
6. Access the frontend at http://localhost:3000.

## Customization
- **Images:** Place custom node images in public/images/ ..
- **API Endpoint:** Change the backend URL in the input box at the top of the app.
