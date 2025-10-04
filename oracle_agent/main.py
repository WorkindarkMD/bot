import asyncio
import websockets
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

AGENT_ID = "ORACLE_01"
HEARTBEAT_INTERVAL = 5  # seconds
SERVER_URI = "ws://localhost:8765"

async def send_heartbeat():
    """
    Connects to the server and sends a heartbeat message every 5 seconds.
    """
    while True:
        try:
            async with websockets.connect(SERVER_URI) as websocket:
                logging.info(f"Connected to Gem.Bot Core at {SERVER_URI}")

                # First, identify this client as an Oracle Agent
                await websocket.send("oracle")
                logging.info("Identified as an Oracle Agent.")

                while True:
                    # Prepare the heartbeat message
                    heartbeat_message = {
                        "agent_id": AGENT_ID,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "alive"
                    }

                    await websocket.send(json.dumps(heartbeat_message))
                    logging.info(f"Sent heartbeat: {heartbeat_message}")

                    await asyncio.sleep(HEARTBEAT_INTERVAL)

        except websockets.exceptions.ConnectionClosed as e:
            logging.error(f"Connection to server lost: {e}. Retrying in {HEARTBEAT_INTERVAL} seconds...")
        except ConnectionRefusedError:
            logging.error(f"Connection refused. Is the Gem.Bot Core server running? Retrying in {HEARTBEAT_INTERVAL} seconds...")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}. Retrying in {HEARTBEAT_INTERVAL} seconds...")

        await asyncio.sleep(HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(send_heartbeat())
    except KeyboardInterrupt:
        logging.info("Oracle Agent is shutting down.")