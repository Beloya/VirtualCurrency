import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from .pattern_analyzer import PatternAnalyzer

class TechnicalAnalyzer:
    def __init__(self):
        self.pattern_analyzer = PatternAnalyzer()

    def calculate_bollinger_bands(self, prices, window=20, num_std_dev=2):
        """计算布林带"""
        try:
            if len(prices) < window:
                return None, None, None
                
            # 使用numpy计算移动平均和标准差
            ma = np.array([np.mean(prices[max(0, i-window+1):i+1]) 
                          for i in range(window-1, len(prices))])
            std = np.array([np.std(prices[max(0, i-window+1):i+1]) 
                           for i in range(window-1, len(prices))])
            
            upper_band = ma + (std * num_std_dev)
            lower_band = ma - (std * num_std_dev)
            
            # 填充前面的值
            padding = np.array([np.nan] * (window-1))
            ma = np.concatenate([padding, ma])
            upper_band = np.concatenate([padding, upper_band])
            lower_band = np.concatenate([padding, lower_band])
            
            return ma, upper_band, lower_band
            
        except Exception as e:
            print(f"计算布林带错误: {str(e)}")
            return None, None, None
    
    def calculate_dynamic_bollinger_bands(self, prices):
        """根据市场波动性动态调整布林带窗口"""
        volatility = np.std(prices[-20:])  # 计算最近20个价格的标准差作为波动性
        window = 10 if volatility > 0.02 else 20  # 动态调整窗口
        return self.calculate_bollinger_bands(prices, window=window)
        
    def calculate_rsi(self, prices, period=14):
        """
        计算RSI指标，返回一个包含所有RSI值的数组
        """
        try:
            if len(prices) < period + 1:
                return None
                
            # 计算价格变化
            deltas = np.diff(prices)
            
            # 创建存储RSI值的数组
            rsi_values = np.zeros(len(prices))
            rsi_values[:period] = np.nan  # 前period个值设为NaN
            
            # 初始化第一个RSI值
            gains = np.zeros(period)
            losses = np.zeros(period)
            for i in range(period):
                if deltas[i] >= 0:
                    gains[i] = deltas[i]
                else:
                    losses[i] = -deltas[i]
                    
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            
            if avg_loss == 0:
                rsi_values[period] = 100
            else:
                rs = avg_gain / avg_loss
                rsi_values[period] = 100 - (100 / (1 + rs))
                
            # 计算剩余的RSI值
            for i in range(period + 1, len(prices)):
                delta = deltas[i-1]
                
                if delta >= 0:
                    avg_gain = (avg_gain * (period - 1) + delta) / period
                    avg_loss = (avg_loss * (period - 1)) / period
                else:
                    avg_gain = (avg_gain * (period - 1)) / period
                    avg_loss = (avg_loss * (period - 1) - delta) / period
                    
                if avg_loss == 0:
                    rsi_values[i] = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi_values[i] = 100 - (100 / (1 + rs))
            
            return rsi_values
            
        except Exception as e:
            print(f"计算RSI错误: {str(e)}")
            return None
    
    def calculate_dynamic_rsi(self, prices, base_period=14):
        """根据市场波动性动态调整RSI阈值"""
        volatility = np.std(prices[-20:])  # 计算最近20个价格的标准差作为波动性
        overbought_threshold = 80 if volatility > 0.02 else 70
        oversold_threshold = 20 if volatility > 0.02 else 30
        
        rsi = self.calculate_rsi(prices, period=base_period)
        
        return rsi, overbought_threshold, oversold_threshold
        
    def calculate_macd(self, prices, fastperiod=12, slowperiod=26, signalperiod=9):
        """计算MACD指标"""
        exp1 = pd.Series(prices).ewm(span=fastperiod, adjust=False).mean()
        exp2 = pd.Series(prices).ewm(span=slowperiod, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=signalperiod, adjust=False).mean()
        hist = macd - signal
        return macd.values, signal.values, hist.values
        
    def calculate_obv(self, prices, volumes):
        """计算OBV指标"""
        obv = np.zeros_like(prices)
        obv[0] = volumes[0]
        for i in range(1, len(prices)):
            if prices[i] > prices[i - 1]:
                obv[i] = obv[i - 1] + volumes[i]
            elif prices[i] < prices[i - 1]:
                obv[i] = obv[i - 1] - volumes[i]
            else:
                obv[i] = obv[i - 1]
        return obv[-1]
        
    def check_indicators(self, df):
        """检查技术指标信号"""
        try:
            closes = df['close'].values
            volumes = df['volume'].values
            
            # 动态计算布林带
            ma, upper_band, lower_band = self.calculate_dynamic_bollinger_bands(closes)
            
            # 动态计算RSI
            rsi, overbought_threshold, oversold_threshold = self.calculate_dynamic_rsi(closes)
            
            # 计算OBV
            obv = self.calculate_obv(closes, volumes)
            trigger_signals=[]
            
            # 检查布林带突破[
            if closes[-1] > upper_band[-1]:
                trigger_signals.append('价格突破布林带上轨，可能回调')
            elif closes[-1] < lower_band[-1]:
                trigger_signals.append('价格跌破布林带下轨，可能反弹')
            
            # 检查RSI超买超卖
            if rsi[-1] > overbought_threshold:
                trigger_signals.append(f'RSI超买（>{overbought_threshold}），可能回调')
            elif rsi[-1] < oversold_threshold:
                trigger_signals.append(f'RSI超卖（<{oversold_threshold}），可能反弹')
            
            # 检查OBV趋势
            if obv > 0:
                trigger_signals.append('OBV上升，可能看涨')
            elif obv < 0:
                trigger_signals.append('OBV下降，可能看跌')
            
            # 检查蜡烛图形态
            # self.pattern_analyzer.check_candlestick_patterns(df)
            return trigger_signals

        except Exception as e:
            print(f"技术指标检查错误: {str(e)}")
            return []

    def calculate_indicators(self, df):
        # 计算MA
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        
        # 计算布林带
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['std'] = df['close'].rolling(window=20).std()
        df['upper'] = df['MA20'] + (df['std'] * 2)
        df['lower'] = df['MA20'] - (df['std'] * 2)
        
        # 计算RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 计算MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']
        
        return df

    def calculate_support_resistance(self, df):
        """计算支撑位和压力位"""
        # 使用过去N个周期的数据
        window = 20
        recent_df = df.tail(window)
        
        # 计算价格密集区
        price_clusters = []
        for price in recent_df['low']:
            # 查找价格聚集区域
            cluster = recent_df[(recent_df['low'] >= price*0.995) & 
                              (recent_df['low'] <= price*1.005)]
        if len(cluster) >= 3:  # 至少3次触及该价格区域
            price_clusters.append(price)
        
        # 计算支撑位
        supports = []
        for price in price_clusters:
            # 价格在此之上的比例
            above_ratio = len(recent_df[recent_df['close'] > price]) / len(recent_df)
            if above_ratio > 0.7:  # 70%的价格在此之上
                supports.append(price)
    
        # 计算压力位
        resistances = []
        for price in price_clusters:
            # 价格在此之下的比例
            below_ratio = len(recent_df[recent_df['close'] < price]) / len(recent_df)
            if below_ratio > 0.7:  # 70%的价格在此之下
                resistances.append(price)
    
        
        # 返回最强支撑位和压力位
        support_price = max(supports) if supports else None
        resistance_price = min(resistances) if resistances else None
        
        return support_price, resistance_price
    
    # 检查各种信号
    def check_technical_signals(self, df, ma_cross_alert, bollinger_alert, price_alert, volume_alert, trend_alert, momentum_alert, macd_cross_alert,monitor_minutes=10,price_threshold=1):
        """检查各种信号"""
        try:
            trigger_signals=[]
            # 检查金叉死叉
            if ma_cross_alert:
                if df['MA5'].iloc[-2] <= df['MA10'].iloc[-2] and df['MA5'].iloc[-1] > df['MA10'].iloc[-1]:
                    trigger_signals.append('金叉')
                elif df['MA5'].iloc[-2] >= df['MA10'].iloc[-2] and df['MA5'].iloc[-1] < df['MA10'].iloc[-1]:
                    trigger_signals.append('死叉')
            
            # 检查布林带突破
            if bollinger_alert:
                if df['close'].iloc[-1] > df['upper'].iloc[-1]:
                    trigger_signals.append('突破布林上轨')
                elif df['close'].iloc[-1] < df['lower'].iloc[-1]:
                    trigger_signals.append('突破布林下轨')
            
            # 检查价格变动
            if price_alert:
                monitor_minutes = int(monitor_minutes)
                threshold = float(price_threshold)
                
                minutes_ago = df.index[-1] - timedelta(minutes=monitor_minutes)
                old_price = df.loc[df.index >= minutes_ago].iloc[0]['close']
                current_price = df['close'].iloc[-1]
                
                # 价格变动百分
                price_change = ((current_price - old_price) / old_price) * 100
                
                if abs(price_change) >= threshold:
                    direction = "上涨" if price_change > 0 else "下跌"
                    trigger_signals.append(f'价格变动{direction}')
            
            # 检查成交量异常
            if volume_alert:
                # 计算成交量的移动平均
                volume_ma = df['volume'].rolling(window=20).mean()
                current_volume = df['volume'].iloc[-1]
                
                # 如果当前成交量超平均的2倍
                if current_volume > volume_ma.iloc[-1] * 2:
                    trigger_signals.append('成交量异常放量')
            
            # 检查趋势突破
            if trend_alert:
                # 使用20日均线作为趋势线
                ma20 = df['close'].rolling(window=20).mean()
                price = df['close'].iloc[-1]
                prev_price = df['close'].iloc[-2]
                
                if prev_price <= ma20.iloc[-2] and price > ma20.iloc[-1]:
                    trigger_signals.append('向上突破20日均线')
                elif prev_price >= ma20.iloc[-2] and price < ma20.iloc[-1]:
                    trigger_signals.append('向下突破20日均线')
            
            # 检查动量背离
            if momentum_alert:
                # 价格创新高但RSI未创新高，可能现顶背离
                if (df['close'].iloc[-1] > df['close'].iloc[-2:-6].max() and 
                    df['RSI'].iloc[-1] < df['RSI'].iloc[-2:-6].max()):
                    trigger_signals.append('可能出现顶背离')
                
                # 价格创新低但RSI未创新低，可能出现底背离
                if (df['close'].iloc[-1] < df['close'].iloc[-2:-6].min() and 
                    df['RSI'].iloc[-1] > df['RSI'].iloc[-2:-6].min()):
                    trigger_signals.append('可能出现底背离')
            
            # 检查MACD交叉
            if macd_cross_alert:
                # MACD金叉
                if (df['MACD'].iloc[-2] <= df['Signal'].iloc[-2] and 
                    df['MACD'].iloc[-1] > df['Signal'].iloc[-1]):
                    trigger_signals.append('MACD金叉')
                
                # MACD死叉
                elif (df['MACD'].iloc[-2] >= df['Signal'].iloc[-2] and 
                      df['MACD'].iloc[-1] < df['Signal'].iloc[-1]):
                    trigger_signals.append('MACD死叉')
            
            trigger_signals.extend(self.check_indicators(df))
            return trigger_signals
            
        except Exception as e:
            print(f"策略检查错误: {str(e)}")
        