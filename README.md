# Gem.Bot Ecosystem v3 - Sprint 1: The Nervous System

This repository contains the initial implementation of the Gem.Bot Ecosystem, focusing on establishing the core communication layer between its three main components as outlined in Sprint 1.

## Architecture

The system consists of three distinct components that communicate in real-time via WebSockets:

1.  **Gem.Bot Core (`gem_bot_core/`)**: The central WebSocket server. It acts as a message broker, listening for connections from Oracle Agents and Strategist Panels. Its primary role in this sprint is to receive "heartbeat" messages from agents and forward them to all connected panels.

2.  **Oracle Agent (`oracle_agent/`)**: A WebSocket client that represents a data-gathering or trade-execution bot on a specific exchange. In this sprint, its sole function is to connect to the Gem.Bot Core and periodically send a `heartbeat` message to signal that it is alive and operational.

3.  **Strategist Panel (`strategist_panel/`)**: A WebSocket client that serves as the human operator's command center. In this sprint, it connects to the Gem.Bot Core and listens for the forwarded `heartbeat` messages, displaying them in the console to provide a real-time status overview of all connected agents.

## How to Run the System

To test the "Nervous System," you need to run all three components simultaneously in separate terminal windows.

### Prerequisites

First, install the necessary Python library:

```bash
pip install -r requirements.txt
```

### Step 1: Start the Gem.Bot Core Server

In your first terminal, navigate to the project root and run:

```bash
python gem_bot_core/main.py
```

You should see a log message indicating the server has started, e.g., `INFO:root:Starting Gem.Bot Core WebSocket server on ws://localhost:8765`.

### Step 2: Start the Strategist Panel

In a second terminal, run the Strategist Panel client:

```bash
python strategist_panel/main.py
```

The panel will connect to the server and wait for messages. You will see a log confirming the connection.

### Step 3: Start the Oracle Agent

In a third terminal, run the Oracle Agent client:

```bash
python oracle_agent/main.py
```

The agent will connect to the server and begin sending a heartbeat every 5 seconds.

### Verification

Once the agent is running, you will see:
-   **In the Agent's terminal:** Log messages indicating that a heartbeat is being sent.
-   **In the Core's terminal:** Log messages showing it received a heartbeat and forwarded it.
-   **In the Panel's terminal:** A formatted printout of the heartbeat data, confirming that the entire communication loop is working.

You can start multiple instances of the `strategist_panel` or `oracle_agent` to see the server handle them correctly.