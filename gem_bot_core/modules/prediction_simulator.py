class PredictionSimulator:
    """
    Имитирует AI/ML модель для генерации торговых сигналов.
    В этой симуляции используется простая, детерминированная логика,
    основанная на дисбалансе книги заявок.
    """
    def __init__(self, imbalance_threshold=0.2):
        """
        Инициализация симулятора.
        :param imbalance_threshold: Порог для принятия решения о покупке/продаже.
        """
        self.imbalance_threshold = imbalance_threshold

    def get_prediction(self, features):
        """
        Генерирует торговый сигнал на основе предоставленных признаков.
        :param features: Словарь с микроструктурными признаками от FeatureExtractor.
        :return: Строка с торговым сигналом ('BUY', 'SELL', 'HOLD').
        """
        if features is None:
            return 'HOLD'

        book_imbalance = features.get('book_imbalance_5_levels')

        if book_imbalance is None:
            return 'HOLD'

        if book_imbalance > self.imbalance_threshold:
            # Если спрос (биды) значительно превышает предложение (аски),
            # ожидаем рост цены.
            return 'BUY'
        elif book_imbalance < -self.imbalance_threshold:
            # Если предложение (аски) значительно превышает спрос (биды),
            # ожидаем падение цены.
            return 'SELL'
        else:
            # Если дисбаланс незначителен, не предпринимаем действий.
            return 'HOLD'