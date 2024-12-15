import numpy as np
import time
from .pattern_analyzer import PatternAnalyzer
from .technical_analyzer import TechnicalAnalyzer

class MultiTimeframeAnalyzer:
    def __init__(self, data_fetcher):
        self.data_fetcher = data_fetcher
        self.technical_analyzer = TechnicalAnalyzer()
        self.pattern_analyzer = PatternAnalyzer()
        
    def analyze_trend(self, df):
        """分析单一时间框架的趋势"""
        try:
            closes = df['close'].values
            
            # 计算多个指标
            # 1. 移动平均线趋势
            ma20 = np.mean(closes[-20:])
            ma50 = np.mean(closes[-50:])
            current_price = closes[-1]
            
            # 2. 计算RSI
            rsi = self.technical_analyzer.calculate_rsi(closes)[-1]
            
            # 3. 计算MACD
            macd, signal, hist = self.technical_analyzer.calculate_macd(closes)
            
            # 综合判断趋势
            trend = {
                'direction': 'neutral',
                'strength': 0,
                'price_vs_ma': 'neutral',
                'rsi_status': 'neutral',
                'macd_status': 'neutral'
            }
            
            # 价格与均线关系
            if current_price > ma20 > ma50:
                trend['direction'] = 'bullish'
                trend['price_vs_ma'] = 'bullish'
                trend['strength'] += 1
            elif current_price < ma20 < ma50:
                trend['direction'] = 'bearish'
                trend['price_vs_ma'] = 'bearish'
                trend['strength'] += 1
            
            # RSI状态
            if rsi > 70:
                trend['rsi_status'] = 'overbought'
                if trend['direction'] == 'bearish':
                    trend['strength'] += 1
            elif rsi < 30:
                trend['rsi_status'] = 'oversold'
                if trend['direction'] == 'bullish':
                    trend['strength'] += 1
            
            # MACD状态
            if hist[-1] > 0 and hist[-1] > hist[-2]:
                trend['macd_status'] = 'bullish'
                if trend['direction'] == 'bullish':
                    trend['strength'] += 1
            elif hist[-1] < 0 and hist[-1] < hist[-2]:
                trend['macd_status'] = 'bearish'
                if trend['direction'] == 'bearish':
                    trend['strength'] += 1
            
            return trend
        
        except Exception as e:
            print(f"趋势分析错误: {str(e)}")
            return None
        

    def analyze_multiple_timeframes(self, symbol):
        """多时间框架分析"""
        try:
            # print("多时间框架分析")
            # 定义时间框架组合
            timeframe_groups = [
                ['1m', '5m', '15m'],  # 短期
                ['15m', '1h', '4h'],  # 中期
                ['4h', '1d', '1w']    # 长期
            ]
            
            # 存储各时间框架的趋势
            trends = {}
            patterns = {}
            
            # 分析每个时间框架
            for timeframes in timeframe_groups:
                group_trends = []
                group_patterns = []
                
                for tf in timeframes:
                    # 获取对应时间框架的数据
                    df = self.data_fetcher.fetch_ohlcv_data(symbol, tf)
                    if df is None or len(df) < 50:
                        continue
                    
                    # 分析趋势
                    trend = self.analyze_trend(df)
                    group_trends.append((tf, trend))
                    
                    # 分析形态
                    _,pattern = self.pattern_analyzer.check_patterns(df)
                    if pattern:
                        group_patterns.append((tf, pattern))
                
                trends[f"{timeframes[0]}-{timeframes[-1]}"] = group_trends
                patterns[f"{timeframes[0]}-{timeframes[-1]}"] = group_patterns
            
            return self.generate_multi_timeframe_signals(trends, patterns)
        
        except Exception as e:
            print(f"多时间框架分析错误: {str(e)}")
            import traceback
            traceback.print_exc()

            return []



    def generate_multi_timeframe_signals(self, trends, patterns):
        """生成多时间框架信号"""
        signals = []
        current_time = time.time()
        
        for timeframe_group, group_trends in trends.items():
            # 检查趋势一致性
            trend_directions = [t[1]['direction'] for t in group_trends if t[1]]
            trend_strengths = [t[1]['strength'] for t in group_trends if t[1]]
            
            if len(trend_directions) >= 2:  # 至少需要两个时间框架的数据
                # 检查趋势是否一致
                if all(d == 'bullish' for d in trend_directions):
                    avg_strength = sum(trend_strengths) / len(trend_strengths)
                    signal = f"{timeframe_group}时间框架趋势一致看涨 (强度: {avg_strength:.1f})"
                    signals.append((signal, current_time))
                
                elif all(d == 'bearish' for d in trend_directions):
                    avg_strength = sum(trend_strengths) / len(trend_strengths)
                    signal = f"{timeframe_group}时间框架趋势一致看跌 (强度: {avg_strength:.1f})"
                    signals.append((signal, current_time))
                elif all(d == 'neutral' for d in trend_directions):
                    avg_strength = sum(trend_strengths) / len(trend_strengths)
                    signal = f"{timeframe_group}时间框架趋势中性 (强度: {avg_strength:.1f})"
                    signals.append((signal, current_time))
            
            # 检查形态确认
            group_patterns = patterns[timeframe_group]
            if group_patterns:
                patterns_list = [p for tf, plist in group_patterns for p in plist]
                pattern_directions = [p[1] for p in patterns_list]
                if len(pattern_directions) >= 2:
                    if all(d == 'bullish' for d in pattern_directions):
                        signal = f"{timeframe_group}时间框架形态确认看涨:{patterns_list}"
                        signals.append((signal, current_time))
                    elif all(d == 'bearish' for d in pattern_directions):
                        signal = f"{timeframe_group}时间框架形态确认看跌:{patterns_list}"
                        signals.append((signal, current_time))
        
        return signals


    def predict_best_entry_exit_multi_timeframe(self, symbol):
        """
        多时间维度预测最佳交易点位
        结合短期、中期、长期走势分析
        """
        try:
            # 定义时间框架组合
            timeframes = {
                'short': ['1m', '5m', '15m'],     # 短期
                'medium': ['30m', '1h', '4h'],    # 中期
                'long': ['4h', '1d', '1w']        # 长期
            }
            
            # 存储各时间维度的分析结果
            timeframe_analysis = {
                'short': {'score': 0, 'signals': [], 'patterns': []},
                'medium': {'score': 0, 'signals': [], 'patterns': []},
                'long': {'score': 0, 'signals': [], 'patterns': []}
            }
            
            # 对每个时间维度进行分析
            for period, tf_list in timeframes.items():
                for tf in tf_list:
                    # 获取对应时间框架的数据
                    df = self.data_fetcher.fetch_ohlcv_data(symbol, tf)
                    if df is None or len(df) < 50:
                        continue
                    
                    # 计算技术指标
                    closes = df['close'].values
                    volumes = df['volume'].values
                    current_price = closes[-1]
                    
                    # RSI
                    rsi = self.technical_analyzer.calculate_rsi(closes)
                    
                    # MACD
                    macd, signal, hist = self.technical_analyzer.calculate_macd(closes)
                    
                    # 布林带
                    ma, upper_band, lower_band = self.technical_analyzer.calculate_bollinger_bands(closes)
                    
                    # 成交量分析
                    volume_ma = np.mean(volumes[-20:])
                    current_volume = volumes[-1]
                    
                    # 趋势分析
                    trend_score = 0
                    if closes[-1] > ma[-1]:
                        trend_score += 1
                    if macd[-1] > signal[-1]:
                        trend_score += 1
                    if closes[-1] > upper_band[-1]:
                        trend_score -= 1  # 超买区域
                    elif closes[-1] < lower_band[-1]:
                        trend_score += 1  # 超卖区域
                    
                    # 动量分析
                    momentum_score = 0
                    if 30 <= rsi[-1] <= 70:
                        momentum_score += 1
                    elif rsi[-1] < 30:
                        momentum_score += 2  # 超卖
                    elif rsi[-1] > 70:
                        momentum_score -= 2  # 超买
                    if len(hist) > 1:  # 确保有足够的数据
                        if hist[-1] > 0 and hist[-1] > hist[-2]:
                            momentum_score += 1  # MACD柱状图上升
                        elif hist[-1] < 0 and hist[-1] < hist[-2]:
                            momentum_score -= 1  # MACD柱状图下降
                    else:
                        print("MACD柱状图数据不足")
                
                    
                    # 成交量分析
                    volume_score = 0
                    if current_volume > volume_ma * 1.5:
                        volume_score += 1
                    
                    # 形态分析
                    patterns = []
                    if len(df) >= 100:  # 确保有足够的数据进行形态分析
                        if (result:=self.pattern_analyzer.is_head_and_shoulders_top(df))[0]:
                            timeframe_analysis[period]['patterns'].append(('头肩顶', -2))
                        if (result:=self.pattern_analyzer.is_head_and_shoulders_bottom(df))[0]:
                            timeframe_analysis[period]['patterns'].append(('头肩底', 2))
                        if (result:=self.pattern_analyzer.is_double_top(df))[0]:
                            timeframe_analysis[period]['patterns'].append(('双顶', -2))
                        if (result:=self.pattern_analyzer.is_double_bottom(df))[0]:
                            timeframe_analysis[period]['patterns'].append(('双底', 2))
                    else:
                        timeframe_analysis[period]['patterns'].append(('形态分析不足', 0))
                    
                    # 计算总分
                    pattern_score = sum(score for _, score in patterns)
                    total_score = trend_score + momentum_score + volume_score + pattern_score
                    
                    # 更新时间维度分析结果
                    timeframe_analysis[period]['score'] += total_score
                    timeframe_analysis[period]['signals'].append({
                        'timeframe': tf,
                        'rsi': rsi[-1],
                        'rsi_signal': 'overbought' if rsi[-1] > 70 else 'oversold' if rsi[-1] < 30 else 'neutral',
                        'macd_signal': 'bullish' if macd[-1] > signal[-1] else 'bearish',
                        'price_vs_ma': 'above' if closes[-1] > ma[-1] else 'below',
                        'volume_signal': 'high' if current_volume > volume_ma * 1.5 else 'normal',
                        'bollinger_position': 'above' if closes[-1] > upper_band[-1] else 'below' if closes[-1] < lower_band[-1] else 'inside'
                    })
                    
            if current_price is None:
                print("无法获取当前价格")
                return None
            # 综合分析结果
            # prediction = {
            #     'signal': '',
            #     'confidence': 0,
            #     'price_targets': {},
            #     'reasons': [],
            #     'risk_level': '',
            #     'timeframe_analysis': timeframe_analysis
            # }
            
            # 计算综合得分
            total_score = (
                timeframe_analysis['short']['score'] * 0.2 +  # 短期权重20%
                timeframe_analysis['medium']['score'] * 0.5 + # 中期权重50%
                timeframe_analysis['long']['score'] * 0.3     # 长期权重30%
            )

            # 生成预测结果
            prediction = {
                'signal': '',
                'confidence': min(abs(total_score) * 10, 100),  # 限制最大值为100
                'price_targets': {},
                'reasons': [],
                'risk_level': '',
                'timeframe_analysis': timeframe_analysis
            }
            
            # 获取当前价格
            current_price = self.data_fetcher.get_current_price(symbol)
            # print(total_score)
            # 根据综合得分生成信号
            if total_score > 8:
                prediction['signal'] = '强烈看多'
                prediction['price_targets'] = {
                    'entry': current_price,
                    'target': current_price * 1.03,  # 3%获利目标
                    'stop_loss': current_price * 0.99  # 1%止损位
                }
            elif total_score > 6:
                prediction['signal'] = '看多'
                prediction['price_targets'] = {
                    'entry': current_price,
                    'target': current_price * 1.02,
                    'stop_loss': current_price * 0.99
                }
            elif total_score < -2:
                prediction['signal'] = '强烈看空'
                prediction['price_targets'] = {
                    'entry': current_price,
                    'target': current_price * 0.97,
                    'stop_loss': current_price * 1.01
                }
            elif total_score < 1:
                prediction['signal'] = '看空'
                prediction['price_targets'] = {
                    'entry': current_price,
                    'target': current_price * 0.98,
                    'stop_loss': current_price * 1.01
                }
            else:
                prediction['signal'] = '观望'
                prediction['price_targets'] = {
                    'entry': current_price,
                    'target': current_price,
                    'stop_loss': current_price
                }
            
            # 设置信心水平
            prediction['confidence'] = min(abs(total_score) * 10, 100)
            
            # 生成分析理由
            for period, analysis in timeframe_analysis.items():
                period_name = {'short': '短期', 'medium': '中期', 'long': '长期'}[period]
                
                for signal in analysis['signals']:
                    # MACD信号
                    if signal['macd_signal'] == 'bullish':
                        prediction['reasons'].append(f"{period_name} {signal['timeframe']} MACD看多")
                    elif signal['macd_signal'] == 'bearish':
                        prediction['reasons'].append(f"{period_name} {signal['timeframe']} MACD看空")
                
                    # RSI信号
                    if signal['rsi_signal'] == 'overbought':
                        prediction['reasons'].append(f"{period_name} {signal['timeframe']} RSI超买({signal['rsi']:.1f})")
                    elif signal['rsi_signal'] == 'oversold':
                        prediction['reasons'].append(f"{period_name} {signal['timeframe']} RSI超卖({signal['rsi']:.1f})")
                
                    # 布林带信号
                    if signal['bollinger_position'] == 'above':
                        prediction['reasons'].append(f"{period_name} {signal['timeframe']} 价格突破布林带上轨")
                    elif signal['bollinger_position'] == 'below':
                        prediction['reasons'].append(f"{period_name} {signal['timeframe']} 价格跌破布林带下轨")
            
                    # 形态信号
                for pattern, _ in analysis['patterns']:
                    prediction['reasons'].append(f"{period_name}出现{pattern}形态")
        
            # 设置风险等级
            if prediction['confidence'] >= 80:
                prediction['risk_level'] = '低风险'
            elif prediction['confidence'] >= 50:
                prediction['risk_level'] = '中等风险'
            else:
                prediction['risk_level'] = '高风险'
        
            return prediction
    
            
        except Exception as e:
            print(f"多时间维度预测错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def analyze(self, symbol):
        """多时间框架分析"""
        # ... 移动原有方法实现 ...
        
    def predict_best_entry_exit(self, symbol):
        """预测最佳交易点位"""
        # ... 移动原有方法实现 ... 