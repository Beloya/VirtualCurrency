# ml_model.py

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
import pickle
from analyzers.technical_analyzer import TechnicalAnalyzer
from analyzers.pattern_analyzer import PatternAnalyzer
from joblib import Parallel, delayed
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import matplotlib.pyplot as plt
from analyzers.multi_timeframe_analyzer import MultiTimeframeAnalyzer





class MLModel:
    def __init__(self, use_ml_model,model_params=None,data_fetcher=None,window_size=1000):
        self.models = {}
        self.feature_columns = []
        self.is_model_trained = False
        self.use_ml_model = use_ml_model
        self.te = TechnicalAnalyzer()
        self.pa = PatternAnalyzer()
        self.model_params = model_params or {
            'loss': 'log',  # 对应于逻辑回归
            'max_iter': 1000,
            'tol': 1e-3,
            'random_state': 42
        }
        self.window_size = window_size
        self.multi_timeframe_analyzer = MultiTimeframeAnalyzer(data_fetcher)


        # 初始化随机森林模型
        # self.model = RandomForestClassifier(n_estimators=100, random_state=42)

    def prepare_data(self, df):
        """准备特征和标签,增加多维度时间特征和技术指标"""
        try:
            # 基础特征
            features = pd.DataFrame()
            
            # 价格特征
            features['close'] = df['close']
            features['open'] = df['open'] 
            features['high'] = df['high']
            features['low'] = df['low']
            features['volume'] = df['volume']
            
            # 计算不同时间窗口的价格变化率
            for window in [5, 10, 20, 30]:
                features[f'price_change_{window}'] = df['close'].pct_change(window)
                features[f'volume_change_{window}'] = df['volume'].pct_change(window)
            
            # 计算移动平均
            for window in [5, 10, 20, 50]:
                features[f'ma_{window}'] = df['close'].rolling(window=window).mean()
                features[f'ma_volume_{window}'] = df['volume'].rolling(window=window).mean()
            
            # 计算RSI
            for window in [6, 14, 20]:
                features[f'rsi_{window}'] = self.te.calculate_rsi(df['close'].values, period=window)
            
            # results = Parallel(n_jobs=-1)(delayed(self.te.calculate_rsi)(df['close'], period) for period in [6, 14, 20])

            # 计算MACD
            macd, signal, hist = self.te.calculate_macd(df['close'].values)
            features['macd'] = macd
            features['macd_signal'] = signal
            features['macd_hist'] = hist
            
            # 计算布林带
            for window in [20, 50]:
                ma, upper, lower = self.te.calculate_dynamic_bollinger_bands(df['close'].values)
                features[f'bb_upper_{window}'] = upper
                features[f'bb_lower_{window}'] = lower
                features[f'bb_width_{window}'] = (upper - lower) / ma
            
            # 计算OBV
            features['obv'] = self.te.calculate_obv(df['close'].values, df['volume'].values)
            
            # 添加时间特征
            features['hour'] = df.index.hour
            features['day_of_week'] = df.index.dayofweek
            features['is_weekend'] = features['day_of_week'].isin([5, 6]).astype(int)
            
            # 计算波动率
            for window in [5, 10, 20]:
                features[f'volatility_{window}'] = df['close'].rolling(window).std()

            # 成交量特征
            for window in [5, 10, 20]:
                # 成交量变化率
                features[f'volume_change_{window}'] = df['volume'].pct_change(window)
                # 成交量移动平均
                features[f'volume_ma_{window}'] = df['volume'].rolling(window=window).mean()
        
            # 成交量震荡指标
            short_window = 5
            long_window = 20
            features['volume_oscillator'] = features[f'volume_ma_{short_window}'] - features[f'volume_ma_{long_window}']
            
            # 成交量加权平均价格 (VWAP)
            features['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()

            # 使用 MultiTimeframeAnalyzer 分析趋势
            trend = self.multi_timeframe_analyzer.analyze_trend(df)
            if trend:
                direction_map = {'bullish': 1, 'bearish': -1, 'neutral': 0}
                features['trend_direction'] = direction_map.get(trend['direction'], 0)
                features['price_vs_ma'] = direction_map.get(trend['price_vs_ma'], 0)
                features['rsi_status'] = direction_map.get(trend['rsi_status'], 0)
                features['macd_status'] = direction_map.get(trend['macd_status'], 0)
                features['trend_strength'] = trend['strength']

            
            # 标签: 未来n个周期的价格变动方向
            for period in [1, 3, 6, 12]:  # 1h, 3h, 6h, 12h
                labels = (df['close'].shift(-period) > df['close']).astype(int)
                features[f'target_{period}h'] = labels
            
            # 删除缺失值
            features = features.dropna()
            # 检查并处理无穷大和超大值
            features.replace([np.inf, -np.inf], np.nan, inplace=True)
            features.dropna(inplace=True)

            # 标准化特征
            # features = (features - features.mean()) / features.std()
            # print(features.describe())
            return features
            
        except Exception as e:
            print(f"准备数据错误: {str(e)}")
            return None

    def train_model(self, df):
        """使用交叉验证训练多个时间维度的模型"""
        try:
            # 准备数据
            df.dropna(inplace=True)
            df = df[df['close'] > 0]
            features = self.prepare_data(df)
            if features is None:
                return
                
            # 仅使用滚动窗口内的数据
            # features = features.iloc[-self.window_size:]
            # 分离特征和标签
            target_columns = [col for col in features.columns if col.startswith('target_')]
            feature_columns = [col for col in features.columns if not col.startswith('target_')]
            
            X = features[feature_columns]
            
            # 对每个预测时间维度训练一个模型
            self.models = {}
            for target in target_columns:
                y = features[target]
                
                # 创建模型
                model = RandomForestClassifier(
                    n_estimators= 300,
                    max_depth=10,
                    min_samples_split=2,
                    min_samples_leaf=1,
                    random_state=42
                )
                
                # 使用时间序列交叉验证
                tscv = TimeSeriesSplit(n_splits=5)
                scores = []
                
                for train_idx, val_idx in tscv.split(X):
                    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                    
                    # 训练模型
                    model.fit(X_train, y_train)
                    
                    # 评估模型
                    score = model.score(X_val, y_val)
                    scores.append(score)
                
                print(f"{target} 模型交叉验证得分: {np.mean(scores):.3f} ± {np.std(scores):.3f}")
                
                # 使用全部数据重新训练
                model.fit(X, y)


                self.models[target] = model
            
            self.is_model_trained = True
            self.feature_columns = feature_columns
            
            # 保存模型
            with open('models.pkl', 'wb') as f:
                pickle.dump({
                    'models': self.models,
                    'feature_columns': self.feature_columns
                }, f)
                
            print("模型训练完成")
            
        except Exception as e:
            print(f"训练模型错误: {str(e)}")

    def predict_market_behavior(self, df):
        """使用多个时间维度的模型进行预测"""
        if not self.is_model_trained:
            print("模型尚未训练")
            return None
            
        try:
            # 准备特征
            features = self.prepare_data(df)
            if features is None:
                print("无法准备数据")
                return None
                
            # 获取最新数据点的特征
            latest_features = features[self.feature_columns].iloc[-1:]
            
            # 并行预测
            def predict_for_target(target, model):
                pred = model.predict(latest_features)[0]
                prob = model.predict_proba(latest_features)[0]
                return target, pred, prob
        
            results = Parallel(n_jobs=-1)(
                delayed(predict_for_target)(target, model) for target, model in self.models.items()
            )


            # 存储不同时间维度的预测结果
            predictions = {}
            probabilities = {}
            # 存储不同时间维度的预测结果
            predictions = {target: pred for target, pred, prob in results}
            probabilities = {target: prob for target, pred, prob in results}
            
            # 使用每个模型进行预测
            for target, model in self.models.items():
                pred = model.predict(latest_features)[0]
                prob = model.predict_proba(latest_features)[0]
                
                predictions[target] = pred
                probabilities[target] = prob
                # print(f"预测结果: {pred}, 置信度: {prob}")
            
            return {
                'predictions': predictions,
                'probabilities': probabilities
            }
            
        except Exception as e:
            print(f"预测错误: {str(e)}")
            return None

    def load_model(self):
        """加载模型"""
        try:
            with open('models.pkl', 'rb') as f:
                data = pickle.load(f)
            self.models = data['models']
            self.feature_columns = data['feature_columns']
            self.is_model_trained = True
            print("模型加载完成")
        except FileNotFoundError:
            print("模型文件未找到，请先训练模型")
    def determine_market_trend(self, predictions, probabilities,market_volatility, base_confidence_threshold=0.7):
        """综合分析市场趋势，结合多模型和时间维度"""
        try:
            # 定义时间维度权重
            weights = {
                'short': 0.3,  # 短期权重
                'medium': 0.3,  # 中期权重
                'long': 0.4   # 长期权重
            }
            weights_dict = {
                'target_1h': "short",  # 短期权重
                'target_3h': "medium",  # 中期权重
                'target_6h': "medium",  # 长期权重
                'target_12h': "long"
            }
            
            # 动态调整置信度阈值
            confidence_threshold = base_confidence_threshold + (market_volatility / 100)
            # print(f"置信度阈值: {confidence_threshold}")
            # 初始化分数
            bullish_score = 0
            bearish_score = 0
            
            # 遍历每个时间维度的预测结果
            for timeframe, pred in predictions.items():
                prob = probabilities[timeframe]
                confidence = max(prob)  # 获取最高置信度
                
                # 仅考虑置信度高于阈值的预测
                if confidence >= confidence_threshold:
                    weight = weights.get(weights_dict.get(timeframe), 0)
                    
                    # 加权分数
                    if pred == 1:  # 假设 1 表示看涨
                        bullish_score += weight * confidence
                    elif pred == 0:  # 假设 0 表示看跌
                        bearish_score += weight * confidence
            
            # 检查异常值
            if abs(bullish_score - bearish_score) < 0.1:
                return "观望"  # 如果分数接近，选择观望
            
            # 综合判断趋势
            if bullish_score > bearish_score:
                return "看多"
            elif bearish_score > bullish_score:
                return "看空"
            else:
                return "观望"
        
        except Exception as e:
            print(f"市场趋势判断错误: {str(e)}")
            return "观望"
    
    def evaluate_model(self, df):
        """评估模型性能"""
        if not self.is_model_trained:
            print("模型尚未训练")
            return None

        try:
            # 准备数据
            features = self.prepare_data(df)
            if features is None:
                print("无法准备数据")
                return None

            # 分离特征和标签
            target_columns = [col for col in features.columns if col.startswith('target_')]
            feature_columns = [col for col in features.columns if not col.startswith('target_')]

            X = features[feature_columns]

            # 评估每个模型
            evaluation_results = {}
            for target in target_columns:
                y = features[target]
                model = self.models.get(target)

                if model is None:
                    print(f"模型 {target} 未找到")
                    continue

                # 使用时间序列交叉验证
                tscv = TimeSeriesSplit(n_splits=5)
                accuracies, precisions, recalls, f1s = [], [], [], []

                for train_idx, val_idx in tscv.split(X):
                    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                    # 预测
                    y_pred = model.predict(X_val)

                    # 计算评估指标
                    accuracies.append(accuracy_score(y_val, y_pred))
                    precisions.append(precision_score(y_val, y_pred))
                    recalls.append(recall_score(y_val, y_pred))
                    f1s.append(f1_score(y_val, y_pred))

                evaluation_results[target] = {
                    'accuracy': np.mean(accuracies),
                    'precision': np.mean(precisions),
                    'recall': np.mean(recalls),
                    'f1_score': np.mean(f1s)
                }

            for target, metrics in evaluation_results.items():
                print(f"{target} 模型评估结果:")
                print(f"  准确率: {metrics['accuracy']:.3f}")
                print(f"  精确率: {metrics['precision']:.3f}")
                print(f"  召回率: {metrics['recall']:.3f}")
                print(f"  F1 分数: {metrics['f1_score']:.3f}")
            return evaluation_results

        except Exception as e:
            print(f"评估模型错误: {str(e)}")
            return None
        
    def backtest_model(self, df, initial_balance=10000, trade_amount=2000):
        """使用历史数据进行回溯测试"""
        if not self.is_model_trained:
            print("模型尚未训练")
            return None

        try:
            # 准备数据
            features = self.prepare_data(df)
            if features is None:
                print("无法准备数据")
                return None

            # 初始化回溯测试参数
            balance = initial_balance
            positions = 0
            trade_log = []

            # 遍历数据进行回溯测试
            window_size = 200 # 例如，使用10个数据点的窗口
            for i in range(window_size, len(features) - 1):
                current_features = features.iloc[i-window_size:i]
                next_close_price = df['close'].iloc[i+1]

                # print(f"当前时间: {df.index[i]}, 当前价格: {next_close_price}")
                # 获取模型预测
                predictions = self.predict_market_behavior(current_features)
                if predictions is None:
                    continue

                # 综合分析市场趋势
                market_trend = self.determine_market_trend(
                    predictions['predictions'],
                    predictions['probabilities'],
                    market_volatility=0  # 假设市场波动率为0
                )
                # 根据市场趋势进行交易
                if market_trend == "看多" and balance >= trade_amount:
                    # 买入
                    positions += trade_amount / next_close_price
                    balance -= trade_amount
                    trade_log.append(f"买入: {trade_amount} at {next_close_price}")

                elif market_trend == "看空" and positions > 0:
                    # 卖出
                    balance += positions * next_close_price
                    trade_log.append(f"卖出: {positions} at {next_close_price}")
                    positions = 0
                # elif market_trend == "观望" and positions > 0:
                #     # 观望行情卖出
                #     balance += positions * next_close_price
                #     trade_log.append(f"观望行情卖出: {positions} at {next_close_price}")
                #     positions = 0
                
                print(f"当前时间: {df.index[i]}, 当前余额: {balance}, 当前持仓: {positions}, 当前价格: {next_close_price}")

            # 计算最终余额
            final_balance = balance + positions * df['close'].iloc[-1]
            print(f"初始余额: {initial_balance}, 最终余额: {final_balance}")
            print("交易记录:")
            for log in trade_log:
                print(log)

            return final_balance

        except Exception as e:
            print(f"回溯测试错误: {str(e)}")
            return None