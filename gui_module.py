import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class CryptoMonitorGUI:
    def __init__(self, config, start_callback, stop_callback, on_closing):
        self.root = tk.Tk()
        self.config = config
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.on_closing = on_closing
        self.setup_ui()

    def setup_ui(self):
        # 设置界面
        self.root.title('加密货币监控系统')
        self.root.geometry('1200x800')
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建左侧控制面板
        self.control_frame = ttk.LabelFrame(self.main_frame, text='控制面板')
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # 添加启动和停止按钮
        self.start_button = ttk.Button(self.control_frame, text="启动监控", 
                                     command=self.start_callback)
        self.start_button.pack(pady=5)

        self.stop_button = ttk.Button(self.control_frame, text="停止监控", 
                                    command=self.stop_callback)
        self.stop_button.pack(pady=5)

        # 创建预测点位显示区域
        self.prediction_frame = ttk.LabelFrame(self.control_frame, text='预测点位')
        self.prediction_frame.pack(fill=tk.X, padx=5, pady=5)

        # 看多点位
        self.bullish_frame = ttk.Frame(self.prediction_frame)
        self.bullish_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(self.bullish_frame, text="看多点位:").pack(side=tk.LEFT)
        self.bullish_label = ttk.Label(self.bullish_frame, text="--")
        self.bullish_label.pack(side=tk.LEFT, padx=5)
        self.bullish_confidence = ttk.Label(self.bullish_frame, text="信心度: --")
        self.bullish_confidence.pack(side=tk.RIGHT)

        # 看空点位
        self.bearish_frame = ttk.Frame(self.prediction_frame)
        self.bearish_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(self.bearish_frame, text="看空点位:").pack(side=tk.LEFT)
        self.bearish_label = ttk.Label(self.bearish_frame, text="--")
        self.bearish_label.pack(side=tk.LEFT, padx=5)
        self.bearish_confidence = ttk.Label(self.bearish_frame, text="信心度: --")
        self.bearish_confidence.pack(side=tk.RIGHT)

        # 创建图表区域
        self.chart_frame = ttk.LabelFrame(self.main_frame, text='价格图表')
        self.chart_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建matplotlib图表
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_signals(self, signals):
        """更新预测点位显示"""
        for signal in signals:
            if signal['type'] == 'bullish':
                self.bullish_label.config(text=f"{signal['price']:.2f}")
                self.bullish_confidence.config(text=f"信心度: {signal['confidence']}%")
            elif signal['type'] == 'bearish':
                self.bearish_label.config(text=f"{signal['price']:.2f}")
                self.bearish_confidence.config(text=f"信心度: {signal['confidence']}%")

    def update_chart(self, df):
        """更新图表"""
        self.ax.clear()
        
        # 绘制价格线
        self.ax.plot(df.index, df['close'], label='价格')
        
        # 绘制移动平均线
        if 'MA20' in df.columns:
            self.ax.plot(df.index, df['MA20'], label='MA20')
        if 'MA50' in df.columns:
            self.ax.plot(df.index, df['MA50'], label='MA50')
            
        # 设置图表格式
        self.ax.set_title('价格走势图')
        self.ax.set_xlabel('时间')
        self.ax.set_ylabel('价格')
        self.ax.legend()
        self.ax.grid(True)
        
        # 自动旋转日期标签
        plt.xticks(rotation=45)
        
        # 调整布局
        self.fig.tight_layout()
        
        # 更新画布
        self.canvas.draw()

    def show_error(self, message):
        messagebox.showerror("错误", message)

    def run(self):
        self.root.mainloop()

    def close(self):
        self.root.destroy() 