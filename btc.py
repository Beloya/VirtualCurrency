#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
import ccxt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
import threading
import time
import json
import os
import sys  # 添加 sys 模块导入
from sklearn.ensemble import RandomForestClassifier
from tkinter import filedialog
from tkcalendar import DateEntry
import pickle
from sklearn.model_selection import TimeSeriesSplit

# 设置matplotlib的默认编码
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
plt.rcParams['font.family'] = ['sans-serif']  # 设置字体族

class CryptoMonitor:
    def __init__(self):
        # 设置GUI默认编码
        if hasattr(sys, 'getdefaultencoding'):
            sys.getdefaultencoding()
        
        self.root = tk.Tk()
        self.root.title('加密货币监控系统')
        self.root.geometry('1200x900')
        
        # 定义颜色主题
        self.vscode_theme = {
            'bg': '#1e1e1e',  # 背景色
            'fg': '#d4d4d4',  # 前景色
            'accent': '#007acc',  # 强调色
            'button_bg': '#3c3c3c',  # 按钮背景色
            'button_fg': '#ffffff'   # 按钮前景色
        }
        
        self.default_theme = {
            'bg': '#f0f0f0',  # 背景色
            'fg': '#000000',  # 前景色
            'accent': '#007acc',  # 强调色
            'button_bg': '#e0e0e0',  # 按钮背景色
            'button_fg': '#000000'   # 按钮前景色
        }
        self.is_model_trained = False
        # 初始化当前主题
        self.current_theme = tk.StringVar(value='VSCode')
        self.colors = self.vscode_theme if self.current_theme.get() == 'VSCode' else self.default_theme

        # 设置深色主题颜色
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 初始化 matplotlib 图形
        self.fig, self.ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
        
        # 初始化交易对和时间周期
        self.symbols = ['BTC/USDT', 'ETH/USDT']
        self.timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        
        # 初始化变量
        self.symbol_var = tk.StringVar(value='BTC/USDT')
        self.timeframe_var = tk.StringVar(value='1h')
        self.use_proxy = tk.BooleanVar(value=False)
        self.proxy_host = tk.StringVar(value='127.0.0.1')
        self.proxy_port = tk.StringVar(value='7890')
        self.max_signals = tk.IntVar(value=100)
        self.trade_amount = tk.DoubleVar(value=100.0)  # 默认交易金额
        
        # 初始化价格提醒设置
        self.price_alert = tk.BooleanVar(value=True)
        self.ma_cross_alert = tk.BooleanVar(value=True)
        self.bollinger_alert = tk.BooleanVar(value=True)
        self.rsi_alert = tk.BooleanVar(value=True)
        self.volume_alert = tk.BooleanVar(value=True)
        self.trend_alert = tk.BooleanVar(value=True)
        self.momentum_alert = tk.BooleanVar(value=True)
        self.macd_cross_alert = tk.BooleanVar(value=True)
        
        # 初始化图表显示设置
        self.show_price = tk.BooleanVar(value=True)
        self.show_ma5 = tk.BooleanVar(value=True)
        self.show_ma10 = tk.BooleanVar(value=True)
        self.show_bollinger = tk.BooleanVar(value=True)
        self.show_rsi = tk.BooleanVar(value=True)
        self.show_macd = tk.BooleanVar(value=True)
        
        # 初始化支撑位和压力位变量
        self.support_level = tk.StringVar(value='--')
        self.resistance_level = tk.StringVar(value='--')
        
        # 初始化其他变量
        self.running = False
        self.recent_signals = []
        self.use_ml_model = tk.BooleanVar(value=False)  # 默认启用机器学习模型
        self.start_date = tk.StringVar(value='2023-01-01')  # 默认开始日期
        self.end_date = tk.StringVar(value='2023-12-31')    # 默认结束日期
        
        # 加载设置
        self.load_settings()
        
        # 现在可以安全地应用主题
        self.apply_theme()
        
        # 创建控件
        self.create_widgets()
        
        # 加载配置
        self.config_file = 'config.json'
        self.load_config_without_display()
        
        # 更新信号显示
        self.update_signal_display()
        
        # 初始化数据
        self.exchange = ccxt.binance()  # 例如，使用 Binance 交易所
        self.load_model()
        
        # 添加醒目的按钮样式
        self.style.configure('Accent.TButton',
            background='#0e639c',
            foreground='white',
            padding=10,
            font=('Microsoft YaHei UI', 9, 'bold'))
        
        # 初始化信号记录
        self.last_signal_times = {}
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始化随机森林模型
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        
    
    def load_config_without_display(self):
        """从文件加载配置，但不更新显示"""
        self.config = {
            'proxy_host': '127.0.0.1',
            'proxy_port': '7890',
            'use_proxy': False,
            'price_alert': True,
            'ma_cross_alert': True,
            'bollinger_alert': True,
            'rsi_alert': True,
            'volume_alert': True,
            'trend_alert': True,
            'momentum_alert': True,
            'macd_cross_alert': True,
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'max_signals': 100,
            'recent_signals': [],
            'theme': 'VSCode',
            'trade_amount': 100.0,  # 默认交易金额
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
            except:
                pass
        
        # 初始化代理设置
        self.use_proxy.set(self.config.get('use_proxy', False))
        self.proxy_host.set(self.config.get('proxy_host', '127.0.0.1'))
        self.proxy_port.set(self.config.get('proxy_port', '7890'))
        
        # 初始化交易设置
        self.symbol_var.set(self.config.get('symbol', 'BTC/USDT'))
        self.timeframe_var.set(self.config.get('timeframe', '1h'))
        
        # 加载信号设置
        self.max_signals.set(self.config.get('max_signals', 100))
        self.recent_signals = self.config.get('recent_signals', [])
        
        # 初始化主题
        self.current_theme.set(self.config.get('theme', 'VSCode'))
        self.apply_theme()
        
        # 更新信号显示
        self.update_signal_display()
        self.trade_amount.set(self.config.get('trade_amount', 100.0))
    
    def load_config(self):
        """从文件加载配置"""
        self.config = {
            'proxy_host': '127.0.0.1',
            'proxy_port': '7890',
            'use_proxy': False,  # 默认不使用代理
            'price_alert': True,
            'ma_cross_alert': True,
            'bollinger_alert': True,
            'rsi_alert': True,
            'volume_alert': True,
            'trend_alert': True,
            'momentum_alert': True,
            'macd_cross_alert': True,
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'max_signals': 100,  # 默认保存100条信号
            'recent_signals': [],  # 保存的信号列表
            'theme': 'VSCode'
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
            except:
                pass
        
        # 初始化代理设置
        self.use_proxy.set(self.config.get('use_proxy', False))
        self.proxy_host.set(self.config.get('proxy_host', '127.0.0.1'))
        self.proxy_port.set(self.config.get('proxy_port', '7890'))
        
        # 初始化交易设置
        self.symbol_var.set(self.config.get('symbol', 'BTC/USDT'))
        self.timeframe_var.set(self.config.get('timeframe', '1h'))
        
        # 加载信号设置
        self.max_signals.set(self.config.get('max_signals', 100))
        self.recent_signals = self.config.get('recent_signals', [])
        
        # 初始化主题
        self.current_theme.set(self.config.get('theme', 'VSCode'))
        self.apply_theme()
        
        # 更新信号显示
        self.update_signal_display()
    
    def save_config(self):
        """保存配置到文件"""
        self.config.update({
            'proxy_host': self.proxy_host.get(),
            'proxy_port': self.proxy_port.get(),
            'use_proxy': self.use_proxy.get(),
            'price_alert': self.price_alert.get(),
            'ma_cross_alert': self.ma_cross_alert.get(),
            'bollinger_alert': self.bollinger_alert.get(),
            'rsi_alert': self.rsi_alert.get(),
            'volume_alert': self.volume_alert.get(),
            'trend_alert': self.trend_alert.get(),
            'momentum_alert': self.momentum_alert.get(),
            'macd_cross_alert': self.macd_cross_alert.get(),
            'symbol': self.symbol_var.get(),
            'timeframe': self.timeframe_var.get(),
            'max_signals': self.max_signals.get(),
            'recent_signals': self.recent_signals,
            'theme': self.current_theme.get(),
            'trade_amount': self.trade_amount.get(),  # 保存交易金额
            'prediction_threshold': self.prediction_threshold.get(),  # 保存预测阈值
        })
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False)
    
    def update_exchange(self):
        """更新交易所实例的代理设置"""
        try:
            if self.exchange is not None:
                if self.use_proxy.get():
                    # 使用代理
                    proxy = f'http://{self.proxy_host.get()}:{self.proxy_port.get()}'
                    self.exchange.proxies = {
                        'http': proxy,
                        'https': proxy
                    }
                else:
                    # 不使用代理
                    self.exchange.proxies = None
            else:
                print("交易所实例未初始化")
        except Exception as e:
            print(f"更新代理设置错误: {str(e)}")

    def create_widgets(self):
        """创建主界面控件"""
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 添加文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="设置", command=self.show_settings_window)
        file_menu.add_command(label="训练模型", command=self.show_training_window)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 创建主控制框架
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 创建中间图表区域
        middle_frame = ttk.Frame(self.root)
        middle_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建图表区域
        chart_frame = ttk.LabelFrame(middle_frame, text='价格走势图', padding=5)
        chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 添加最近信号显示框架
        signal_frame = ttk.LabelFrame(middle_frame, text='最近信号', padding=2)
        signal_frame.pack(side=tk.BOTTOM, pady=2, padx=2, fill=tk.X)
        
        # 创建文本框以显示信号
        self.signal_text = tk.Text(signal_frame, height=10, wrap=tk.WORD, 
                                   bg=self.colors['bg'], fg=self.colors['fg'], 
                                   font=('Microsoft YaHei UI', 9))
        self.signal_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(signal_frame, orient='vertical', command=self.signal_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.signal_text.configure(yscrollcommand=scrollbar.set)
        
        # 交易设置 - 使用水平布局
        trade_frame = ttk.LabelFrame(control_frame, text='交易设置', padding=2)
        trade_frame.pack(pady=2, padx=2, fill=tk.X)
        
        symbol_frame = ttk.Frame(trade_frame)
        symbol_frame.pack(fill=tk.X, padx=2)
        ttk.Label(symbol_frame, text='交易对:').pack(side=tk.LEFT, padx=2)
        self.symbol_var = tk.StringVar(value='BTC/USDT')
        symbol_cb = ttk.Combobox(symbol_frame, textvariable=self.symbol_var, 
            values=self.symbols, width=10)
        symbol_cb.pack(side=tk.LEFT, padx=2)
        symbol_cb.bind('<<ComboboxSelected>>', lambda e: self.save_config())
        
        timeframe_frame = ttk.Frame(trade_frame)
        timeframe_frame.pack(fill=tk.X, padx=2, pady=2)
        ttk.Label(timeframe_frame, text='周期:').pack(side=tk.LEFT, padx=2)
        self.timeframe_var = tk.StringVar(value='1h')
        timeframe_cb = ttk.Combobox(timeframe_frame, textvariable=self.timeframe_var,
            values=self.timeframes, width=10)
        timeframe_cb.pack(side=tk.LEFT, padx=2)
        timeframe_cb.bind('<<ComboboxSelected>>', lambda e: self.save_config())
        
        # 价格显示
        price_frame = ttk.LabelFrame(control_frame, text='当前价格', padding=2)
        price_frame.pack(pady=2, padx=2, fill=tk.X)
        self.price_label = ttk.Label(price_frame, text='--', 
            font=('Consolas', 12, 'bold'))
        self.price_label.pack(pady=2)
        
        # 监控设置 - 使用网格布局
        monitor_frame = ttk.LabelFrame(control_frame, text='监控设置', padding=2)
        monitor_frame.pack(pady=2, padx=2, fill=tk.X)
        
        monitor_grid = ttk.Frame(monitor_frame)
        monitor_grid.pack(padx=2, pady=2)
        
        ttk.Label(monitor_grid, text='监控时间:').grid(row=0, column=0, padx=2)
        self.monitor_minutes = ttk.Entry(monitor_grid, width=8)
        self.monitor_minutes.insert(0, '30')
        self.monitor_minutes.grid(row=0, column=1, padx=2)
        ttk.Label(monitor_grid, text='分钟').grid(row=0, column=2, padx=2)
        
        ttk.Label(monitor_grid, text='价格阈值:').grid(row=1, column=0, padx=2)
        self.price_threshold = ttk.Entry(monitor_grid, width=8)
        self.price_threshold.insert(0, '1')
        self.price_threshold.grid(row=1, column=1, padx=2)
        ttk.Label(monitor_grid, text='%').grid(row=1, column=2, padx=2)
        
        # 图表控制 - 使用水平布局
        chart_control_frame = ttk.LabelFrame(control_frame, text='图表显示', padding=2)
        chart_control_frame.pack(pady=2, padx=2, fill=tk.X)
        
        self.show_price = tk.BooleanVar(value=True)
        self.show_ma5 = tk.BooleanVar(value=True)
        self.show_ma10 = tk.BooleanVar(value=True)
        self.show_bollinger = tk.BooleanVar(value=True)
        self.show_rsi = tk.BooleanVar(value=True)
        self.show_macd = tk.BooleanVar(value=True)  # 添加MACD控制变量
        
        checks_frame = ttk.Frame(chart_control_frame)
        checks_frame.pack(fill=tk.X, padx=2)
        
        ttk.Checkbutton(checks_frame, text='价格', variable=self.show_price, 
            command=self.update_chart_visibility).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(checks_frame, text='MA5', variable=self.show_ma5,
            command=self.update_chart_visibility).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(checks_frame, text='MA10', variable=self.show_ma10,
            command=self.update_chart_visibility).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(checks_frame, text='布林', variable=self.show_bollinger,
            command=self.update_chart_visibility).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(checks_frame, text='RSI', variable=self.show_rsi,
            command=self.update_chart_visibility).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(checks_frame, text='MACD', variable=self.show_macd,
            command=self.update_chart_visibility).pack(side=tk.LEFT, padx=2)
        
        # 添加提醒设置框
        alert_frame = ttk.LabelFrame(control_frame, text='提醒设置', padding=2)
        alert_frame.pack(pady=2, padx=2, fill=tk.X)
        
        # 价格提醒置
        price_alert_frame = ttk.Frame(alert_frame)
        price_alert_frame.pack(fill=tk.X, padx=2)
        
        self.price_alert = tk.BooleanVar(value=True)
        ttk.Checkbutton(price_alert_frame, text='价格波动', 
            variable=self.price_alert).pack(side=tk.LEFT, padx=2)
        
        # 技术指标提醒设置
        indicator_alert_frame = ttk.Frame(alert_frame)
        indicator_alert_frame.pack(fill=tk.X, padx=2)
        
        self.ma_cross_alert = tk.BooleanVar(value=True)
        self.bollinger_alert = tk.BooleanVar(value=True)
        self.rsi_alert = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(indicator_alert_frame, text='均线交叉', 
            variable=self.ma_cross_alert).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(indicator_alert_frame, text='布林突破', 
            variable=self.bollinger_alert).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(indicator_alert_frame, text='RSI超买卖', 
            variable=self.rsi_alert).pack(side=tk.LEFT, padx=2)
        
        # 添加策略提醒设置
        strategy_frame = ttk.LabelFrame(alert_frame, text='策略提醒', padding=2)
        strategy_frame.pack(pady=2, padx=2, fill=tk.X)
        
        self.volume_alert = tk.BooleanVar(value=True)
        self.trend_alert = tk.BooleanVar(value=True)
        self.momentum_alert = tk.BooleanVar(value=True)
        self.macd_cross_alert = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(strategy_frame, text='成交量异常', 
            variable=self.volume_alert).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(strategy_frame, text='趋势突破', 
            variable=self.trend_alert).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(strategy_frame, text='动量背离', 
            variable=self.momentum_alert).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(strategy_frame, text='MACD交叉', 
            variable=self.macd_cross_alert).pack(side=tk.LEFT, padx=2)
        
        self.signal_menu = tk.Menu(self.root, tearoff=0)
        self.signal_menu.add_command(label="清空信号", command=self.clear_signals)
        self.signal_menu.add_separator()
        self.signal_menu.add_command(label="退出", command=self.root.quit)


        # 绑定右键点击事件
        self.signal_text.bind("<Button-3>", self.show_signal_menu)
        # 添加策略评分显示框架
        score_frame = ttk.LabelFrame(control_frame, text='策略评分', padding=2)
        score_frame.pack(pady=2, padx=2, fill=tk.X)
        
        # 添加帮助按钮
        help_button = ttk.Button(score_frame, text='?', width=3,
            command=self.show_strategy_help)
        help_button.pack(side=tk.RIGHT, padx=2, pady=2)
        
        # 总分显示
        total_score_frame = ttk.Frame(score_frame)
        total_score_frame.pack(fill=tk.X, padx=2, pady=2)
        ttk.Label(total_score_frame, text='总体评分:').pack(side=tk.LEFT, padx=2)
        self.total_score_label = ttk.Label(total_score_frame, text='--', 
            font=('Consolas', 12, 'bold'))
        self.total_score_label.pack(side=tk.LEFT, padx=2)
        
        # 细分数显示
        details_frame = ttk.Frame(score_frame)
        details_frame.pack(fill=tk.X, padx=2)
        
        # 创建详细分数标签
        self.trend_score_label = ttk.Label(details_frame, text='趋势: --')
        self.trend_score_label.pack(fill=tk.X, padx=2)
        
        self.momentum_score_label = ttk.Label(details_frame, text='动量: --')
        self.momentum_score_label.pack(fill=tk.X, padx=2)
        
        self.volume_score_label = ttk.Label(details_frame, text='成交量: --')
        self.volume_score_label.pack(fill=tk.X, padx=2)
        
        self.tech_score_label = ttk.Label(details_frame, text='技术指标: --')
        self.tech_score_label.pack(fill=tk.X, padx=2)
        
        # 启动按钮
        self.start_btn = ttk.Button(control_frame, text='启动监控', 
            command=self.start_monitoring, style='Accent.TButton')
        self.start_btn.pack(pady=5, padx=2, fill=tk.X)
        
        # 添加支撑位和压力��显示
        levels_frame = ttk.LabelFrame(control_frame, text='支撑位/压力位', padding=2)
        levels_frame.pack(pady=2, padx=2, fill=tk.X)
        
        ttk.Label(levels_frame, text='支撑位:').pack(side=tk.LEFT, padx=2)
        self.support_label = ttk.Label(levels_frame, textvariable=self.support_level)
        self.support_label.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(levels_frame, text='压力位:').pack(side=tk.LEFT, padx=2)
        self.resistance_label = ttk.Label(levels_frame, textvariable=self.resistance_level)
        self.resistance_label.pack(side=tk.LEFT, padx=2)
        
        # 添加资金管理设置框
        fund_management_frame = ttk.LabelFrame(control_frame, text='资金管理', padding=2)
        fund_management_frame.pack(pady=2, padx=2, fill=tk.X)
        
        ttk.Label(fund_management_frame, text='交易金额:').pack(side=tk.LEFT, padx=2)
        ttk.Entry(fund_management_frame, textvariable=self.trade_amount, width=10).pack(side=tk.LEFT, padx=2)
    
        # 添加预测分析按钮框架
        prediction_frame = ttk.LabelFrame(control_frame, text='预测分析', padding=2)
        prediction_frame.pack(pady=2, padx=2, fill=tk.X)
        
        # 添加手动预测按钮
        predict_btn = ttk.Button(prediction_frame, text='分析交易机会', 
            command=self.manual_predict, style='Accent.TButton')
        predict_btn.pack(pady=5, padx=2, fill=tk.X)
        
        # 添加自动预测阈值设置
        threshold_frame = ttk.Frame(prediction_frame)
        threshold_frame.pack(fill=tk.X, padx=2)
        
        ttk.Label(threshold_frame, text='预警阈值:').pack(side=tk.LEFT, padx=2)
        self.prediction_threshold = ttk.Entry(threshold_frame, width=8)
        self.prediction_threshold.insert(0, '90')  # 默认阈值80%
        self.prediction_threshold.pack(side=tk.LEFT, padx=2)
        ttk.Label(threshold_frame, text='%').pack(side=tk.LEFT)
    
    def manual_predict(self):
        """手动触发预测分析"""
        try:
            symbol = self.symbol_var.get()
            prediction = self.predict_best_entry_exit_multi_timeframe(symbol)
            if prediction:
                self.display_multi_timeframe_prediction(prediction)
        except Exception as e:
            print(f"手动预测错误: {str(e)}")
            messagebox.showerror("错误", f"预测分析失败: {str(e)}")

    def check_signals(self, df):
        """检查信号"""
        try:
            # 获取当前交易对
            symbol = self.symbol_var.get()
            
            # 执行多时间框架分析
            multi_tf_signals = self.analyze_multiple_timeframes(symbol)
            
            # 触发信号
            for signal, timestamp in multi_tf_signals:
                self.trigger_signal(signal, timestamp)
            
            if self.use_ml_model.get() and self.is_model_trained:
                # 使用机器学习模型检查信号
                predictions = self.predict_market_behavior(df)
                if predictions is not None:
                    for i, prediction in enumerate(predictions):
                        if prediction == 1:
                            self.trigger_signal('ML模型预测看涨信号', time.time())
                        elif prediction == 0:
                            self.trigger_signal('ML模型预测看跌信号', time.time())
            
            # 执行预测分析但只在满足阈值时显示
            prediction = self.predict_best_entry_exit_multi_timeframe(symbol)
            if prediction and prediction['signal'] != '观望':  # 只在有明确信号时检查
                try:
                    threshold = float(self.prediction_threshold.get())
                    if prediction['confidence'] >= threshold:
                        # 检查是否已经触发过相同信号
                        current_time = time.time()
                        signal_key = f"{prediction['signal']}_{prediction['confidence']}"
                        
                        # 如果该信号在最近30分钟内没有触发过
                        if (signal_key not in self.last_signal_times or 
                            current_time - self.last_signal_times.get(signal_key, 0) > 1800):
                            
                            # 更新最后触发时间
                            self.last_signal_times[signal_key] = current_time
                            
                            # 添加时间戳到信号
                            signal_time = datetime.now().strftime('%H:%M:%S')
                            signal_text = f"[{signal_time}] {prediction['signal']} "
                            signal_text += f"(信心度: {prediction['confidence']}%)"
                            
                            # 触发信号
                            self.trigger_signal(signal_text, current_time)
                            
                            # 显示预测窗口
                            self.root.after(0, lambda: self.display_multi_timeframe_prediction(prediction))
                except ValueError:
                    print("预警阈值设置无效")
            
            # 使用其他方法检查信号
            self.check_patterns(df)
            self.check_indicators(df)
            
        except Exception as e:
            print(f"信号检查错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def apply_theme(self):
        """应用当前主题"""
        self.colors = self.vscode_theme if self.current_theme.get() == 'VSCode' else self.default_theme
        
        # 配置 ttk 样式
        self.style.configure('TFrame', background=self.colors['bg'])
        self.style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'])
        self.style.configure('TButton', background=self.colors['button_bg'], foreground=self.colors['button_fg'])
        self.style.configure('TCheckbutton', background=self.colors['bg'], foreground=self.colors['fg'])
        self.style.configure('TLabelframe', background=self.colors['bg'], foreground=self.colors['fg'])
        self.style.configure('TLabelframe.Label', background=self.colors['bg'], foreground=self.colors['fg'])
        
        # 更新 matplotlib 图形背景
        if hasattr(self, 'fig') and hasattr(self, 'ax'):
            self.fig.patch.set_facecolor(self.colors['bg'])
            self.ax.set_facecolor(self.colors['bg'])
            if hasattr(self, 'canvas'):
                self.canvas.draw()

    def change_theme(self, event):
        """更改主题"""
        self.apply_theme()
        self.save_config()  # 保存当前主题设置
    
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
        
        # 计算支撑位和压力位
        self.support_level.set(f"{df['low'].min():.2f}")
        self.resistance_level.set(f"{df['high'].max():.2f}")
        
        return df
        
    def check_signals(self, df):
        """检查各种信号"""
        try:
            current_time = time.time()
            
            # 检查金叉死叉
            if self.ma_cross_alert.get():
                if df['MA5'].iloc[-2] <= df['MA10'].iloc[-2] and df['MA5'].iloc[-1] > df['MA10'].iloc[-1]:
                    self.trigger_signal('金叉', current_time)
                elif df['MA5'].iloc[-2] >= df['MA10'].iloc[-2] and df['MA5'].iloc[-1] < df['MA10'].iloc[-1]:
                    self.trigger_signal('死叉', current_time)
            
            # 检查布林带突破
            if self.bollinger_alert.get():
                if df['close'].iloc[-1] > df['upper'].iloc[-1]:
                    self.trigger_signal('突破布林上轨', current_time)
                elif df['close'].iloc[-1] < df['lower'].iloc[-1]:
                    self.trigger_signal('突破布林下轨', current_time)
            
            # 检查价格变动
            if self.price_alert.get():
                monitor_minutes = int(self.monitor_minutes.get())
                threshold = float(self.price_threshold.get())
                
                minutes_ago = df.index[-1] - timedelta(minutes=monitor_minutes)
                old_price = df.loc[df.index >= minutes_ago].iloc[0]['close']
                current_price = df['close'].iloc[-1]
                
                # 价格变动百分
                price_change = ((current_price - old_price) / old_price) * 100
                
                if abs(price_change) >= threshold:
                    direction = "上涨" if price_change > 0 else "下跌"
                    self.trigger_signal(f'价格变动{direction}', current_time)
            
            # 检查成交量异常
            if self.volume_alert.get():
                # 计算成交量的移动平均
                volume_ma = df['volume'].rolling(window=20).mean()
                current_volume = df['volume'].iloc[-1]
                
                # 如果当前成交量超平均的2倍
                if current_volume > volume_ma.iloc[-1] * 2:
                    self.trigger_signal('成交量异常放', current_time)
            
            # 检查趋势突破
            if self.trend_alert.get():
                # 使用20日均线作为趋势线
                ma20 = df['close'].rolling(window=20).mean()
                price = df['close'].iloc[-1]
                prev_price = df['close'].iloc[-2]
                
                if prev_price <= ma20.iloc[-2] and price > ma20.iloc[-1]:
                    self.trigger_signal('向上突破20日均线', current_time)
                elif prev_price >= ma20.iloc[-2] and price < ma20.iloc[-1]:
                    self.trigger_signal('向下突破20日均线', current_time)
            
            # 检查动量背离
            if self.momentum_alert.get():
                # 价格创新高但RSI未创新高，可能��现顶背离
                if (df['close'].iloc[-1] > df['close'].iloc[-2:-6].max() and 
                    df['RSI'].iloc[-1] < df['RSI'].iloc[-2:-6].max()):
                    self.trigger_signal('可能出现顶背离', current_time)
                
                # 价格创新低但RSI未创新低，可能出现底背离
                if (df['close'].iloc[-1] < df['close'].iloc[-2:-6].min() and 
                    df['RSI'].iloc[-1] > df['RSI'].iloc[-2:-6].min()):
                    self.trigger_signal('可能出现底背离', current_time)
            
            # 检查MACD交叉
            if self.macd_cross_alert.get():
                # MACD金叉
                if (df['MACD'].iloc[-2] <= df['Signal'].iloc[-2] and 
                    df['MACD'].iloc[-1] > df['Signal'].iloc[-1]):
                    self.trigger_signal('MACD金叉', current_time)
                
                # MACD死叉
                elif (df['MACD'].iloc[-2] >= df['Signal'].iloc[-2] and 
                      df['MACD'].iloc[-1] < df['Signal'].iloc[-1]):
                    self.trigger_signal('MACD死叉', current_time)
                    
            # 检查经典形态
            self.check_patterns(df)
            
        except Exception as e:
            print(f"策略检查错误: {str(e)}")
    
    def trigger_signal(self, signal_name, current_time):
        """触发信号提醒"""
        # 检查信号是否在5分钟内重复
        last_time = self.last_signal_times.get(signal_name, 0)
        if current_time - last_time >= 300:  # 300秒 = 5分钟
            self.last_signal_times[signal_name] = current_time
            
            # 添加新信号
            new_signal = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {signal_name}"
            self.recent_signals.append(new_signal)
            
            # 限制信号数量
            max_signals = self.max_signals.get()
            if len(self.recent_signals) > max_signals:
                self.recent_signals = self.recent_signals[-max_signals:]
            
            # 更新信号显示
            self.update_signal_display()
            
            # 结合信号评分建议买入或卖出金额
            trade_amount = self.trade_amount.get()
            message = f'{self.symbol_var.get()} {signal_name}！建议交易金额: {trade_amount} USDT'
            # self.root.after(0, lambda: messagebox.showinfo('信号提醒', message))
    
    def update_signal_display(self):
        """更新最近信号显示"""
        # 获取当前交易对和时间周期
        symbol = self.symbol_var.get()
        timeframe = self.timeframe_var.get()
        
        # 更新文本框显示
        self.signal_text.config(state=tk.NORMAL)  # 允许编辑
        self.signal_text.delete('1.0', tk.END)  # 清空当前内容
        
        # 添加交易设置信息和信号数量信息
        header = f"交易对: {symbol}, 周期: {timeframe}\n"
        header += f"保存信号数: {self.max_signals.get()}\n"
        header += "-" * 50 + "\n"
        
        # 添加所有信号
        signal_text = header + '\n'.join(self.recent_signals)
        
        self.signal_text.insert(tk.END, signal_text)
        self.signal_text.config(state=tk.DISABLED)  # 设置为只读
        self.signal_text.see(tk.END)  # 滚动到最后一行
    
    def update_chart(self, df):
        self.fig.clear()
        
        # 创建子图，比例为3:1:1
        gs = self.fig.add_gridspec(3, 1, height_ratios=[3, 1, 1], hspace=0.1)
        ax1 = self.fig.add_subplot(gs[0])  # 主图
        ax2 = self.fig.add_subplot(gs[1], sharex=ax1)  # RSI，共享x轴
        ax3 = self.fig.add_subplot(gs[2], sharex=ax1)  # MACD，共享x轴
        
        # 设置图表式
        for ax in [ax1, ax2, ax3]:
            ax.set_facecolor(self.colors['bg'])
            ax.grid(True, color='#404040', linestyle='--', linewidth=0.5)
            ax.tick_params(colors=self.colors['fg'])
        
        # 绘制主图
        if self.show_price.get():
            ax1.plot(df.index, df['close'], label='价格', color='#569cd6')
        if self.show_ma5.get():
            ax1.plot(df.index, df['MA5'], label='MA5', color='#4ec9b0')
        if self.show_ma10.get():
            ax1.plot(df.index, df['MA10'], label='MA10', color='#ce9178')
        if self.show_bollinger.get():
            ax1.plot(df.index, df['upper'], label='布林上轨', color='#c586c0', linestyle='--')
            ax1.plot(df.index, df['lower'], label='布林下轨', color='#c586c0', linestyle='--')
        
        # 绘制RSI
        if self.show_rsi.get():
            ax2.plot(df.index, df['RSI'], label='RSI', color='#dcdcaa')
            ax2.axhline(y=70, color='#f14c4c', linestyle='--', alpha=0.5)
            ax2.axhline(y=30, color='#23d18b', linestyle='--', alpha=0.5)
            ax2.set_ylim(0, 100)
            ax2.set_ylabel('RSI')
        
        # 绘制MACD
        if self.show_macd.get():
            # 绘制柱状图
            colors = np.where(df['Histogram'] >= 0, '#23d18b', '#f14c4c')
            ax3.bar(df.index, df['Histogram'], color=colors, label='MACD柱状', alpha=0.7, width=0.6)
            # 绘制MACD线和信号线
            ax3.plot(df.index, df['MACD'], label='MACD', color='#569cd6')
            ax3.plot(df.index, df['Signal'], label='Signal', color='#ce9178')
            ax3.set_ylabel('MACD')
        
        # 设置标题和标签
        ax1.set_title(f'{self.symbol_var.get()} {self.timeframe_var.get()}', 
            color=self.colors['fg'])
        
        # 只最底部显示时间轴
        ax1.tick_params(labelbottom=False)  # 隐藏上面两个图的x轴标签
        ax2.tick_params(labelbottom=False)  # 隐藏间的x轴标签
        
        # 调整时间轴式
        ax3.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
        
        # 设置图例
        for ax in [ax1, ax2, ax3]:
            if ax.get_legend():
                ax.get_legend().remove()
            legend = ax.legend(loc='upper left')
            if legend:
                legend.get_frame().set_facecolor(self.colors['bg'])
                for text in legend.get_texts():
                    text.set_color(self.colors['fg'])
        
        self.canvas.draw()

        # 更新支撑位和压力位显示
        self.support_level.set(f"{df['low'].min():.2f}")
        self.resistance_level.set(f"{df['high'].max():.2f}")

    def update_chart_visibility(self):
        """更新图表显示状态"""
        if hasattr(self, 'last_df') and self.last_df is not None:
            self.update_chart(self.last_df)

    def fetch_data(self):
        while self.running:
            try:
                # 确保交易所实例使用最新的代理设置
                self.update_exchange()
                
                # 取K线数据
                ohlcv = self.exchange.fetch_ohlcv(
                    self.symbol_var.get(),
                    self.timeframe_var.get(),
                    limit=100
                )
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # 更新当前价格显示
                current_price = df['close'].iloc[-1]
                self.root.after(0, lambda: self.price_label.config(text=f'{current_price:.2f} USDT'))
                
                # 计算指标
                df = self.calculate_indicators(df)
                self.calculate_strategy_scores(df)
                
                # 检查信号
                self.root.after(0, lambda: self.check_signals(df))
                
                # 保存最新的数据用于图表更新
                self.last_df = df
                
                # 更新图表
                self.root.after(0, lambda: self.update_chart(df))
                
                time.sleep(10)  # 每10秒更新一次
                
            except Exception as e:
                print(f"错误: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("错误", f"获取数据失败: {str(e)}\n请检查网络和代理设置"))
                self.running = False
                self.root.after(0, lambda: self.start_btn.config(text='启动监控'))
                time.sleep(5)  # 出错后等待5秒重试
    
    def start_monitoring(self):
        """启动监控前先测试连接"""
        if not self.running:
            # 尝试连接交易所
            if not self.test_exchange_connection():
                messagebox.showerror("错误", "先配置并试代理设置")
                return
            
            self.running = True
            self.start_btn.config(text='停止监控')
            threading.Thread(target=self.fetch_data, daemon=True).start()
        else:
            self.stop_monitoring()

    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        self.start_btn.config(text='启动监控')
        print("监控已停止")
    
    def run(self):
        """运行程"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"程序异常: {str(e)}")
        finally:
            self.running = False
            self.save_config()  # 保存配置
            if hasattr(self, 'exchange'):
                self.exchange = None
            print("程序已安全退出")
    
    def test_exchange_connection(self):
        """测试交易所连接"""
        try:
            # 更新代理设置
            self.update_exchange()
            
            # 尝试获取服务器时间来测试连接
            self.exchange.load_time_difference()
            return True
        except Exception as e:
            print(f"连接测试失败: {str(e)}")
            return False

    def save_proxy_settings(self):
        """保存并试代理设置"""
        try:
            # 存配置
            self.config['proxy_host'] = self.proxy_host.get()
            self.config['proxy_port'] = self.proxy_port.get()
            self.config['use_proxy'] = self.use_proxy.get()
            self.save_config()
            
            # 测试连接
            if self.test_exchange_connection():
                messagebox.showinfo('成功', '代理设置已保存并测试成功')
            else:
                messagebox.showwarning('警告', '代理设置已保存，但连接测试失败\n请检查代理服务器是否正常运行')
        except Exception as e:
            messagebox.showerror("错误", f"保存代理设置失败: {str(e)}")
    
    def on_closing(self):
        """处理窗口关闭事件"""
        if self.running:
            if messagebox.askokcancel("确认退出", "监控正在行中，确定要退出吗？"):
                self.running = False
                time.sleep(1)  # 给线程一点时间来结束
                self.save_config()  # 保存配置
                self.root.destroy()
        else:
            self.save_config()  # 保存配置
            self.root.destroy()

    def calculate_strategy_scores(self, df):
        """计算各项策略得分"""
        try:
            scores = {}
            
            # 1. 趋势得分 (0-100)
            ma20 = df['close'].rolling(window=20).mean()
            ma50 = df['close'].rolling(window=50).mean()
            current_price = df['close'].iloc[-1]
            
            trend_score = 50  # 基础分
            # 价格在均线上方，加分
            if current_price > ma20.iloc[-1]:
                trend_score += 15
            if current_price > ma50.iloc[-1]:
                trend_score += 15
            # 短期均线在长期均线上方，加分
            if ma20.iloc[-1] > ma50.iloc[-1]:
                trend_score += 20
            
            scores['trend'] = min(100, max(0, trend_score))
            
            # 2. 动量得分 (0-100)
            momentum_score = 50
            
            # RSI指标评分
            rsi = df['RSI'].iloc[-1]
            if 40 <= rsi <= 60:  # 中性
                momentum_score += 10
            elif 30 <= rsi < 40 or 60 < rsi <= 70:  # 轻微超买/超卖
                momentum_score += 20
            elif rsi < 30 or rsi > 70:  # 强烈超买/超卖
                momentum_score += 30
            
            # MACD评分
            if df['MACD'].iloc[-1] > df['Signal'].iloc[-1]:
                momentum_score += 20
            
            scores['momentum'] = min(100, max(0, momentum_score))
            
            # 3. 成交量评分 (0-100)
            volume_score = 50
            volume_ma = df['volume'].rolling(window=20).mean()
            current_volume = df['volume'].iloc[-1]
            
            # 成交量比较
            volume_ratio = current_volume / volume_ma.iloc[-1]
            if volume_ratio > 2:
                volume_score += 30
            elif volume_ratio > 1.5:
                volume_score += 20
            elif volume_ratio > 1:
                volume_score += 10
            
            # 成交量趋势
            if df['volume'].iloc[-3:].mean() > volume_ma.iloc[-3:].mean():
                volume_score += 20
            
            scores['volume'] = min(100, max(0, volume_score))
            
            # 4. 技术指标得分 (0-100)
            tech_score = 50
            
            # 布林带位置
            upper = df['upper'].iloc[-1]
            lower = df['lower'].iloc[-1]
            if lower <= current_price <= upper:
                tech_score += 20
            
            # 均线金叉/死叉
            if df['MA5'].iloc[-1] > df['MA10'].iloc[-1] and \
               df['MA5'].iloc[-2] <= df['MA10'].iloc[-2]:
                tech_score += 30
            
            scores['tech'] = min(100, max(0, tech_score))
            
            # 计算总分 (加权平均)
            weights = {
                'trend': 0.35,
                'momentum': 0.25,
                'volume': 0.2,
                'tech': 0.2
            }
            
            total_score = sum(score * weights[key] for key, score in scores.items())
            scores['total'] = round(total_score, 1)
            
            # 更新界面显示
            self.root.after(0, lambda: self.update_score_display(scores))
            
            return scores
            
        except Exception as e:
            print(f"策略评分计算错误: {str(e)}")
            return None

    def update_score_display(self, scores):
        """更新分数显示"""
        if not scores:
            return
        
        # 更新总分显示
        total_score = scores['total']
        color = '#23d18b' if total_score >= 70 else '#f14c4c' if total_score <= 30 else '#dcdcaa'
        self.total_score_label.config(text=f'{total_score}', foreground=color)
        
        # 更详分数
        self.trend_score_label.config(
            text=f'趋势: {scores["trend"]:.0f}',
            foreground=self.get_score_color(scores["trend"]))
        self.momentum_score_label.config(
            text=f'动量: {scores["momentum"]:.0f}',
            foreground=self.get_score_color(scores["momentum"]))
        self.volume_score_label.config(
            text=f'成交量: {scores["volume"]:.0f}',
            foreground=self.get_score_color(scores["volume"]))
        self.tech_score_label.config(
            text=f'技术指标: {scores["tech"]:.0f}',
            foreground=self.get_score_color(scores["tech"]))

    def get_score_color(self, score):
        """根据分数返回显示颜色"""
        if score >= 70:
            return '#23d18b'  # 绿色
        elif score <= 30:
            return '#f14c4c'  # 红色
        return '#dcdcaa'  # 黄色

    def show_strategy_help(self):
        """显示策略评分说明"""
        help_text = """
策略评分系统说明：

1. 总体评分 (100分制)
- ≥ 70分：强烈看多信号
- ≤ 30分：强烈看空信号
- 30-70分：市场中性或盘整

2. 趋势分 (权重35%)
- 于20日和50日均线
- 价格位于均线上：+15分
- 短期均线在长期均线上方：+20分
- 基础分：50分

3. 动量评分 (权重25%)
- RSI指标：
  * 中性区域(40-60)：+10分
  * 轻微超买/超卖(30-40或60-70)：+20分
  * 强烈超买/超卖(<30或>70)：+30分
- MACD：
  * MACD线在信号线上方：+20分
- 基础分：50分

4. 成交量评分 (权重20%)
- 当前成交量/20平均：
  * >2倍：+30分
  * >1.5倍：+20分
  * >1倍：+10分
- 3日成��量均值上升：+20分
- 基础分：50分

5. 技术指标评分 (权重20%)
- 价格在布林带内：+20分
- 均线金叉：+30分
- 基础分：50分

使用建议：
1. 评分仅供参考，不建议单独作为交易依据
2. 建议结合多个维���综合分析
3. 重点关注分数的变化趋势
4. 极端分数常预示反转机会
5. 配合其他技术指标基本面分析使用
"""
        
        # 创建帮助窗口
        help_window = tk.Toplevel(self.root)
        help_window.title('策略评分说明')
        help_window.geometry('500x600')
        help_window.configure(bg=self.colors['bg'])
        
        # 添加文本框
        text = tk.Text(help_window, 
            wrap=tk.WORD,
            bg=self.colors['bg'],
            fg=self.colors['fg'],
            font=('Microsoft YaHei UI', 10),
            padx=10,
            pady=10)
        text.pack(fill=tk.BOTH, expand=True)
        
        # 插入说明文本
        text.insert('1.0', help_text)
        text.config(state='disabled')  # 设置为只读
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(help_window, orient='vertical', command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscrollcommand=scrollbar.set)
        
        # 窗口置顶
        help_window.transient(self.root)
        help_window.grab_set()
        
        # 添加关闭按钮
        close_button = ttk.Button(help_window, text='关闭', 
            command=help_window.destroy)
        close_button.pack(pady=10)

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
            if self.is_head_and_shoulders_top(highs[-100:]):
                patterns.append(('头肩顶', 'bearish'))
            
            # 头肩底形态判断
            elif self.is_head_and_shoulders_bottom(lows[-100:]):
                patterns.append(('头肩底', 'bullish'))
            
            # 双顶形态判断
            elif self.is_double_top(highs[-50:]):
                patterns.append(('双顶', 'bearish'))
            
            # 双底形态判断
            elif self.is_double_bottom(lows[-50:]):
                patterns.append(('双底', 'bullish'))
            
            # 三角形形态判断（只在没有发现其他形态时检查）
            if not patterns:
                if self.is_ascending_triangle(highs[-50:], lows[-50:]):
                    patterns.append(('上升三角形', 'bullish'))
                elif self.is_descending_triangle(highs[-50:], lows[-50:]):
                    patterns.append(('下降三角形', 'bearish'))
            
        except Exception as e:
            print(f"形态检查错误: {str(e)}")

    def is_head_and_shoulders_top(self, prices, threshold=0.02, min_distance=5):
        """改进的头肩顶形��检测"""
        if len(prices) < 50:
            return False
        
        # 寻找所有峰值
        peaks = []
        for i in range(2, len(prices)-2):
            if prices[i] > prices[i-1] and prices[i] > prices[i-2] and \
               prices[i] > prices[i+1] and prices[i] > prices[i+2]:
                peaks.append((i, prices[i]))
        
        # 确保有足够的峰值
        if len(peaks) < 3:
            return False
        
        # 检查最后的峰值序列
        for i in range(len(peaks)-2):
            left_shoulder = peaks[i]
            head = peaks[i+1]
            right_shoulder = peaks[i+2]
            
            # 检查时间间隔
            if head[0] - left_shoulder[0] < min_distance or \
               right_shoulder[0] - head[0] < min_distance:
                continue
            
            # 检查头部是否高于两肩
            if head[1] > left_shoulder[1] and head[1] > right_shoulder[1]:
                # 检查两肩是否大致相等
                shoulder_diff = abs(left_shoulder[1] - right_shoulder[1])
                if shoulder_diff / left_shoulder[1] < threshold:
                    # 检查颈线是否大致水平
                    neckline_slope = (right_shoulder[1] - left_shoulder[1]) / (right_shoulder[0] - left_shoulder[0])
                    if abs(neckline_slope) < 0.1:  # 允许轻微倾斜
                        return True
        
        return False

    def is_double_top(self, prices, threshold=0.02, min_distance=5, max_distance=30):
        """改进的双顶形态检测"""
        if len(prices) < 30:
            return False
        
        # 寻找峰值
        peaks = []
        for i in range(2, len(prices)-2):
            if prices[i] > prices[i-1] and prices[i] > prices[i-2] and \
               prices[i] > prices[i+1] and prices[i] > prices[i+2]:
                peaks.append((i, prices[i]))
        
        if len(peaks) < 2:
            return False
        
        # 检查最后两个峰值
        for i in range(len(peaks)-1):
            first_peak = peaks[i]
            second_peak = peaks[i+1]
            
            # 检查时间间隔
            peak_distance = second_peak[0] - first_peak[0]
            if min_distance <= peak_distance <= max_distance:
                # 检查峰值是否大致相等
                peak_diff = abs(first_peak[1] - second_peak[1])
                if peak_diff / first_peak[1] < threshold:
                    # 检查中间的谷值
                    valley = min(prices[first_peak[0]:second_peak[0]])
                    if valley < min(first_peak[1], second_peak[1]) * 0.95:
                        return True
        
        return False

    def is_head_and_shoulders_bottom(self, prices, threshold=0.02):
        """头肩底形态检测"""
        if len(prices) < 50:
            return False
        
        # 寻找三个谷值
        valleys = []
        for i in range(2, len(prices)-2):
            if prices[i] < prices[i-1] and prices[i] < prices[i-2] and \
               prices[i] < prices[i+1] and prices[i] < prices[i+2]:
                valleys.append((i, prices[i]))
        
        if len(valleys) < 3:
            return False
        
        # 检查最后三个��值是否符合头肩底形态
        last_valleys = valleys[-3:]
        if len(last_valleys) == 3:
            left_shoulder, head, right_shoulder = last_valleys
            
            # 头部应该低于两肩
            if head[1] < left_shoulder[1] and head[1] < right_shoulder[1]:
                # 两肩应该大致相等
                shoulder_diff = abs(left_shoulder[1] - right_shoulder[1])
                if shoulder_diff / left_shoulder[1] < threshold:
                    return True
        
        return False

    def is_double_bottom(self, prices, threshold=0.02):
        """双底形态检测"""
        if len(prices) < 30:
            return False
        
        # 寻找谷值
        valleys = []
        for i in range(2, len(prices)-2):
            if prices[i] < prices[i-1] and prices[i] < prices[i-2] and \
               prices[i] < prices[i+1] and prices[i] < prices[i+2]:
                valleys.append((i, prices[i]))
        
        if len(valleys) < 2:
            return False
        
        # 检查最后两个���值
        last_valleys = valleys[-2:]
        if len(last_valleys) == 2:
            first_valley, second_valley = last_valleys
            
            # 两个谷值应该大致相等
            valley_diff = abs(first_valley[1] - second_valley[1])
            if valley_diff / first_valley[1] < threshold:
                # 两个谷值之间应该有足够的距离
                if 5 <= second_valley[0] - first_valley[0] <= 30:
                    return True
        
        return False

    def is_ascending_triangle(self, highs, lows, threshold=0.02):
        """上升三角形形态检测"""
        if len(highs) < 20 or len(lows) < 20:
            return False
        
        # 检查最高点是否形成水平线
        high_diff = abs(highs[-1] - highs[-10])
        if high_diff / highs[-1] > threshold:
            return False
        
        # 检查最低��是否形成上升趋势
        low_slope = (lows[-1] - lows[-10]) / 10
        if low_slope <= 0:
            return False
        
        return True

    def is_descending_triangle(self, highs, lows, threshold=0.02):
        """下降三角形形态检测"""
        if len(highs) < 20 or len(lows) < 20:
            return False
        
        # 检查最低点是否形成水平线
        low_diff = abs(lows[-1] - lows[-10])
        if low_diff / lows[-1] > threshold:
            return False
        
        # 检查最高点是否形成下降趋势
        high_slope = (highs[-1] - highs[-10]) / 10
        if high_slope >= 0:
            return False
        
        return True

    def show_settings_window(self):
        """显示设置窗口"""
        # 创建设置窗口
        settings_window = tk.Toplevel(self.root)
        settings_window.title('设置')
        settings_window.geometry('400x500')
        settings_window.transient(self.root)  # 设置为主窗口的子窗口
        settings_window.grab_set()  # 模态窗口
        
        # 使用当前主题
        settings_window.configure(bg=self.colors['bg'])
        
        # 创建设置框架
        main_frame = ttk.Frame(settings_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 代理设置
        proxy_frame = ttk.LabelFrame(main_frame, text='代理设置', padding=5)
        proxy_frame.pack(fill=tk.X, pady=5)
        
        # 代理启用复选框
        ttk.Checkbutton(proxy_frame, text='启用代理', 
            variable=self.use_proxy).pack(padx=5, pady=2)
        
        # 代理地址设置
        proxy_host_frame = ttk.Frame(proxy_frame)
        proxy_host_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(proxy_host_frame, text='地址:').pack(side=tk.LEFT)
        ttk.Entry(proxy_host_frame, textvariable=self.proxy_host).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 代���端口���置
        proxy_port_frame = ttk.Frame(proxy_frame)
        proxy_port_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(proxy_port_frame, text='端口:').pack(side=tk.LEFT)
        ttk.Entry(proxy_port_frame, textvariable=self.proxy_port).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 主题设置
        theme_frame = ttk.LabelFrame(main_frame, text='界面主题', padding=5)
        theme_frame.pack(fill=tk.X, pady=5)
        
        theme_inner_frame = ttk.Frame(theme_frame)
        theme_inner_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(theme_inner_frame, text='主题:').pack(side=tk.LEFT)
        theme_cb = ttk.Combobox(theme_inner_frame, textvariable=self.current_theme,
            values=['VSCode', 'Default'], width=15)
        theme_cb.pack(side=tk.LEFT, padx=5)
        theme_cb.bind('<<ComboboxSelected>>', self.change_theme)
        
        # 信号设置
        signal_frame = ttk.LabelFrame(main_frame, text='信号设置', padding=5)
        signal_frame.pack(fill=tk.X, pady=5)
        
        signal_inner_frame = ttk.Frame(signal_frame)
        signal_inner_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(signal_inner_frame, text='保存信号数量:').pack(side=tk.LEFT)
        ttk.Entry(signal_inner_frame, textvariable=self.max_signals, width=10).pack(side=tk.LEFT, padx=5)
        
        # 机器学习模型设置
        ml_frame = ttk.LabelFrame(main_frame, text='机器学习模型设置', padding=5)
        ml_frame.pack(fill=tk.X, pady=5)
        
        # 机器学习模型启用复选框
        ttk.Checkbutton(ml_frame, text='启用机器学习模型', 
            variable=self.use_ml_model).pack(padx=5, pady=2)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 保存按钮
        save_button = ttk.Button(button_frame, text='保存设置',
            command=lambda: self.save_settings(settings_window))
        save_button.pack(side=tk.RIGHT, padx=5)
        
        # 取消按钮
        cancel_button = ttk.Button(button_frame, text='取消',
            command=settings_window.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # 资金管理设置
        fund_management_frame = ttk.LabelFrame(main_frame, text='资金管理', padding=5)
        fund_management_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(fund_management_frame, text='交易金额:').pack(side=tk.LEFT, padx=5)
        ttk.Entry(fund_management_frame, textvariable=self.trade_amount, width=10).pack(side=tk.LEFT, padx=5)
    
    def save_settings(self, settings_window=None):
        """保存设置"""
        try:
            # 验证代理端口
            if self.use_proxy.get():
                try:
                    port = int(self.proxy_port.get())
                    if port < 0 or port > 65535:
                        raise ValueError
                except ValueError:
                    messagebox.showerror('错误', '代理端口必须是0-65535之间的数字')
                    return
            
            # 验证信号数量
            try:
                signals = int(self.max_signals.get())
                if signals < 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror('错误', '信号数量必须是正整数')
                return
            
            # 保存设置
            self.save_config()
            
            # 更新代理
            self.update_exchange()
            
            # 更新主题
            self.apply_theme()
            
            # 更新信号显示
            self.update_signal_display()
            
            # 保存机器学习模型启用状态
            config = {
                'use_ml_model': self.use_ml_model.get(),
                # 其他配置项...
            }
            
            with open('config.json', 'w') as f:
                json.dump(config, f)
            
            if settings_window:
                settings_window.destroy()
            
            print("设置已保�����")
        
        except Exception as e:
            print(f"保存设置时出错：{str(e)}")

    def load_settings(self):
        """加载设置"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:  # 指定编码为utf-8
                config = json.load(f)
            
            # 加载机器学习模型启用状态
            self.use_ml_model.set(config.get('use_ml_model', True))
            # 加载其他配置项...
            
            print("设置已加载")
        
        except FileNotFoundError:
            print("配置文件未找到，使用默认设置")
        except Exception as e:
            print(f"加载设置时出错：{str(e)}")

    def show_signal_menu(self, event):
        """显示右键菜单"""
        try:
            self.signal_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.signal_menu.grab_release()

    def clear_signals(self):
        """清空最近信号"""
        self.recent_signals.clear()
        self.update_signal_display()
        self.save_config()  # 保存配置以更新信号记录

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
                    df = self.fetch_ohlcv_data(symbol, tf)
                    if df is None or len(df) < 50:
                        continue
                    
                    # 分析趋势
                    trend = self.analyze_trend(df)
                    group_trends.append((tf, trend))
                    
                    # 分析形态
                    pattern = self.analyze_patterns(df)
                    if pattern:
                        group_patterns.append((tf, pattern))
                
                trends[f"{timeframes[0]}-{timeframes[-1]}"] = group_trends
                patterns[f"{timeframes[0]}-{timeframes[-1]}"] = group_patterns
            
            return self.generate_multi_timeframe_signals(trends, patterns)
        
        except Exception as e:
            print(f"多时间框架分析错误: {str(e)}")
            return []

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
            rsi = self.calculate_rsi(closes)[-1]
            
            # 3. 计算MACD
            macd, signal, hist = self.calculate_macd(closes)
            
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

    def analyze_patterns(self, df):
        """分析单一时间框架的形态"""
        patterns = []
        highs = df['high'].values
        lows = df['low'].values
        
        # 检查各种形态
        if self.is_head_and_shoulders_top(highs):
            patterns.append(('头肩顶', 'bearish'))
        elif self.is_head_and_shoulders_bottom(lows):
            patterns.append(('头肩底', 'bullish'))
        elif self.is_double_top(highs):
            patterns.append(('双顶', 'bearish'))
        elif self.is_double_bottom(lows):
            patterns.append(('双底', 'bullish'))
        
        return patterns

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
            
            # 检查形态确认
            group_patterns = patterns[timeframe_group]
            if group_patterns:
                pattern_directions = [p[1] for tf, plist in group_patterns for p in plist]
                if len(pattern_directions) >= 2:
                    if all(d == 'bullish' for d in pattern_directions):
                        signal = f"{timeframe_group}时间框架形态确认看涨"
                        signals.append((signal, current_time))
                    elif all(d == 'bearish' for d in pattern_directions):
                        signal = f"{timeframe_group}时间框架形态确认看跌"
                        signals.append((signal, current_time))
        
        return signals

    def check_signals(self, df):
        """检查信号"""
        try:
            # 获取当前交易对
            symbol = self.symbol_var.get()
            
            # 执行多时间框架分析
            multi_tf_signals = self.analyze_multiple_timeframes(symbol)
            
            # 触发信号
            for signal, timestamp in multi_tf_signals:
                self.trigger_signal(signal, timestamp)
            
            if self.use_ml_model.get() and self.is_model_trained:
                # 使用机器学习模型检查信号
                predictions = self.predict_market_behavior(df)
                if predictions is not None:
                    for i, prediction in enumerate(predictions):
                        if prediction == 1:
                            self.trigger_signal('ML模型预测看涨信号', time.time())
                        elif prediction == 0:
                            self.trigger_signal('ML模型预测看跌信号', time.time())
            
            # 执行预测分析但只在满足阈值时显示
            prediction = self.predict_best_entry_exit_multi_timeframe(symbol)
            if prediction and prediction['signal'] != '观望':  # 只在有明确信号时检查
                try:
                    threshold = float(self.prediction_threshold.get())
                    if prediction['confidence'] >= threshold:
                        # 检查是否已经触发过相同信号
                        current_time = time.time()
                        signal_key = f"{prediction['signal']}_{prediction['confidence']}"
                        
                        # 如果该信号在最近30分钟内没有触发过
                        if (signal_key not in self.last_signal_times or 
                            current_time - self.last_signal_times.get(signal_key, 0) > 1800):
                            
                            # 更新最后触发时间
                            self.last_signal_times[signal_key] = current_time
                            
                            # 添加时间戳到信号
                            signal_time = datetime.now().strftime('%H:%M:%S')
                            signal_text = f"[{signal_time}] {prediction['signal']} "
                            signal_text += f"(信心度: {prediction['confidence']}%)"
                            
                            # 触发信号
                            self.trigger_signal(signal_text, current_time)
                            
                            # 显示预测窗口
                            self.root.after(0, lambda: self.display_multi_timeframe_prediction(prediction))
                except ValueError:
                    print("预警阈值设置无效")
            
            # 使用其他方法检查信号
            self.check_patterns(df)
            self.check_indicators(df)
            
        except Exception as e:
            print(f"信号检查错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def fetch_ohlcv_data(self, symbol, timeframe, start_date=None, end_date=None):
        """
        获取K线数据并进行预处理
        
        Args:
            symbol (str): 交易对
            timeframe (str): 时间周期
            start_date (str, optional): 开始日期，格式 'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式 'YYYY-MM-DD'
        """
        try:
            # 如果提供了日期范围，转换为时间戳
            if start_date and end_date:
                start_timestamp = int(pd.Timestamp(start_date).timestamp() * 1000)
                end_timestamp = int(pd.Timestamp(end_date).timestamp() * 1000)
                
                # 获取指定日期范围的K线数据
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol, 
                    timeframe, 
                    since=start_timestamp,
                    limit=1000  # 增加限制以获取更多数据
                )
                
                # 过滤结束日期
                ohlcv = [candle for candle in ohlcv if candle[0] <= end_timestamp]
            else:
                # 如果没有提供日期范围，获取最近的数据
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            
            # 创建DataFrame并设置正确的时间索引
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"获取{timeframe}数据错误: {str(e)}")
            return None

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
            
            # 检查布林带突破[
            if closes[-1] > upper_band[-1]:
                self.trigger_signal('价格突破布林带上轨，可能回调', time.time())
            elif closes[-1] < lower_band[-1]:
                self.trigger_signal('价格跌破布林带下轨，可能反弹', time.time())
            
            # 检查RSI超买超卖
            if rsi[-1] > overbought_threshold:
                self.trigger_signal(f'RSI超买（>{overbought_threshold}），可能回调', time.time())
            elif rsi[-1] < oversold_threshold:
                self.trigger_signal(f'RSI超卖（<{oversold_threshold}），可能反弹', time.time())
            
            # 检查OBV趋势
            if obv > 0:
                self.trigger_signal('OBV上升，可能看涨', time.time())
            elif obv < 0:
                self.trigger_signal('OBV下降，可能看跌', time.time())
            
            # 检查蜡烛图形态
            self.check_candlestick_patterns(df)
        
        except Exception as e:
            print(f"技术指标检查错误: {str(e)}")

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

    def check_candlestick_patterns(self, df):
        """检查蜡烛图形态"""
        try:
            opens = df['open'].values
            closes = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            
            # 检查锤子线
            if self.is_hammer(opens, closes, highs, lows):
                self.trigger_signal('检测到锤子线，可能反转', time.time())
            
            # 检查吞没形态
            if self.is_engulfing(opens, closes):
                self.trigger_signal('检测到吞没形态，可能反转', time.time())
        
        except Exception as e:
            print(f"蜡烛图形态检查错误: {str(e)}")

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
            
            return {
                'predictions': predictions,
                'probabilities': probabilities
            }
            
        except Exception as e:
            print(f"预测错误: {str(e)}")
            return None

    def fetch_and_save_historical_data(self, symbol, timeframe, since, filename):
        """抓取并保存历史数据"""
        try:
            # 使用ccxt库从交易所获取数据
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since)
            # 将数据转换为DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 保存数据到CSV文件
            df.to_csv(filename, index=False)
            print(f"数据已保存到 {filename}")
        except Exception as e:
            print(f"抓取历史数据错误: {str(e)}")

    def load_historical_data(self, filename):
        """加载历史数据"""
        try:
            if os.path.exists(filename):
                df = pd.read_csv(filename)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            else:
                print(f"文件 {filename} 不存在")
                return None
        except Exception as e:
            print(f"加载历史数据错误: {str(e)}")
            return None

    def train_model_from_file(self, filename):
        """从文件中加载数据并训练模型"""
        df = self.load_historical_data(filename)
        if df is not None:
            self.train_model(df)
        else:
            print("无法加载数据进行训练")

    def show_training_window(self):
        """显示训练模型窗口"""
        # 创建训练窗口
        training_window = tk.Toplevel(self.root)
        training_window.title('训练模型')
        training_window.geometry('300x300')
        training_window.transient(self.root)
        training_window.grab_set()
        
        # 使用当前主题
        training_window.configure(bg=self.colors['bg'])
        
        # 添加日期选择
        ttk.Label(training_window, text='开始日期:').pack(pady=5)
        DateEntry(training_window, textvariable=self.start_date, date_pattern='yyyy-mm-dd').pack(pady=5)
        
        ttk.Label(training_window, text='结束日期:').pack(pady=5)
        DateEntry(training_window, textvariable=self.end_date, date_pattern='yyyy-mm-dd').pack(pady=5)
        
        # 添加训练按钮
        train_button = ttk.Button(training_window, text='开始训练', command=self.start_training)
        train_button.pack(pady=20)
        
        # 添加关闭按钮
        close_button = ttk.Button(training_window, text='关闭', command=training_window.destroy)
        close_button.pack(pady=10)

    def start_training(self):
        """开始训练模型"""
        # 获取用户选择的日期范围
        start_date = self.start_date.get()
        end_date = self.end_date.get()
        
        # 获取历史数据
        df = self.fetch_ohlcv_data(self.symbol_var.get(), '1h', start_date, end_date)
        print(len(df))
        if df is not None and len(df) > 50:
            self.train_model(df)
        else:
            print("数据不足，无法训练模型")

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

    def get_available_symbols(self):
        """获取可用的交易对列表"""
        # 这里可以从交易所API获取可用的交易对列表
        return ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']  # 示例

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
                    df = self.fetch_ohlcv_data(symbol, tf)
                    if df is None or len(df) < 50:
                        continue
                    
                    # 计算技术指标
                    closes = df['close'].values
                    volumes = df['volume'].values
                    current_price = closes[-1]
                    
                    # RSI
                    rsi = self.calculate_rsi(closes)
                    
                    # MACD
                    macd, signal, hist = self.calculate_macd(closes)
                    
                    # 布林带
                    ma, upper_band, lower_band = self.calculate_bollinger_bands(closes)
                    
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
                        if self.is_head_and_shoulders_top(df['high'].values):
                            patterns.append(('头肩顶', -2))
                        if self.is_head_and_shoulders_bottom(df['low'].values):
                            patterns.append(('头肩底', 2))
                        if self.is_double_top(df['high'].values):
                            patterns.append(('双顶', -2))
                        if self.is_double_bottom(df['low'].values):
                            patterns.append(('双底', 2))
                    else:
                        patterns.append(('形态分析不足', 0))
                    
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
                    timeframe_analysis[period]['patterns'].extend(patterns)
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
            current_price = self.get_current_price(symbol)
            
            # 根据综合得分生成信号
            if total_score > 3:
                prediction['signal'] = '强烈看多'
                prediction['price_targets'] = {
                    'entry': current_price,
                    'target': current_price * 1.03,  # 3%获利目标
                    'stop_loss': current_price * 0.99  # 1%止损位
                }
            elif total_score > 1:
                prediction['signal'] = '看多'
                prediction['price_targets'] = {
                    'entry': current_price,
                    'target': current_price * 1.02,
                    'stop_loss': current_price * 0.99
                }
            elif total_score < -3:
                prediction['signal'] = '强烈看空'
                prediction['price_targets'] = {
                    'entry': current_price,
                    'target': current_price * 0.97,
                    'stop_loss': current_price * 1.01
                }
            elif total_score < -1:
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

    def display_multi_timeframe_prediction(self, prediction):
        """显示多时间维度预测结果"""
        if prediction is None:
            return
            
        # 创建预测结果窗口
        pred_window = tk.Toplevel(self.root)
        pred_window.title('多时间维度交易预测分析')
        pred_window.geometry('600x900')
        
        # 使用当前主题
        pred_window.configure(bg=self.colors['bg'])
        
        # 创建主框架
        main_frame = ttk.Frame(pred_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 显示主要信号
        signal_frame = ttk.LabelFrame(main_frame, text='交易信号')
        signal_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(signal_frame, text=f"综合信号: {prediction['signal']}", 
            font=('Microsoft YaHei UI', 12, 'bold')).pack(pady=5)
        ttk.Label(signal_frame, text=f"信心指数: {prediction['confidence']}%").pack()
        ttk.Label(signal_frame, text=f"风险等级: {prediction['risk_level']}").pack()
        
        # 显示目标价位
        if prediction['signal'] != '观望':
            price_frame = ttk.LabelFrame(main_frame, text='价格目标')
            price_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(price_frame, text=f"入场价: {prediction['price_targets']['entry']:.2f}").pack()
            ttk.Label(price_frame, text=f"目标价: {prediction['price_targets']['target']:.2f}").pack()
            ttk.Label(price_frame, text=f"止损价: {prediction['price_targets']['stop_loss']:.2f}").pack()
        
        # 显示时间维度分析
        timeframe_frame = ttk.LabelFrame(main_frame, text='时间维度分析')
        timeframe_frame.pack(fill=tk.X, pady=5)
        
        for period, analysis in prediction['timeframe_analysis'].items():
            period_name = {'short': '短期', 'medium': '中期', 'long': '长期'}[period]
            ttk.Label(timeframe_frame, text=f"\n{period_name}分析:", 
                font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor='w')
            ttk.Label(timeframe_frame, text=f"得分: {analysis['score']}").pack(anchor='w')
            
            # 显示各时间框架的信号
            for signal in analysis['signals']:
                signal_text = f"• {signal['timeframe']}: "
                signal_text += f"MACD {signal['macd_signal']}, "
                signal_text += f"价格在均线{'上方' if signal['price_vs_ma'] == 'above' else '下方'}, "
                signal_text += f"成交量{'放大' if signal['volume_signal'] == 'high' else '正常'}"
                ttk.Label(timeframe_frame, text=signal_text).pack(anchor='w')
        
        # 显示分析理由
        reasons_frame = ttk.LabelFrame(main_frame, text='详细分析理由')
        reasons_frame.pack(fill=tk.X, pady=5)
        
        for reason in prediction['reasons']:
            ttk.Label(reasons_frame, text=f"• {reason}").pack(anchor='w')

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


if __name__ == '__main__':
    app = CryptoMonitor()
    app.run()


