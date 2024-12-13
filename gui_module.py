import tkinter as tk
from tkinter import messagebox

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

        # 添加启动和停止按钮
        self.start_button = tk.Button(self.root, text="启动监控", command=self.start_callback)
        self.start_button.pack()

        self.stop_button = tk.Button(self.root, text="停止监控", command=self.stop_callback)
        self.stop_button.pack()

    def update_signals(self, signals):
        # 更新信号显示
        print("更新信号:", signals)

    def update_chart(self, df):
        # 更新图表
        print("更新图表")

    def show_error(self, message):
        messagebox.showerror("错误", message)

    def run(self):
        self.root.mainloop()

    def close(self):
        self.root.destroy() 