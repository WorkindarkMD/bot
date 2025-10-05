import asyncio
import json
import logging
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed
import sys
from pathlib import Path
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
    Центральное ядро AI. Принимает данные от агентов "Оракул",
    обрабатывает их и транслирует результаты в "Панель Стратега".
    """
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.prediction_simulator = PredictionSimulator()
        self.oracle_clients: Set[WebSocketServerProtocol] = set()
        self.strategist_clients: Set[WebSocketServerProtocol] = set()
        self._running = True

    async def handle_oracle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Обрабатывает входящие соединения от агентов 'Оракул'."""
        self.oracle_clients.add(websocket)
        logger.info(f"Агент 'Оракул' подключился: {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Определяем тип данных и обновляем соответствующий модуль
                    if 'arg' in data and data['arg'].get('channel') == 'books':
                        self.feature_extractor.update_order_book(data)
                    elif 'arg' in data and data['arg'].get('channel') == 'trade':
                        self.feature_extractor.add_trade(data)
                    else:
                        # Обработка других типов сообщений, например, подтверждение подписки
                        logger.debug(f"Получено сервисное сообщение от Оракула: {message[:150]}")

                except json.JSONDecodeError:
                    logger.warning(f"Получено некорректное JSON-сообщение от Оракула: {message}")
                except Exception as e:
                    logger.error(f"Ошибка при обработке сообщения от Оракула: {e}")
        except ConnectionClosed:
            logger.info(f"Агент 'Оракул' отключился: {websocket.remote_address}")
        finally:
            self.oracle_clients.remove(websocket)

    async def handle_strategist_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Обрабатывает входящие соединения от 'Панели Стратега'."""
        self.strategist_clients.add(websocket)
        logger.info(f"Стратег подключился: {websocket.remote_address}")
        try:
            # Держим соединение открытым, но не ожидаем сообщений от стратега в этой версии
            await websocket.wait_closed()
        except ConnectionClosed:
            logger.info(f"Стратег отключился: {websocket.remote_address}")
        finally:
            self.strategist_clients.remove(websocket)

    async def broadcast_to_strategists(self, message: str):
        """Отправляет сообщение всем подключенным стратегам."""
        if not self.strategist_clients:
            return
        # Используем asyncio.gather для параллельной отправки
        await asyncio.gather(
            *[client.send(message) for client in self.strategist_clients]
        )

    async def processing_loop(self):
        """
        Основной цикл обработки данных и генерации сигналов.
        """
        logger.info("Запуск основного цикла обработки...")
        while self._running:
            await asyncio.sleep(PROCESSING_INTERVAL_SECONDS)
            try:
                # 1. Извлечь признаки
                features = self.feature_extractor.extract_features()
                if features is None:
                    logger.debug("Недостаточно данных для извлечения признаков.")
                    continue

                # 2. Получить предсказание
                prediction = self.prediction_simulator.get_prediction(features)

                # 3. Сформировать и отправить результат
                result = {
                    'type': 'core_update',
                    'features': features,
                    'prediction': prediction
                }

                # Сериализуем в JSON и транслируем стратегам
                await self.broadcast_to_strategists(json.dumps(result))
                logger.info(f"Сгенерирован и отправлен сигнал: {prediction}, WAP: {features.get('wap', 'N/A'):.2f}")

            except Exception as e:
                logger.error(f"Ошибка в цикле обработки: {e}")

    async def start(self):
        """Запускает все компоненты ядра."""
        logger.info(f"Запуск сервера для Оракулов на порту {ORACLE_PORT}...")
        oracle_server = await websockets.serve(self.handle_oracle_connection, "localhost", ORACLE_PORT)

        logger.info(f"Запуск сервера для Стратегов на порту {STRATEGIST_PORT}...")
        strategist_server = await websockets.serve(self.handle_strategist_connection, "localhost", STRATEGIST_PORT)

        processing_task = asyncio.create_task(self.processing_loop())

        await asyncio.gather(processing_task)

    def stop(self):
        self._running = False


async def main():
    core = GemBotCore()
    try:
        await core.start()
    except asyncio.CancelledError:
        logger.info("Задача ядра была отменена.")
    finally:
        core.stop()
        logger.info("Ядро Gem.Bot было остановлено.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка по требованию пользователя.")