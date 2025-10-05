import asyncio
import websockets
import json
import logging
from websockets.exceptions import ConnectionClosed

# --- Configuration ---
CORE_WS_URL = "ws://localhost:8766"
LOG_LEVEL = logging.INFO

# --- Logging Setup ---
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StrategistPanel")

async def listen_to_core():
    """
    Connects to the Gem.Bot core and listens for updates, printing them to the console.
    """
    logger.info("Strategist Panel started.")
    while True:
        try:
            async with websockets.connect(CORE_WS_URL) as websocket:
                logger.info(f"Connection to Gem.Bot core at {CORE_WS_URL} established.")
                while True:
                    message = await websocket.recv()
                    try:
                        data = json.loads(message)

                        # Pretty-print the data to the console
                        if data.get('type') == 'core_update':
                            features = data.get('features', {})
                            prediction = data.get('prediction', 'N/A')

                            wap = features.get('wap', 0)
                            spread = features.get('spread', 0)
                            imbalance = features.get('book_imbalance_5_levels', 0)

                            log_message = f"SIGNAL: {prediction:<5} | WAP: {wap:9.2f} | Spread: {spread:7.4f} | Imbalance: {imbalance:7.4f}"
                            logger.info(log_message)
                        else:
                            # Fallback for other message types
                            logger.info(json.dumps(data, indent=2))

                    except json.JSONDecodeError:
                        logger.warning(f"Received invalid JSON message: {message}")
                    except Exception as e:
                        logger.error(f"Error processing message from core: {e}")

        except (ConnectionClosed, ConnectionRefusedError) as e:
            logger.warning(f"Failed to connect to core: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            await asyncio.sleep(5)

async def main():
    try:
        await listen_to_core()
    except asyncio.CancelledError:
        logger.info("Panel task was cancelled.")
    finally:
        logger.info("Strategist Panel has been stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping on user request.")