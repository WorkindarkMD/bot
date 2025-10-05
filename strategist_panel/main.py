import asyncio
import websockets
import json
import logging

# --- Configuration ---
CORE_WS_URL = "ws://localhost:8766"
LOG_LEVEL = logging.INFO

# --- Logging Setup ---
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StrategistPanel")

async def listen_to_core():
    """
    Подключается к ядру Gem.Bot и слушает обновления.
    """
    logger.info("Панель Стратега запущена.")
    while True:
        try:
            async with websockets.connect(CORE_WS_URL) as websocket:
                logger.info(f"Установлено соединение с ядром Gem.Bot по адресу {CORE_WS_URL}")
                while True:
                    message = await websocket.recv()
                    try:
                        data = json.loads(message)

                        # Красивый вывод данных в консоль
                        if data.get('type') == 'core_update':
                            features = data.get('features', {})
                            prediction = data.get('prediction', 'N/A')

                            wap = features.get('wap', 0)
                            spread = features.get('spread', 0)
                            imbalance = features.get('book_imbalance_5_levels', 0)

                            print("-" * 50)
                            print(f"СИГНАЛ: {prediction}")
                            print(f"  WAP: {wap:.2f} | Spread: {spread:.4f} | Imbalance: {imbalance:.4f}")
                            print("-" * 50)
                        else:
                            print(json.dumps(data, indent=2))

                    except json.JSONDecodeError:
                        logger.warning(f"Получено некорректное JSON-сообщение: {message}")
                    except Exception as e:
                        logger.error(f"Ошибка при обработке сообщения от ядра: {e}")

        except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError) as e:
            logger.warning(f"Не удалось подключиться к ядру: {e}. Повтор через 5 секунд...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            await asyncio.sleep(5)


async def main():
    try:
        await listen_to_core()
    except asyncio.CancelledError:
        logger.info("Задача панели была отменена.")
    finally:
        logger.info("Панель Стратега была остановлена.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка по требованию пользователя.")