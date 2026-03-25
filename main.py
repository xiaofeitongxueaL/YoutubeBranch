import customtkinter as ctk
import threading, re, os, requests
from tkinter import filedialog, messagebox # 增加导入 messagebox
# 1. 导入解耦后的核心模块
from config_manager import ConfigManager
from download_engine import DownloaderEngine

# 设置主题
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# 日志桥接器：负责把引擎的输出传给 UI 文本框
class MyLogger:
    def __init__(self, textbox):
        self.textbox = textbox
    def write(self, msg):
        clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', msg) # 清除 ANSI 颜色代码
        self.textbox.after(0, lambda: self.textbox.insert("end", clean_msg + "\n"))
        self.textbox.after(0, lambda: self.textbox.see("end"))
    def debug(self, msg): self.write(msg)
    def warning(self, msg): self.write(f"⚠️ {msg}")
    def error(self, msg): self.write(f"🚨 {msg}")

class YouTubeDownloaderPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cm = ConfigManager()
        self.conf = self.cm.config

        # --- 确保所有 UI 变量全部在这里定义 ---
        self.download_path_var = ctk.StringVar(value=self.conf.get('last_path', ""))
        self.proxy_addr_var = ctk.StringVar(value=self.conf.get('last_proxy', "http://127.0.0.1:7890"))
        
        self.proxy_enabled_var = ctk.BooleanVar(value=self.conf.get('proxy_enabled', False))
        self.sub_var = ctk.BooleanVar(value=self.conf.get('sub', False))
        self.audio_var = ctk.BooleanVar(value=self.conf.get('audio', False))
        self.thumb_var = ctk.BooleanVar(value=self.conf.get('thumb', False))
        self.shutdown_var = ctk.BooleanVar(value=self.conf.get('shutdown', False))
        self.auto_paste_var = ctk.BooleanVar(value=self.conf.get('auto_paste', False))
        
        self.quality_var = ctk.StringVar(value=self.conf.get('quality', "最高画质"))
        self.cookie_var = ctk.StringVar(value=self.conf.get('cookie_browser', "无"))
        # --------------------------------------

        self.title("YouTube 全能爬虫 Pro v4.5")
        self.geometry("750x920") 
        self.grid_columnconfigure(0, weight=1)
        
        self.setup_ui()  # 现在执行这行，绝对不会报错了
        
        # 3. 初始化下载引擎 (注意：必须在 setup_ui 之后，因为需要 log_box)
        self.engine = DownloaderEngine(
            ffmpeg_path=self.cm.ffmpeg_bin,
            logger=MyLogger(self.log_box),
            progress_hook=self.update_ui_status
        )

        # 启动在线公告检查
        threading.Thread(target=self.check_online_info, daemon=True).start()

        self.monitor_clipboard() # 开启循环监听

    def setup_ui(self):
        """负责所有的 UI 布局代码"""
        self.msg_label = ctk.CTkLabel(self, text="正在同步在线公告...", text_color="gray")
        self.msg_label.grid(row=0, column=0, pady=(10, 0))

        self.label = ctk.CTkLabel(self, text="YouTube 全能爬虫系统", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=1, column=0, padx=20, pady=(10, 10))

        # 批量输入
        self.url_text = ctk.CTkTextbox(self, width=680, height=100)
        self.url_text.grid(row=2, column=0, padx=20, pady=5)
        
        # 路径选择
        self.path_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.path_frame.grid(row=3, column=0, padx=20, pady=5)
        self.download_path_var = ctk.StringVar(value=self.conf['last_path']) 
        ctk.CTkEntry(self.path_frame, width=470, textvariable=self.download_path_var).pack(side="left", padx=(0, 10))
        ctk.CTkButton(self.path_frame, text="📁 选路径", width=80, command=self.select_path, fg_color="#34495e").pack(side="left", padx=2)
        ctk.CTkButton(self.path_frame, text="📂 打开", width=80, command=self.open_folder, fg_color="#2c3e50").pack(side="left", padx=2)

        # 代理区
        self.proxy_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.proxy_frame.grid(row=4, column=0, padx=20, pady=5)
        self.proxy_enabled_var = ctk.BooleanVar(value=self.conf.get('proxy_enabled', False))
        ctk.CTkSwitch(self.proxy_frame, text="启用代理", variable=self.proxy_enabled_var, command=self.toggle_proxy).pack(side="left", padx=5)
        self.proxy_addr_var = ctk.StringVar(value=self.conf['last_proxy'])
        self.proxy_entry = ctk.CTkEntry(self.proxy_frame, width=450, textvariable=self.proxy_addr_var)
        self.proxy_entry.pack(side="left", padx=5)
        self.toggle_proxy()

        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.grid(row=5, column=0, padx=20, pady=10)

        # 第一行：使用局部变量 row1，不需要 self.row1
        row1 = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkSwitch(row1, text="内嵌字幕", variable=self.sub_var).pack(side="left", padx=10)
        ctk.CTkSwitch(row1, text="仅音频", variable=self.audio_var).pack(side="left", padx=10)
        ctk.CTkSwitch(row1, text="保存封面", variable=self.thumb_var).pack(side="left", padx=10)
        ctk.CTkSwitch(row1, text="任务完关机", variable=self.shutdown_var).pack(side="left", padx=10)

        # 第二行：使用局部变量 row2，不需要 self.row2
        row2 = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkSwitch(row2, text="自动识别链接", variable=self.auto_paste_var, progress_color="cyan").pack(side="left", padx=10)
        
        ctk.CTkLabel(row2, text="画质:").pack(side="left", padx=(10, 2))
        ctk.CTkOptionMenu(row2, values=["最高画质", "2160p (4K)", "1080p", "720p"], variable=self.quality_var, width=100).pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="Cookie:").pack(side="left", padx=(10, 2))
        ctk.CTkOptionMenu(row2, values=["无", "chrome", "edge", "firefox"], variable=self.cookie_var, width=100).pack(side="left", padx=5)

        # 下载按钮
        self.download_btn = ctk.CTkButton(self, text="🚀 开启全能爬取模式", height=50, command=self.start_batch_download, font=ctk.CTkFont(size=18, weight="bold"))
        self.download_btn.grid(row=6, column=0, padx=20, pady=20)

        # 进度显示
        self.status_label = ctk.CTkLabel(self, text="准备就绪", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label.grid(row=7, column=0)
        self.log_box = ctk.CTkTextbox(self, width=680, height=200, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.grid(row=8, column=0, padx=20, pady=10)

        # --- 新增：免责声明标签 (放在 row=9) ---
        disclaimer_text = (
            "免责声明：本工具仅供编程学习与个人测试使用。请遵守当地法律法规及 YouTube 服务条款，\n"
            "严禁将下载内容用于未经授权的分发、商业盈利或传播至第三方平台。使用者因违规使用产生的任何法律责任由其自行承担。"
        )
        self.disclaimer_label = ctk.CTkLabel(
            self, 
            text=disclaimer_text, 
            font=ctk.CTkFont(size=10), # 小字号
            text_color="gray",         # 灰色，不显眼
            justify="center"           # 居中显示
        )
        self.disclaimer_label.grid(row=9, column=0, padx=20, pady=(5, 15)) # 放在最底部，留出一点边距

    def show_custom_notification(self, title, message):
        """创建一个独立的、置顶的自定义通知窗口"""
        # 创建顶层窗口
        top = ctk.CTkToplevel(self)
        top.title(title)
        top.geometry("400x200")
        
        # --- 核心需求：窗口置顶 ---
        top.attributes("-topmost", True)
        top.focus_force() # 强制获取焦点
        
        # 居中显示（相对于主窗口）
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 100
        top.geometry(f"+{x}+{y}")

        # 窗口布局
        label = ctk.CTkLabel(top, text="🎊", font=ctk.CTkFont(size=40))
        label.pack(pady=(20, 10))
        
        msg_label = ctk.CTkLabel(top, text=message, font=ctk.CTkFont(size=14, weight="bold"))
        msg_label.pack(pady=10)

        close_btn = ctk.CTkButton(top, text="我知道了", width=100, command=top.destroy)
        close_btn.pack(pady=(10, 20))

        top.after(5000, top.destroy)
    
    def monitor_clipboard(self):
        """极速监测剪贴板：只填入链接，不请求网络"""
        if self.auto_paste_var.get():
            try:
                clip_text = self.clipboard_get().strip()
                yt_pattern = r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[a-zA-Z0-9_-]{11}"
            
                if re.match(yt_pattern, clip_text):
                    current_text = self.url_text.get("0.0", "end").strip()
                    if clip_text not in current_text:
                        self.url_text.insert("end", clip_text + "\n")
                        self.status_label.configure(text="📋 已自动添加链接，准备下载", text_color="cyan")
                        self.after(3000, lambda: self.status_label.configure(text="准备就绪", text_color="white"))
            except Exception:
                pass
        self.after(1500, self.monitor_clipboard)        
    # --- UI 事件方法 ---
    def toggle_proxy(self):
        self.proxy_entry.configure(state="normal" if self.proxy_enabled_var.get() else "disabled")

    def select_path(self):
        folder = filedialog.askdirectory()
        if folder: self.download_path_var.set(folder)

    def open_folder(self):
        path = self.download_path_var.get()
        if os.path.exists(path): os.startfile(path)

    def check_online_info(self):
        try:
            url = "https://raw.githubusercontent.com/xiaofeitongxueaL/YoutubeDownload/refs/heads/main/info.json"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                self.after(0, lambda: self.msg_label.configure(text=data.get("notice", ""), text_color="cyan"))
        except: pass

    def update_ui_status(self, d):
        if d['status'] == 'downloading':
            p = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_percent_str', '0%'))
            s = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_speed_str', 'N/A'))
            eta = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_eta_str', 'N/A'))
            self.after(0, lambda: self.status_label.configure(text=f"进度: {p} | 速度: {s} | 剩余: {eta}"))
        elif d['status'] == 'finished':
            self.after(0, lambda: self.status_label.configure(text="下载完成，正在合并...", text_color="yellow"))

    def save_config(self):
        new_data = {
            "last_path": self.download_path_var.get(), 
            "last_proxy": self.proxy_addr_var.get(), 
            "proxy_enabled": self.proxy_enabled_var.get(), 
            "sub": self.sub_var.get(), 
            "audio": self.audio_var.get(), 
            "thumb": self.thumb_var.get(), 
            "shutdown": self.shutdown_var.get(), 
            "quality": self.quality_var.get(),
            "auto_paste": self.auto_paste_var.get(),
            "cookie_browser": self.cookie_var.get(),
        }
        self.cm.save_config(new_data)

    def start_batch_download(self):
        self.save_config()
        urls = [u.strip() for u in self.url_text.get("0.0", "end").split("\n") if u.strip()]
        if not urls: return
        self.download_btn.configure(state="disabled")
        self.log_box.delete("0.0", "end")
        threading.Thread(target=self.batch_task, args=(urls,), daemon=True).start()

    def batch_task(self, urls):
        """核心下载任务循环：调用外部引擎"""
        for i, url in enumerate(urls, 1):
            try:
                # 调用解耦后的引擎执行下载
                self.engine.download(
                    url=url, 
                    config=self.cm.config, 
                    download_path=self.download_path_var.get()
                )
            except Exception as e:
                clean_err = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
                self.after(0, lambda msg=clean_err[:100]: self.log_box.insert("end", f"🚨 失败: {msg}\n"))
        
        self.after(0, lambda: self.status_label.configure(text="✨ 任务全部完成！", text_color="#2ecc71"))
        self.after(0, lambda: self.download_btn.configure(state="normal"))
        # --- 新增：系统弹窗提醒 ---
        self.after(0, lambda: self.show_custom_notification("任务提醒", "🚀 所有下载任务已圆满完成！\n文件已妥善保存至您的下载目录。"))
        if self.shutdown_var.get(): os.system("shutdown /s /t 60")

if __name__ == "__main__":
    YouTubeDownloaderPro().mainloop()