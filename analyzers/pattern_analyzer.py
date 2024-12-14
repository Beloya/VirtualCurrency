import time
from scipy.signal import argrelextrema
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression


class PatternAnalyzer:
    def is_head_and_shoulders_top(self,df, threshold=0.02, min_distance=5):
        """头肩顶形态检测"""
        """改进的头肩顶形态检测"""
        max_points, _ = find_extrema(df)
        if len(max_points) < 3:
            return False, None

        left_shoulder, head, right_shoulder = max_points.iloc[-3], max_points.iloc[-2], max_points.iloc[-1]
        shoulder_diff = abs(left_shoulder['close'] - right_shoulder['close'])
        
        # 确保头部比肩膀高出一定比例
        if head['close'] > left_shoulder['close'] * (1 + threshold) and \
           head['close'] > right_shoulder['close'] * (1 + threshold) and \
           shoulder_diff / left_shoulder['close'] < threshold:
            
            # 使用线性回归拟合颈线
            lows_between = df['close'].iloc[left_shoulder.name:right_shoulder.name]
            slope, intercept = fit_line(lows_between)
            neckline = slope * np.arange(len(lows_between)) + intercept
            
            # 检查是否突破颈线
            breakout = any(df['close'].iloc[right_shoulder.name:] < neckline)
            
            # 确认突破后价格行为
            if breakout and df['close'].iloc[right_shoulder.name:right_shoulder.name+5].mean() < neckline:
                return True, neckline
        return False, None
        
    def is_double_top(self, df, threshold=0.02, min_distance=5, max_distance=30):
        """双顶形态检测"""
        max_points, _ = find_extrema(df)
        if len(max_points) < 2:
            return False, None

        first_top, second_top = max_points.iloc[-2], max_points.iloc[-1]
        # 检查两个顶部是否大致相等
        tops_diff = abs(second_top['close'] - first_top['close'])
        if tops_diff / first_top['close'] > threshold:
            return False, None
            
        # 检查两个顶部之间的距离 (使用索引差值而不是日期差值)
        index_diff = max_points.index.get_loc(second_top.name) - max_points.index.get_loc(first_top.name)
        if index_diff < min_distance:
            return False, None
            
        # 计算颈线
        lows_between = df.loc[first_top.name:second_top.name, 'close']
        neckline = lows_between.min()
        
        # 检查是否突破颈线
        breakout = any(df.loc[second_top.name:, 'close'] < neckline)
        
        return breakout, neckline

        
    def check_patterns(self, df):
        """检查经典技术形态"""
        try:
            # 获取最近的价格数据
            prices = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            
            # 存储检测到的形态
            patterns = []
            
            # 头肩顶形态判断
            if (result:=self.is_head_and_shoulders_top(df))[0]:
                patterns.append(f'头肩顶：bearish, 颈线: {result[1]}')
            
            # 头肩底形态判断
            elif (result:=self.is_head_and_shoulders_bottom(df))[0]:
                patterns.append(f'头肩底：bullish, 颈线: {result[1]}')
            
            # 双顶形态判断
            elif (result:=self.is_double_top(df))[0]:
                patterns.append(f'双顶：bearish, 颈线: {result[1]}')
            
            # 双底形态判断
            elif (result:=self.is_double_bottom(df))[0] :
                patterns.append(f'双底：bullish, 颈线: {result[1]}')

            patterns.extend(self.check_candlestick_patterns(df))
            
            # 三角形形态判断（只在没有发现其他形态时检查）
            if not patterns:
                if (result:=self.is_ascending_triangle(df))[0]:
                    resistance, (support_slope, support_intercept) = result
                    support_prices = support_slope * np.arange(len(df)) + support_intercept
                    patterns.append(f'上升三角形：bullish, 阻力线: {resistance}，支撑线: {support_prices}')
                elif (result:=self.is_descending_triangle(df))[0]:
                    support, (resistance_slope, resistance_intercept) = result
                    resistance_prices = resistance_slope * np.arange(len(df)) + resistance_intercept
                    patterns.append(f'下降三角形：bearish, 支撑线: {support}，阻力线: {resistance_prices}')
                elif (result:=self.detect_symmetrical_triangle(df))[0]:
                    patterns.append(f'对称三角形：bullish, 阻力线: {result[1]}，支撑线: {result[2]}')
            # print(patterns)
            return patterns
        except Exception as e:
            print(f"形态检查错误: {str(e)}")


    # 检测对称三角形
    def detect_symmetrical_triangle(self,df):
        # 使用 find_extrema 函数获取高点和低点
        max_points, min_points = find_extrema(df)
        highs = max_points.dropna(subset=['close'])
        lows = min_points.dropna(subset=['close'])

        # 至少需要两个高点和两个低点
        if len(highs) < 2 or len(lows) < 2:
            return False, None, None

        # 确保索引是数值型
        high_indices = np.arange(len(highs))
        low_indices = np.arange(len(lows))

        # 拟合高点和低点的趋势线
        high_trend = np.polyfit(high_indices, highs['close'].values, 1)
        low_trend = np.polyfit(low_indices, lows['close'].values, 1)

        # 检查收敛
        recent_data = df.tail(10)
        recent_indices = np.arange(len(recent_data))
        high_line = high_trend[0] * recent_indices + high_trend[1]
        low_line = low_trend[0] * recent_indices + low_trend[1]
        is_converging = (recent_data['high'].values <= high_line).all() and (recent_data['low'].values >= low_line).all()

        if is_converging:
            return True, high_trend, low_trend
        return False, None, None


    def is_head_and_shoulders_bottom(self, df, threshold=0.02):
        """头肩底形态检测"""
        _, min_points = find_extrema(df)
        if len(min_points) < 3:
            return False, None

        left_shoulder, head, right_shoulder = min_points.iloc[-3], min_points.iloc[-2], min_points.iloc[-1]
        shoulder_diff = abs(left_shoulder['close'] - right_shoulder['close'])
        if head['close'] < left_shoulder['close'] and head['close'] < right_shoulder['close'] and \
                shoulder_diff / left_shoulder['close'] < threshold:
            lows_between = df['close'].iloc[left_shoulder.name:right_shoulder.name]
            neckline = lows_between.max()
            breakout = any(df['close'].iloc[right_shoulder.name:] > neckline)
            return breakout, neckline
        return False, None

    def is_double_bottom(self, df, tolerance=0.02, min_distance=5, max_distance=30):
        """
        检测双底形态
        """
        _, min_points = find_extrema(df)
        if len(min_points) < 2:
            return False, None

        first_bottom, second_bottom = min_points.iloc[-2], min_points.iloc[-1]
        
        # 检查两个底部的价格差异是否在容忍范围内
        if abs(second_bottom['close'] - first_bottom['close']) / first_bottom['close'] > tolerance:
            return False, None

        # 检查两个底部之间的时间跨度
        index_diff = second_bottom.name - first_bottom.name
        if index_diff < min_distance or index_diff > max_distance:
            return False, None

        # 计算颈线
        highs_between = df['close'].iloc[first_bottom.name:second_bottom.name]
        neckline = highs_between.max()

        # 检查是否突破颈线
        breakout = any(df['close'].iloc[second_bottom.name:] > neckline)

        # 确认突破后价格行为
        if breakout and df['close'].iloc[second_bottom.name:second_bottom.name+5].mean() > neckline:
            return True, neckline

        return False, None

    def is_ascending_triangle(self, df, threshold=0.02):
        """
        检测上升三角形形态
        """
        max_points, min_points = find_extrema(df)
        if len(max_points) < 2 or len(min_points) < 2:
            return False, None, None

        resistance = max_points['close'].mean()
        slope, intercept = fit_line(min_points['close'])
        recent_prices = df['close'].tail(10)
        support_line = [slope * i + intercept for i in range(len(recent_prices))]
        is_converging = all([recent_prices.iloc[i] >= support_line[i] and recent_prices.iloc[i] <= resistance
                             for i in range(len(recent_prices))])
        return is_converging, resistance, (slope, intercept)

    def is_descending_triangle(self, df, threshold=0.02):
        """
        检测下降三角形形态
        """
        max_points, min_points = find_extrema(df)
        if len(max_points) < 2 or len(min_points) < 2:
            return False, None, None

        support = min_points['close'].mean()
        slope, intercept = fit_line(max_points['close'])
        recent_prices = df['close'].tail(10)
        resistance_line = [slope * i + intercept for i in range(len(recent_prices))]
        is_converging = all([recent_prices.iloc[i] >= support and recent_prices.iloc[i] <= resistance_line[i]
                             for i in range(len(recent_prices))])
        return is_converging, support, (slope, intercept)   
    
    def is_hammer(self, opens, closes, highs, lows, threshold=0.3):
        """检测锤子线形态"""
        if len(opens) < 2:
            return False
        
        # 检查最后一个蜡烛
        body = abs(closes[-1] - opens[-1])
        lower_shadow = opens[-1] - lows[-1] if closes[-1] > opens[-1] else closes[-1] - lows[-1]
        upper_shadow = highs[-1] - closes[-1] if closes[-1] > opens[-1] else highs[-1] - opens[-1]
        
        # 锤子线条件
        if lower_shadow > 2 * body and upper_shadow < body * threshold:
            return True
        
        return False

    def is_engulfing(self, opens, closes):
        """检测吞没形态"""
        if len(opens) < 2:
            return False
        
        # 检查最后两个蜡烛
        prev_body = abs(closes[-2] - opens[-2])
        curr_body = abs(closes[-1] - opens[-1])
        
        # 看涨吞没
        if closes[-1] > opens[-1] and opens[-1] < closes[-2] and closes[-1] > opens[-2]:
            return True
        
        # 看跌吞没
        if closes[-1] < opens[-1] and opens[-1] > closes[-2] and closes[-1] < opens[-2]:
            return True
        
        return False
    
    def check_candlestick_patterns(self, df):
        """检查蜡烛图形态"""
        try:
            trigger_signals=[]

            opens = df['open'].values
            closes = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            
            # 检查锤子线
            if self.is_hammer(opens, closes, highs, lows):
                trigger_signals.append('检测到锤子线，可能反转')
            
            # 检查吞没形态
            if self.is_engulfing(opens, closes):
                trigger_signals.append('检测到吞没形态，可能反转')
            return trigger_signals
        except Exception as e:
            print(f"蜡烛图形态检查错误: {str(e)}")
            return []

    def analyze_patterns(self, df):
        """分析单一时间框架的形态"""
        patterns = []
        highs = df['high'].values
        lows = df['low'].values
        
        # 检查各种形态
        if (result:=self.is_head_and_shoulders_top(df))[0]:
            patterns.append(f'头肩顶, 颈线: {result[1]}')
        elif (result:=self.is_head_and_shoulders_bottom(df))[0]:
            patterns.append(f'头肩底, 颈线: {result[1]}')
        elif (result:=self.is_double_top(df))[0]:
            patterns.append(f'双顶, 颈线: {result[1]}')
        elif ( result := self.is_double_bottom(df))[0]:
            patterns.append(f'双底, 颈线: {result[1]}')
        
        return patterns

