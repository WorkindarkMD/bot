import asyncio
import json
import logging
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed
from typing import Set

from gem_bot_core.modules.feature_extractor import FeatureExtractor
from gem_bot_core.modules.prediction_simulator import PredictionSimulator

# --- Configuration ---
ORACLE_PORT = 8765
STRATEGIST_PORT = 8766
PROCESSING_INTERVAL_SECONDS = 1
LOG_LEVEL = logging.INFO

# --- Logging Setup ---
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GemBotCore")


class GemBotCore:
    """
    The central AI core. It receives data from "Oracle" agents, processes it,
    and broadcasts the results to the "Strategist Panel".
    """
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.prediction_simulator = PredictionSimulator()
        self.oracle_clients: Set[WebSocketServerProtocol] = set()
        self.strategist_clients: Set[WebSocketServerProtocol] = set()
        self._running = True

    async def handle_oracle_connection(self, websocket: WebSocketServerProtocol):
        """
        Handles incoming connections from "Oracle" agents.
        """
        self.oracle_clients.add(websocket)
        logger.info(f"Oracle Agent connected: {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if 'arg' in data and data['arg'].get('channel') == 'books':
                        self.feature_extractor.update_order_book(data)
                    elif 'arg' in data and data['arg'].get('channel') == 'trade':
                        self.feature_extractor.add_trade(data)
                    else:
                        logger.debug(f"Received service message from Oracle: {message[:150]}")
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON from Oracle: {message}")
                except Exception as e:
                    logger.error(f"Error processing message from Oracle: {e}", exc_info=True)
        except ConnectionClosed:
            logger.info(f"Oracle Agent disconnected: {websocket.remote_address}")
        finally:
            self.oracle_clients.remove(websocket)

    async def handle_strategist_connection(self, websocket: WebSocketServerProtocol):
        """
        Handles incoming connections from the "Strategist Panel".
        """
        self.strategist_clients.add(websocket)
        logger.info(f"Strategist Panel connected: {websocket.remote_address}")
        try:
            await websocket.wait_closed()
        finally:
            logger.info(f"Strategist Panel disconnected: {websocket.remote_address}")
            self.strategist_clients.remove(websocket)

    async def broadcast_to_strategists(self, message: str):
        """Sends a message to all connected strategists."""
        if self.strategist_clients:
            await asyncio.gather(
                *[client.send(message) for client in self.strategist_clients],
                return_exceptions=True  # Avoids one failed send from stopping others
            )

    async def processing_loop(self):
        """The main data processing and signal generation loop."""
        logger.info("Starting main processing loop...")
        while self._running:
            await asyncio.sleep(PROCESSING_INTERVAL_SECONDS)
            try:
                features = self.feature_extractor.extract_features()
                if features is None:
                    continue

                prediction = self.prediction_simulator.get_prediction(features)

                result = {
                    'type': 'core_update',
                    'features': features,
                    'prediction': prediction
                }

                await self.broadcast_to_strategists(json.dumps(result, default=str))
                logger.info(f"Signal generated and sent: {prediction}, WAP: {features.get('wap', 'N/A'):.2f}")

            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)

    async def start(self):
        """Starts all core components."""
        logger.info(f"Starting Oracle server on port {ORACLE_PORT}...")
        oracle_server = await websockets.serve(self.handle_oracle_connection, "localhost", ORACLE_PORT)

        logger.info(f"Starting Strategist server on port {STRATEGIST_PORT}...")
        strategist_server = await websockets.serve(self.handle_strategist_connection, "localhost", STRATEGIST_PORT)

        processing_task = asyncio.create_task(self.processing_loop())

        await processing_task

    def stop(self):
        self._running = False


async def main():
    core = GemBotCore()
    try:
        await core.start()
    except asyncio.CancelledError:
        logger.info("Core task was cancelled.")
    finally:
        core.stop()
        logger.info("Gem.Bot Core has been stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping on user request.")