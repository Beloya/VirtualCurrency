# ml_model.py

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
import pickle

class MLModel:
    def __init__(self, use_ml_model):
        self.models = {}
        self.feature_columns = []
        self.is_model_trained = False
        self.use_ml_model = use_ml_model
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
                features[f'rsi_{window}'] = self.calculate_rsi(df['close'].values, period=window)
            
            # 计算MACD
            macd, signal, hist = self.calculate_macd(df['close'].values)
            features['macd'] = macd
            features['macd_signal'] = signal
            features['macd_hist'] = hist
            
            # 计算布林带
            for window in [20, 50]:
                ma, upper, lower = self.calculate_bollinger_bands(df['close'].values, window=window)
                features[f'bb_upper_{window}'] = upper
                features[f'bb_lower_{window}'] = lower
                features[f'bb_width_{window}'] = (upper - lower) / ma
            
            # 计算OBV
            features['obv'] = self.calculate_obv(df['close'].values, df['volume'].values)
            
            # 添加时间特征
            features['hour'] = df.index.hour
            features['day_of_week'] = df.index.dayofweek
            features['is_weekend'] = features['day_of_week'].isin([5, 6]).astype(int)
            
            # 计算波动率
            for window in [5, 10, 20]:
                features[f'volatility_{window}'] = df['close'].rolling(window).std()
            
            # 标签: 未来n个周期的价格变动方向
            for period in [1, 3, 6, 12]:  # 1h, 3h, 6h, 12h
                labels = (df['close'].shift(-period) > df['close']).astype(int)
                features[f'target_{period}h'] = labels
            
            # 删除缺失值
            features = features.dropna()
            
            return features
            
        except Exception as e:
            print(f"准备数据错误: {str(e)}")
            return None

    def train_model(self, df):
        """使用交叉验证训练多个时间维度的模型"""
        try:
            # 准备数据
            features = self.prepare_data(df)
            if features is None:
                return
                
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
                    n_estimators=100,
                    max_depth=10,
                    min_samples_split=10,
                    min_samples_leaf=5,
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
            
            # 存储不同时间维度的预测结果
            predictions = {}
            probabilities = {}
            
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
    def determine_market_trend(self, predictions, probabilities, confidence_threshold=0.7):
        """综合分析市场趋势，结合多模型和时间维度"""
        try:
            # 定义时间维度权重
            weights = {
                'short': 0.2,  # 短期权重
                'medium': 0.3,  # 中期权重
                'long': 0.5   # 长期权重
            }
            weights_dict = {
                'target_1h': "short",  # 短期权重
                'target_3h': "medium",  # 中期权重
                'target_6h': "medium",  # 长期权重
                'target_12h': "long"
            }
            
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
        