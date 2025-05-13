# Topology mapping for a private cloud 

## Basic Overview
This repository consists of two main components that work together to create and maintain real-time visualisations of a private cloud infrastructure. The system monitors component health, generates topology diagrams, and sends alerts when critical issues are detected.

## Contents
- Generator Files (for both event and topology)
- Technical details (of database and visualisations)
- Modifying the Topology (components & connections)
- Misc. Details (update period, output files)

## A) The important generator files

### 1. Event Generator (`events.py`)

#### What does it do?
- Generates random events for different component types (KVM, Ceph, Switch, NAS)
- Updates respective component health status in Supabase
- Health status changes with probablities (configurable, to be substituted with actual events later):
  - Healthy (Green): 60% 
  - Degraded (Orange): 30% 
  - Critical (Red): 10%

### 2. Topology Generator (`combined_topology.py`)


#### What does it do?

- Create PNG diagrams using `diagrams` library and an interactive HTML visualisation using Plotly
- Real-time monitoring of infrastructure changes with email alerts if the updates are critical
- Colour coded health checks for components

## B) Technical Details

### Database Structure
Supabase with the following tables for components-
- `servers`: KVM compute nodes
- `storage`: Ceph storage nodes
- `network_switches`: Network infrastructure
- `backup`: NAS backup systems

Then for switch connections-
- `server_connected_switches`: Server-to-switch connections
- `storage_connected_switches`: Storage-to-switch connections
- `backup_connected_switches`: Backup-to-switch connections
- `network_connected_components`: General network connections

### How is it visualised?

#### PNG Diagram
Left-to-right layout with components clustered (Compute, Storage, Network, Backup) and health-status coloured connections

#### HTML Topology
A logical positioning where non-switch nodes are on the left and switch nodes are on the right.

On hover information includes component info (name, ID, type, role, health/power status) and relevant conponent-specific details (CPU, MAC, IP, etc.)

Component types are represented with specific and recognisable icons; edge connections show port information.

## C) Modifying the Topology

### To the Components:
1. **Adding New Components -**
Must be added to appropriate Supabase table and include all required fields (name, type, role, health)

2. **Removing Components -**
Remove the component from the Supabase table as well as its associated connections.

3. **Status Changes -**
Everything is automatically reflected in both PNG and HTML outputs after a configurable update period (we take it as 10 seconds). If status becomes critical, will trigger an email notification.

### To the Connections:
1. **Adding Connections -**
Add it to the appropriate connection table in Supabase. Note - specify the correct port numbers please.

2. **Modifying Connections -**
Update that specific connection's details in Supabase. 

3. **Removing Connections -**
Simply delete the connection from the appropriate table.

## Miscellaneous Details

### Update Intervals
- Event generation: 10 seconds (configurable)
- Topology updates: 10 seconds (configurable)

### Outputs created
- PNG Diagram: `HPE_topology.png`
- Interactive HTML: `HPE_topology.html`
