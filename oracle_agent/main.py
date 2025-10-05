import asyncio
import json
import websockets
import logging
from websockets.exceptions import ConnectionClosed, ConnectionClosedError

from connectors.bitget_direct_connector import BitgetDirectConnector

# --- Configuration ---
GEM_BOT_CORE_WS_URL = "ws://localhost:8765"
LOG_LEVEL = logging.INFO

# --- Logging Setup ---
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OracleAgent")

class OracleAgent:
    """
    The "Oracle" agent: gathers data from the exchange and forwards it to the core.
    Uses a queue to decouple data receiving from data forwarding, enhancing robustness.
    """
    def __init__(self, core_ws_url: str):
        self.data_queue = asyncio.Queue()
        self.connector = BitgetDirectConnector(
            symbols=["BTCUSDT"],
            channels=["trade", "books"],
            on_message_callback=self.handle_exchange_message
        )
        self.core_ws_url = core_ws_url
        self._running = True

    async def handle_exchange_message(self, message: str):
        """
        Callback function invoked by the connector upon receiving a message from the exchange.
        Places the message into a queue for further processing.
        """
        try:
            await self.data_queue.put(message)
        except Exception as e:
            logger.error(f"Error handling exchange message: {e}")

    async def forward_data_to_core(self):
        """
        Connects to the Gem.Bot core and forwards data from the queue.
        Implements a resilient reconnection logic.
        """
        while self._running:
            try:
                async with websockets.connect(self.core_ws_url) as websocket:
                    logger.info(f"Connection to Gem.Bot core at {self.core_ws_url} established.")
                    while self._running:
                        message = await self.data_queue.get()
                        if message is None:  # Stop signal
                            break
                        try:
                            await websocket.send(message)
                            logger.debug(f"Message forwarded to core: {message[:100]}...")
                        except ConnectionClosed:
                            logger.warning("Connection to Gem.Bot core lost. Reconnecting...")
                            break
            except (ConnectionClosedError, ConnectionRefusedError) as e:
                logger.warning(f"Failed to connect to Gem.Bot core: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error in forward_data_to_core: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def start(self):
        """Starts the Oracle Agent."""
        logger.info("Starting Oracle Agent...")
        self.connector.start()  # Correctly starts the connector's background task
        forwarding_task = asyncio.create_task(self.forward_data_to_core())
        await forwarding_task

    async def stop(self):
        """Stops the Oracle Agent gracefully."""
        logger.info("Stopping Oracle Agent...")
        self._running = False
        self.connector.stop()
        await self.data_queue.put(None)  # Unblock the forwarder to let it exit
        await asyncio.sleep(1)

async def main():
    agent = OracleAgent(core_ws_url=GEM_BOT_CORE_WS_URL)
    try:
        await agent.start()
    except asyncio.CancelledError:
        logger.info("Agent task was cancelled.")
    finally:
        await agent.stop()
        logger.info("Oracle Agent has been stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping on user request.")