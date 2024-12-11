class StrategyAnalyzer:
    def __init__(self, config):
        self.config = config

    def analyze(self, df):
        # 简单的策略示例：检查价格是否高于20日均线
        df['MA20'] = df['close'].rolling(window=20).mean()
        if df['close'].iloc[-1] > df['MA20'].iloc[-1]:
            return ["看涨信号"]
        else:
            return ["看跌信号"] 