import ccxt
import pandas as pd
import threading
import time

class DataFetcher:
    def __init__(self, config):
        self.config = config
        self.exchange = ccxt.binance()
        self.running = False

    def test_connection(self):
        try:
            self.exchange.load_time_difference()
            return True
        except Exception as e:
            print(f"连接测试失败: {str(e)}")
            return False

    def start_fetching(self, callback):
        self.running = True
        threading.Thread(target=self.fetch_data, args=(callback,), daemon=True).start()

    def stop_fetching(self):
        self.running = False

    def fetch_data(self, callback):
        while self.running:
            try:
                ohlcv = self.exchange.fetch_ohlcv('BTC/USDT', '1h', limit=100)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                callback(df)
                time.sleep(10)
            except Exception as e:
                print(f"数据获取错误: {str(e)}")
                time.sleep(5) 