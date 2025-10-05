class PredictionSimulator:
    """
    Simulates an AI/ML model for generating trading signals.
    In this simulation, simple, deterministic logic based on order book
    imbalance is used.
    """
    def __init__(self, imbalance_threshold=0.2):
        """
        Initializes the simulator.
        :param imbalance_threshold: The threshold for making a buy/sell decision.
        """
        self.imbalance_threshold = imbalance_threshold

    def get_prediction(self, features):
        """
        Generates a trading signal based on the provided features.
        :param features: A dictionary of microstructural features from FeatureExtractor.
        :return: A string with the trading signal ('BUY', 'SELL', 'HOLD').
        """
        if features is None:
            return 'HOLD'

        book_imbalance = features.get('book_imbalance_5_levels')

        if book_imbalance is None:
            return 'HOLD'

        if book_imbalance > self.imbalance_threshold:
            # If demand (bids) significantly exceeds supply (asks),
            # we expect the price to rise.
            return 'BUY'
        elif book_imbalance < -self.imbalance_threshold:
            # If supply (asks) significantly exceeds demand (bids),
            # we expect the price to fall.
            return 'SELL'
        else:
            # If the imbalance is insignificant, take no action.
            return 'HOLD'