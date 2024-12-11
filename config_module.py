import json
import os

class ConfigManager:
    def __init__(self):
        self.config_file = 'config.json'

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return self.default_config()

    def save_config(self, config):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False)

    def default_config(self):
        return {
            'proxy_host': '127.0.0.1',
            'proxy_port': '7890',
            'use_proxy': False,
            'symbol': 'BTC/USDT',
            'timeframe': '1h'
        } 