# 1. 通用的局部极值查找函数
def find_extrema(df, column='close', order=5):
    """
    查找局部极值（高点和低点）
    """
     # 检查输入数据的完整性
    if column not in df.columns:
        raise ValueError(f"DataFrame中缺少必要的列: {column}")

    # 确保数据不为空
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    values = df[column].values

    # 查找局部极大值和极小值
    max_indices = argrelextrema(values, np.greater_equal, order=order)[0]
    min_indices = argrelextrema(values, np.less_equal, order=order)[0]

    # 返回包含时间戳和指定列的DataFrame
    # 使用索引来获取时间戳
    max_points = pd.DataFrame({'timestamp': df.index[max_indices], column: df.iloc[max_indices][column].values})
    min_points = pd.DataFrame({'timestamp': df.index[min_indices], column: df.iloc[min_indices][column].values})

    return max_points, min_points

# 平滑价格曲线： 平滑价格减少噪声干扰
def smooth_prices(df, column='close', window=5):
    """
    使用滚动平均平滑价格数据
    """
    df['smoothed'] = df[column].rolling(window=window).mean()
    return df

# 拟合线性趋势（用于颈线或趋势线）
def fit_line(points):
    """
    使用线性回归拟合一条直线
    """
    X = np.array(range(len(points))).reshape(-1, 1)
    y = points.values
    reg = LinearRegression().fit(X, y)
    return reg.coef_[0], reg.intercept_





pattern="""常见形态列表
        反转形态
          双顶形态（Double Top）：
            与双底相反，两个高点接近相同，价格跌破颈线后通常确认反转。
          头肩顶（Head and Shoulders）：
            三个高点，中间高点（头部）最高，两边的高点（肩膀）较低，价格跌破颈线确认反转。
          头肩底（Inverse Head and Shoulders）：
            与头肩顶相反，三个低点，中间低点最低，价格突破颈线确认反转。
        持续形态
            对称三角形（Symmetrical Triangle）：
                高点逐步降低，低点逐步抬高，形成对称收敛，突破方向可能不确定。
            矩形整理形态（Rectangle Consolidation）：
                高点和低点形成水平区间，价格在区间内震荡。
            旗形和三角旗形（Flag and Pennant）：
                快速上涨或下跌后的短暂整理，通常突破原趋势方向。"""