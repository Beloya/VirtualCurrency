# data_fetcher.py

import ccxt
import pandas as pd
import time
from tkinter import ttk, messagebox
import numpy as np



class DataFetcher:
    def __init__(self, exchange_name='binance', use_proxy=False, proxy_host='127.0.0.1', proxy_port='1080'):
        self.exchange = getattr(ccxt, exchange_name)()
        self.use_proxy = use_proxy
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.update_exchange_proxy(use_proxy,proxy_host,proxy_port)

    def update_exchange_proxy(self,use_proxy,proxy_host,proxy_port):
        """更新交易所实例的代理设置"""
        self.use_proxy = use_proxy
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        if self.use_proxy:
            proxy = f'http://{self.proxy_host}:{self.proxy_port}'
            self.exchange.proxies = {
                'http': proxy,
                'https': proxy
            }
        else:
            self.exchange.proxies = None

    def fetch_ohlcv_data(self, symbol, timeframe, start_date=None, end_date=None,data_limit=1000,page_limit=1000):
        """
        获取K线数据并进行预处理
        
        Args:
            symbol (str): 交易对
            timeframe (str): 时间周期
            start_date (str, optional): 开始日期，格式 'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式 'YYYY-MM-DD'
        """
        try:
            all_ohlcv = []
            since = None

            # 如果提供了日期范围，转换为时间戳
            if start_date:
                since = int(pd.Timestamp(start_date).timestamp() * 1000)
            if end_date:
                end_timestamp = int(pd.Timestamp(end_date).timestamp() * 1000)

            fetch_limit = min(data_limit,page_limit)
            left_num = data_limit
            while True:
                # 获取K线数据
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol, 
                    timeframe, 
                    since=since,
                    limit=fetch_limit  # 每次获取1000条数据
                )
                left_num-=fetch_limit
                fetch_limit = min(page_limit,left_num)
                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)

                # 更新since为最后一条数据的时间戳
                since = ohlcv[-1][0] + 1

                # 如果提供了结束日期，检查是否超出范围
                if end_date and ohlcv[-1][0] > end_timestamp:
                    break

                # 如果获取的数据量已经超过data_limit，停止获取
                if left_num<=0:
                    break

                # 暂停一段时间以避免请求过于频繁
                time.sleep(self.exchange.rateLimit / 1000)

            # 过滤结束日期
            if end_date:
                all_ohlcv = [candle for candle in all_ohlcv if candle[0] <= end_timestamp]

            # 创建DataFrame并设置正确的时间索引
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"获取{timeframe}数据错误: {str(e)}")
            return None

    def test_exchange_connection(self):
        """测试交易所连接"""
        try:
            # 更新代理设置
            self.update_exchange_proxy(self.use_proxy,self.proxy_host,self.proxy_port)
            
            # 尝试获取服务器时间来测试连接
            self.exchange.load_time_difference()
            return True
        except Exception as e:
            print(f"连接测试失败: {str(e)}")
            return False
    
    def fetch_data(self,symbol,timeframe):
        # 确保交易所实例使用最新的代理设置
        # self.update_exchange()
                
        # 取K线数据
        ohlcv = self.exchange.fetch_ohlcv(
            symbol,
            timeframe,
            limit=1000
        )
                
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
                

                
                
            
    def fetch_and_save_historical_data(self, symbol, timeframe, since,end_date, filename):
        """抓取并保存历史数据"""
        try:
            # 使用ccxt库从交易所获取数据
            ohlcv = self.fetch_ohlcv_data(symbol=symbol, timeframe=timeframe, since=since,end_date=end_date)
            # 将数据转换为DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # 保存数据到CSV文件
            df.to_csv(filename, index=False)
            print(f"数据已保存到 {filename}")
        except Exception as e:
            print(f"抓取历史数据错误: {str(e)}")
    
    def get_current_price(self, symbol):
        """
        获取当前价格
        """
        try:
            # 首先尝试从交易所获取最新价格
            ticker = self.exchange.fetch_ticker(symbol)
            if ticker and 'last' in ticker:
                return ticker['last']
            
            # 如果无法直接获取最新价格，则从最近的K线数据中获取
            df = self.fetch_ohlcv_data(symbol, '1m', limit=1)  # 获取最近1分钟的数据
            if df is not None and not df.empty:
                return df['close'].iloc[-1]
                
            # 如果都失败了，抛出异常
            raise Exception("无法获取当前价格")
            
        except Exception as e:
            print(f"获取当前价格错误: {str(e)}")
            # 返回None或者抛出异常，这里选择返回None
            return None
        
    def release_exchange(self):
        """释放交易所实例"""
        self.exchange = None
        # self.update_exchange_proxy(False, '127.0.0.1', '1080')

    def calculate_market_volatility(self, prices, window=20):
        """
        计算市场波动性，使用对数收益率的标准差。
        
        :param prices: pd.Series, 价格数据
        :param window: int, 计算波动性的时间窗口
        :return: float, 市场波动性
        """
        # 计算对数收益率
        log_returns = np.log(prices / prices.shift(1))
        
        # 计算对数收益率的标准差
        volatility = log_returns.rolling(window=window).std().iloc[-1]
        
        # 将波动性转换为百分比
        return volatility * 100

