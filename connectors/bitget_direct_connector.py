import asyncio
import websockets
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# As per the official Bitget documentation for Spot WebSocket
BITGET_WS_URL = "wss://ws.bitget.com/spot/v1/stream"

class BitgetDirectConnector:
    """
    A direct, robust, and integratable WebSocket connector for Bitget,
    written from scratch using the 'websockets' library.
    """
    def __init__(self, symbols: list, channels: list, on_message_callback: callable):
        """
        :param symbols: A list of trading pairs (e.g., ['BTCUSDT']).
        :param channels: A list of channels to subscribe to (e.g., ['books', 'trade']).
        :param on_message_callback: An async function to be called for each message.
        """
        self.ws_url = BITGET_WS_URL
        self.on_message_callback = on_message_callback
        # Dynamically create subscription arguments from symbols and channels
        self.subscription_args = [
            {"instType": "SP", "channel": ch, "instId": sym}
            for sym in symbols
            for ch in channels
        ]
        self.websocket = None
        self._is_running = False
        self._main_task = None

    async def _run(self):
        """The main loop that handles connection and reconnection."""
        while self._is_running:
            try:
                logger.info(f"Connector: Connecting to {self.ws_url}...")
                async with websockets.connect(self.ws_url, ping_interval=None) as ws:
                    self.websocket = ws
                    logger.info("Connector: Bitget connection established.")
                    await self._subscribe()

                    consumer_task = asyncio.create_task(self._message_consumer())
                    pinger_task = asyncio.create_task(self._ping_handler())

                    # Wait for either task to complete (which indicates a disconnect)
                    done, pending = await asyncio.wait(
                        {consumer_task, pinger_task},
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in pending:
                        task.cancel()

            except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
                logger.error(f"Connector: Connection closed/refused: {e}. Reconnecting in 5 seconds...")
            except Exception as e:
                logger.error(f"Connector: An unexpected error occurred: {e}. Reconnecting in 5 seconds...", exc_info=True)

            if self._is_running:
                await asyncio.sleep(5)

    async def _subscribe(self):
        """Sends the subscription message based on the initialized arguments."""
        if not self.subscription_args:
            logger.warning("Connector: No subscription arguments provided.")
            return
        subscription_payload = {
            "op": "subscribe",
            "args": self.subscription_args
        }
        await self.websocket.send(json.dumps(subscription_payload))
        logger.info(f"Connector: Subscription message sent: {subscription_payload}")

    async def _message_consumer(self):
        """Consumes messages and forwards them via the callback."""
        try:
            async for message in self.websocket:
                if message == "pong":
                    continue
                await self.on_message_callback(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connector: Consumer task stopped due to connection closure.")

    async def _ping_handler(self):
        """Sends a 'ping' message every 25 seconds to keep the connection alive."""
        while True:
            try:
                await asyncio.sleep(25)
                await self.websocket.ping()
            except websockets.exceptions.ConnectionClosed:
                logger.info("Connector: Pinger task stopped.")
                break

    def start(self):
        """Starts the connector in a background task."""
        if not self._is_running:
            self._is_running = True
            self._main_task = asyncio.create_task(self._run())
            logger.info("Connector: Started.")

    def stop(self):
        """Stops the connector and cleans up tasks."""
        if self._is_running:
            self._is_running = False
            if self._main_task:
                self._main_task.cancel()
            logger.info("Connector: Stop requested.")

# --- Test Block ---
if __name__ == '__main__':
    async def test_handler(msg):
        print(f"DATA RECEIVED: {msg}")

    async def main_test():
        logger.info("--- Testing Direct Bitget Connector (From Scratch) ---")
        connector = BitgetDirectConnector(on_message_callback=test_handler)
        connector.start()
        try:
            await asyncio.sleep(60)
        finally:
            logger.info("Test finished. Stopping connector.")
            connector.stop()

    try:
        asyncio.run(main_test())
    except KeyboardInterrupt:
        logger.info("\nTest stopped by user.")