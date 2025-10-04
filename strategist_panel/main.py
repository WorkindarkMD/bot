import asyncio
import websockets
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SERVER_URI = "ws://localhost:8765"

async def listen_for_updates():
    """
    Connects to the Gem.Bot Core server and listens for incoming messages.
    """
    while True:
        try:
            async with websockets.connect(SERVER_URI) as websocket:
                logging.info(f"Connected to Gem.Bot Core at {SERVER_URI}")

                # First, identify this client as a Strategist Panel
                await websocket.send("strategist")
                logging.info("Identified as a Strategist Panel. Awaiting heartbeats...")

                # Listen for messages from the server
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        logging.info("--- Heartbeat Received ---")
                        logging.info(f"  Agent ID:    {data.get('agent_id', 'N/A')}")
                        logging.info(f"  Timestamp:   {data.get('timestamp', 'N/A')}")
                        logging.info(f"  Status:      {data.get('status', 'N/A')}")
                        logging.info("--------------------------")
                    except json.JSONDecodeError:
                        logging.warning(f"Received non-JSON message: {message}")

        except websockets.exceptions.ConnectionClosed as e:
            logging.error(f"Connection to server lost: {e}. Retrying in 5 seconds...")
        except ConnectionRefusedError:
            logging.error(f"Connection refused. Is the Gem.Bot Core server running? Retrying in 5 seconds...")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}. Retrying in 5 seconds...")

        await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(listen_for_updates())
    except KeyboardInterrupt:
        logging.info("Strategist Panel is shutting down.")