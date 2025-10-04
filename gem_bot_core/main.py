import asyncio
import websockets
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Sets to store connected clients
ORACLE_AGENTS = set()
STRATEGIST_PANELS = set()

async def register_client(websocket):
    """
    Registers a new client, identifying them as an Oracle Agent or a Strategist Panel.
    """
    try:
        # The first message from a client should be its identification
        identity = await websocket.recv()
        if identity == "oracle":
            ORACLE_AGENTS.add(websocket)
            logging.info(f"Oracle Agent connected: {websocket.remote_address}")
        elif identity == "strategist":
            STRATEGIST_PANELS.add(websocket)
            logging.info(f"Strategist Panel connected: {websocket.remote_address}")
        else:
            logging.warning(f"Unknown client type connected: {identity}. Disconnecting.")
            await websocket.close()
            return False
        return True
    except websockets.exceptions.ConnectionClosed:
        logging.info("Client disconnected during registration.")
        return False

async def unregister_client(websocket):
    """
    Unregisters a client upon disconnection.
    """
    if websocket in ORACLE_AGENTS:
        ORACLE_AGENTS.remove(websocket)
        logging.info(f"Oracle Agent disconnected: {websocket.remote_address}")
    elif websocket in STRATEGIST_PANELS:
        STRATEGIST_PANELS.remove(websocket)
        logging.info(f"Strategist Panel disconnected: {websocket.remote_address}")

async def message_handler(websocket):
    """
    Handles incoming messages from all clients.
    """
    is_registered = await register_client(websocket)
    if not is_registered:
        return

    try:
        # Listen for messages from Oracle Agents
        async for message in websocket:
            if websocket in ORACLE_AGENTS:
                logging.info(f"Received heartbeat from Oracle Agent: {message}")

                # Forward the message to all Strategist Panels
                if STRATEGIST_PANELS:
                    # Use asyncio.gather to send messages concurrently
                    await asyncio.gather(*[panel.send(message) for panel in STRATEGIST_PANELS])
                    logging.info(f"Forwarded heartbeat to {len(STRATEGIST_PANELS)} Strategist Panel(s).")

    except websockets.exceptions.ConnectionClosedError:
        logging.info(f"Connection closed with error for client: {websocket.remote_address}")
    except Exception as e:
        logging.error(f"An unexpected error occurred with client {websocket.remote_address}: {e}")
    finally:
        await unregister_client(websocket)

async def main():
    host = "localhost"
    port = 8765
    logging.info(f"Starting Gem.Bot Core WebSocket server on ws://{host}:{port}")

    async with websockets.serve(message_handler, host, port):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server is shutting down.")