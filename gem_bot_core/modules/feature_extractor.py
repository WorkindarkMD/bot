import numpy as np
from collections import deque
import time

class FeatureExtractor:
    """
    Extracts microstructural features from real-time market data.
    This class is stateful, maintaining the current state of the order book
    and recent trades.
    """
    def __init__(self, max_trades=100):
        """
        Initializes the FeatureExtractor.
        :param max_trades: The number of recent trades to store and analyze.
        """
        self.order_book = {'bids': {}, 'asks': {}}
        self.last_update_ts = None
        self.trades = deque(maxlen=max_trades)
        self.last_trade_ts = None

    def update_order_book(self, data):
        """
        Updates the order book state from connector data.
        Handles both 'snapshot' and 'update' actions.
        """
        action = data.get('action')
        if not action or 'data' not in data or not data['data']:
            return

        book_data = data['data'][0]

        if action == 'snapshot':
            self.order_book['bids'] = {float(price): float(size) for price, size in book_data.get('bids', [])}
            self.order_book['asks'] = {float(price): float(size) for price, size in book_data.get('asks', [])}
        elif action == 'update':
            for side in ['bids', 'asks']:
                for price, size in book_data.get(side, []):
                    price, size = float(price), float(size)
                    if size == 0:
                        if price in self.order_book[side]:
                            del self.order_book[side][price]
                    else:
                        self.order_book[side][price] = size

        self.last_update_ts = int(book_data.get('ts'))

    def add_trade(self, data):
        """
        Adds new trades to the queue for analysis.
        """
        trade_list = data.get('data', [])
        if not trade_list:
            return

        for trade in trade_list:
            # trade format: [timestamp, price, size, side]
            self.trades.append({
                'ts': int(trade[0]),
                'price': float(trade[1]),
                'size': float(trade[2]),
                'side': trade[3]
            })
        self.last_trade_ts = int(trade_list[-1][0])

    def extract_features(self):
        """
        Extracts and calculates a set of microstructural features from the current state.
        :return: A dictionary of features, or None if data is insufficient.
        """
        if not self.order_book['bids'] or not self.order_book['asks']:
            return None

        sorted_bids = sorted(self.order_book['bids'].items(), key=lambda x: x[0], reverse=True)
        sorted_asks = sorted(self.order_book['asks'].items(), key=lambda x: x[0])

        if not sorted_bids or not sorted_asks:
            return None

        best_bid_price, best_bid_size = sorted_bids[0]
        best_ask_price, best_ask_size = sorted_asks[0]

        # 1. Bid-Ask Spread
        spread = best_ask_price - best_bid_price

        # 2. Mid-Price
        mid_price = (best_ask_price + best_bid_price) / 2

        # 3. Weighted Average Price (WAP)
        wap = (best_bid_price * best_ask_size + best_ask_price * best_bid_size) / (best_bid_size + best_ask_size) if (best_bid_size + best_ask_size) > 0 else mid_price

        # 4. Book Imbalance (5 levels)
        bid_depth = sum(size for _, size in sorted_bids[:5])
        ask_depth = sum(size for _, size in sorted_asks[:5])
        book_imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0

        # 5. Trade Imbalance
        buy_volume = sum(t['size'] for t in self.trades if t['side'] == 'buy')
        sell_volume = sum(t['size'] for t in self.trades if t['side'] == 'sell')
        total_trade_volume = buy_volume + sell_volume
        trade_imbalance = (buy_volume - sell_volume) / total_trade_volume if total_trade_volume > 0 else 0

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