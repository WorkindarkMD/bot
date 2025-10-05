import asyncio
import json
import websockets
import logging
import sys
from pathlib import Path

from connectors.bitget_direct_connector import BitgetDirectConnector

# --- Configuration ---
GEM_BOT_CORE_WS_URL = "ws://localhost:8765"
LOG_LEVEL = logging.INFO

# --- Logging Setup ---
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OracleAgent")

class OracleAgent:
    """
    Агент "Оракул": собирает данные с биржи и передает их в ядро.
    """
    def __init__(self, core_ws_url):
        self.data_queue = asyncio.Queue()
        # Инициализируем коннектор, передавая наш callback
        self.connector = BitgetDirectConnector(
            channels=["trade", "books"],
            on_message_callback=self.handle_exchange_message,
            symbols=["BTCUSDT"]
        )
        self.core_ws_url = core_ws_url
        self._running = True

    async def handle_exchange_message(self, message):
        """
        Callback-функция, которая вызывается коннектором при получении сообщения от биржи.
        Помещает сообщение в очередь для дальнейшей обработки.
        """
        try:
            await self.data_queue.put(message)
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения от биржи: {e}")

    async def forward_data_to_core(self):
        """
        Подключается к ядру Gem.Bot и пересылает данные из очереди.
        Реализует отказоустойчивое переподключение.
        """
        while self._running:
            try:
                async with websockets.connect(self.core_ws_url) as websocket:
                    logger.info(f"Установлено соединение с ядром Gem.Bot по адресу {self.core_ws_url}")
                    while self._running:
                        message = await self.data_queue.get()
                        if message is None:  # Сигнал для остановки
                            break
                        try:
                            # Пересылаем необработанную JSON-строку
                            await websocket.send(message)
                            logger.debug(f"Сообщение переслано в ядро: {message[:100]}...")
                        except websockets.ConnectionClosed:
                            logger.warning("Соединение с ядром Gem.Bot потеряно. Переподключение...")
                            break  # Выходим из внутреннего цикла для переподключения
                        except Exception as e:
                            logger.error(f"Ошибка при отправке данных в ядро: {e}")
            except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError) as e:
                logger.warning(f"Не удалось подключиться к ядру Gem.Bot: {e}. Повтор через 5 секунд...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Неожиданная ошибка в forward_data_to_core: {e}")
                await asyncio.sleep(5) # Ждем перед повторной попыткой

    async def start(self):
        """Запускает агента "Оракул"."""
        logger.info("Запуск агента 'Оракул'...")
        # Запускаем коннектор к бирже в отдельной задаче
        self.connector.start()
        # Запускаем задачу пересылки данных
        forwarding_task = asyncio.create_task(self.forward_data_to_core())

        # Ожидаем завершения задачи пересылки
        await forwarding_task

    async def stop(self):
        """Корректно останавливает агента "Оракул"."""
        logger.info("Остановка агента 'Оракул'...")
        self._running = False
        self.connector.stop()
        # Помещаем 'None' в очередь, чтобы разблокировать и завершить задачу forward_data_to_core
        await self.data_queue.put(None)
        # Даем время на завершение задач
        await asyncio.sleep(1)


async def main():
    agent = OracleAgent(core_ws_url=GEM_BOT_CORE_WS_URL)
    try:
        await agent.start()
    except asyncio.CancelledError:
        logger.info("Задача агента была отменена.")
    finally:
        await agent.stop()
        logger.info("Агент 'Оракул' был остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка по требованию пользователя.")