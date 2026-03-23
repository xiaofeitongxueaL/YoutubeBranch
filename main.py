import customtkinter as ctk
import yt_dlp, threading, re, os, sys, requests
from tkinter import filedialog
# 1. 导入你刚才创建的新模块
from config_manager import ConfigManager

# 设置主题
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MyLogger:
    def __init__(self, textbox):
        self.textbox = textbox
    def write(self, msg):
        clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', msg)
        self.textbox.after(0, lambda: self.textbox.insert("end", clean_msg + "\n"))
        self.textbox.after(0, lambda: self.textbox.see("end"))
    def debug(self, msg): self.write(msg)
    def warning(self, msg): self.write(f"⚠️ {msg}")
    def error(self, msg): self.write(f"🚨 {msg}")

class YouTubeDownloaderPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        # 2. 初始化配置管理器
        self.cm = ConfigManager()
        self.conf = self.cm.config # 获取配置数据

        self.title("YouTube 全能爬虫 Pro v4.4 (模块化版)")
        self.geometry("750x920") 
        self.grid_columnconfigure(0, weight=1)
        
        # 联网公告
        self.msg_label = ctk.CTkLabel(self, text="正在同步在线公告...", text_color="gray")
        self.msg_label.grid(row=0, column=0, pady=(10, 0))
        threading.Thread(target=self.check_online_info, daemon=True).start()

        self.label = ctk.CTkLabel(self, text="YouTube 全能爬虫系统", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=1, column=0, padx=20, pady=(10, 10))

        # 批量输入
        self.url_text = ctk.CTkTextbox(self, width=680, height=100)
        self.url_text.grid(row=2, column=0, padx=20, pady=5)
        
        # 路径选择区
        self.path_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.path_frame.grid(row=3, column=0, padx=20, pady=5)
        self.download_path_var = ctk.StringVar(value=self.conf['last_path']) 
        ctk.CTkEntry(self.path_frame, width=470, textvariable=self.download_path_var).pack(side="left", padx=(0, 10))
        
        # 按钮 1：选路径
        ctk.CTkButton(self.path_frame, text="📁 选路径", width=80, command=self.select_path, fg_color="#34495e").pack(side="left", padx=2)
        
        # 按钮 2：新增的“打开”按钮
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

        # 开关区
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.grid(row=5, column=0, padx=20, pady=10)
        self.sub_var = ctk.BooleanVar(value=self.conf.get('sub', False))
        self.audio_var = ctk.BooleanVar(value=self.conf.get('audio', False))
        self.thumb_var = ctk.BooleanVar(value=self.conf.get('thumb', False))
        self.shutdown_var = ctk.BooleanVar(value=self.conf.get('shutdown', False))

        ctk.CTkSwitch(self.ctrl_frame, text="内嵌字幕", variable=self.sub_var).pack(side="left", padx=5)
        ctk.CTkSwitch(self.ctrl_frame, text="仅音频", variable=self.audio_var).pack(side="left", padx=5)
        ctk.CTkSwitch(self.ctrl_frame, text="保存封面", variable=self.thumb_var).pack(side="left", padx=5)
        ctk.CTkSwitch(self.ctrl_frame, text="任务完关机", variable=self.shutdown_var).pack(side="left", padx=5)

        self.quality_var = ctk.StringVar(value=self.conf.get('quality', "最高画质"))
        ctk.CTkOptionMenu(self.ctrl_frame, values=["最高画质", "2160p (4K)", "1440p (2K)", "1080p", "720p"], variable=self.quality_var, width=120).pack(side="left", padx=5)

        # 下载按钮
        self.download_btn = ctk.CTkButton(self, text="🚀 开启全能爬取模式", height=50, command=self.start_batch_download, font=ctk.CTkFont(size=18, weight="bold"))
        self.download_btn.grid(row=6, column=0, padx=20, pady=20)

        # 进度显示
        self.status_label = ctk.CTkLabel(self, text="准备就绪", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label.grid(row=7, column=0)
        self.log_box = ctk.CTkTextbox(self, width=680, height=200, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.grid(row=8, column=0, padx=20, pady=10)

    def toggle_proxy(self):
        self.proxy_entry.configure(state="normal" if self.proxy_enabled_var.get() else "disabled")

    def check_online_info(self):
        try:
            url = "https://raw.githubusercontent.com/xiaofeitongxueaL/YoutubeDownload/refs/heads/main/info.json"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                self.after(0, lambda: self.msg_label.configure(text=data.get("notice", ""), text_color="cyan"))
        except: pass

    # 3. 简化后的保存配置方法
    def save_config(self):
        new_data = {
            "last_path": self.download_path_var.get(), 
            "last_proxy": self.proxy_addr_var.get(), 
            "proxy_enabled": self.proxy_enabled_var.get(), 
            "sub": self.sub_var.get(), 
            "audio": self.audio_var.get(), 
            "thumb": self.thumb_var.get(), 
            "shutdown": self.shutdown_var.get(), 
            "quality": self.quality_var.get()
        }
        self.cm.save_config(new_data)

    def select_path(self):
        folder = filedialog.askdirectory()
        if folder: self.download_path_var.set(folder)

    # --- 新增：一键打开下载目录 ---
    def open_folder(self):
        path = self.download_path_var.get()
        if os.path.exists(path):
            os.startfile(path) # 仅适用于 Windows
        else:
            self.log_box.insert("end", "🚨 错误：文件夹路径不存在！\n")

    def start_batch_download(self):
        self.save_config()
        urls = [u.strip() for u in self.url_text.get("0.0", "end").split("\n") if u.strip()]
        if not urls: return
        self.download_btn.configure(state="disabled")
        self.log_box.delete("0.0", "end")
        threading.Thread(target=self.batch_task, args=(urls,), daemon=True).start()

    def update_ui_status(self, d):
        if d['status'] == 'downloading':
            p = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_percent_str', '0%'))
            s = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_speed_str', 'N/A'))
            eta = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_eta_str', 'N/A'))
            self.after(0, lambda: self.status_label.configure(text=f"进度: {p} | 速度: {s} | 剩余: {eta}"))
        elif d['status'] == 'finished':
            self.after(0, lambda: self.status_label.configure(text="下载完成，正在合并文件...", text_color="yellow"))

    def batch_task(self, urls):
        q_map = {"最高画质": "bestvideo+bestaudio/best", "2160p (4K)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]", "1440p (2K)": "bestvideo[height<=1440]+bestaudio/best[height<=1440]", "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]", "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]"}
        active_proxy = self.proxy_addr_var.get() if self.proxy_enabled_var.get() else None

        for i, url in enumerate(urls, 1):
            is_audio = self.audio_var.get()
            suffix = "_音频" if is_audio else ("_带字幕" if self.sub_var.get() else "_原版")
            name_tmpl = f'%(title)s{suffix}.%(ext)s' if is_audio else f'%(title)s{suffix}_%(height)sp.%(ext)s'

            ydl_opts = {
                'proxy': active_proxy, 
                # 4. 使用管理器提供的 FFmpeg 路径
                'ffmpeg_location': self.cm.ffmpeg_bin, 
                'outtmpl': os.path.join(self.download_path_var.get(), name_tmpl),
                'noplaylist': True, 'quiet': True, 'no_warnings': True,
                'logger': MyLogger(self.log_box),
                'progress_hooks': [self.update_ui_status],
                'merge_output_format': 'mp4',
                'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}, {'key': 'FFmpegMetadata'}],
            }

            if self.thumb_var.get():
                ydl_opts.update({'writethumbnail': True})
                ydl_opts['postprocessors'].append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
            
            if self.audio_var.get():
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'})
            else:
                ydl_opts['format'] = q_map.get(self.quality_var.get(), "bestvideo+bestaudio/best")
                if self.sub_var.get():
                    ydl_opts.update({'writesubtitles': True, 'writeautomaticsub': True, 'subtitleslangs': ['zh-Hans', 'en'], 'embedsubs': True})
                    ydl_opts['postprocessors'].extend([{'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'}, {'key': 'FFmpegEmbedSubtitle'}])

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
            except Exception as e:
                clean_err = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
                self.after(0, lambda msg=clean_err[:50]: self.log_box.insert("end", f"🚨 失败: {msg}\n"))
        
        self.after(0, lambda: self.status_label.configure(text="✨ 任务全部完成！", text_color="#2ecc71"))
        self.after(0, lambda: self.download_btn.configure(state="normal"))
        if self.shutdown_var.get(): os.system("shutdown /s /t 60")

if __name__ == "__main__":
    YouTubeDownloaderPro().mainloop()