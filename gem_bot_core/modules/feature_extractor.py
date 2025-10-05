import numpy as np
from collections import deque
import time

class FeatureExtractor:
    """
    Извлекает микроструктурные признаки из рыночных данных в реальном времени.
    Этот класс является stateful, он поддерживает актуальное состояние
    книги заявок и недавних сделок.
    """
    def __init__(self, max_trades=100):
        """
        Инициализация FeatureExtractor.
        :param max_trades: Количество последних сделок для хранения и анализа.
        """
        self.order_book = {'bids': {}, 'asks': {}}
        self.last_update_ts = None
        self.trades = deque(maxlen=max_trades)
        self.last_trade_ts = None

    def update_order_book(self, data):
        """
        Обновляет состояние книги заявок на основе данных от коннектора.
        Обрабатывает как 'snapshot' (полный снимок), так и 'update' (инкрементальные изменения).
        """
        # Bitget сначала присылает snapshot, затем обновления
        if data['action'] == 'snapshot':
            # Преобразуем строки в float для вычислений
            self.order_book['bids'] = {float(price): float(size) for price, size in data['data'][0]['bids']}
            self.order_book['asks'] = {float(price): float(size) for price, size in data['data'][0]['asks']}
        elif data['action'] == 'update':
            for side in ['bids', 'asks']:
                for price, size in data['data'][0][side]:
                    price, size = float(price), float(size)
                    if size == 0:
                        # Если размер 0, удаляем уровень цены
                        if price in self.order_book[side]:
                            del self.order_book[side][price]
                    else:
                        self.order_book[side][price] = size

        self.last_update_ts = int(data['data'][0]['ts'])

    def add_trade(self, data):
        """
        Добавляет новые сделки в очередь для анализа.
        """
        for trade in data['data']:
            ts, price, size, side = trade
            self.trades.append({
                'ts': int(ts),
                'price': float(price),
                'size': float(size),
                'side': side
            })
        if data['data']:
            self.last_trade_ts = int(data['data'][-1][0])

    def extract_features(self):
        """
        Извлекает и вычисляет набор микроструктурных признаков из текущего состояния.
        :return: Словарь с признаками или None, если данных недостаточно.
        """
        if not self.order_book['bids'] or not self.order_book['asks']:
            return None

        # Сортируем биды (desc) и аски (asc) для нахождения лучших цен
        sorted_bids = sorted(self.order_book['bids'].items(), key=lambda x: x[0], reverse=True)
        sorted_asks = sorted(self.order_book['asks'].items(), key=lambda x: x[0])

        best_bid_price, best_bid_size = sorted_bids[0]
        best_ask_price, best_ask_size = sorted_asks[0]

        # 1. Bid-Ask Spread
        spread = best_ask_price - best_bid_price

        # 2. Mid-Price (Средняя цена)
        mid_price = (best_ask_price + best_bid_price) / 2

        # 3. Weighted Average Price (WAP) - Средневзвешенная цена
        wap = (best_bid_price * best_ask_size + best_ask_price * best_bid_size) / (best_bid_size + best_ask_size)

        # 4. Book Imbalance (Дисбаланс книги заявок по 5 уровням)
        bid_depth = sum(size for price, size in sorted_bids[:5])
        ask_depth = sum(size for price, size in sorted_asks[:5])
        book_imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0

        # 5. Trade Imbalance (Дисбаланс по сделкам)
        buy_volume = sum(t['size'] for t in self.trades if t['side'] == 'buy')
        sell_volume = sum(t['size'] for t in self.trades if t['side'] == 'sell')
        total_volume = buy_volume + sell_volume
        trade_imbalance = (buy_volume - sell_volume) / total_volume if total_volume > 0 else 0

        features = {
            'timestamp': time.time(),
            'best_bid': best_bid_price,
            'best_ask': best_ask_price,
            'spread': spread,
            'mid_price': mid_price,
            'wap': wap,
            'book_imbalance_5_levels': book_imbalance,
            'trade_imbalance': trade_imbalance,
            'last_book_update_ts': self.last_update_ts,
            'last_trade_ts': self.last_trade_ts,
        }

        return features