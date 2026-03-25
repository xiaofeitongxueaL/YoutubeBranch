import yt_dlp
import os
import re

class DownloaderEngine:
    def __init__(self, ffmpeg_path, logger=None, progress_hook=None):
        """
        :param ffmpeg_path: FFmpeg bin 目录路径
        :param logger: 传递日志记录对象 (需有 debug, warning, error 方法)
        :param progress_hook: 进度条回调函数
        """
        self.ffmpeg_path = ffmpeg_path
        self.logger = logger
        self.progress_hook = progress_hook

    def get_ydl_opts(self, config, url, download_path):
        """根据配置生成 yt-dlp 参数字典"""
        q_map = {
            "最高画质": "bestvideo+bestaudio/best",
            "2160p (4K)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "1440p (2K)": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]"
        }

        is_audio = config.get('audio', False)
        is_sub = config.get('sub', False)
        suffix = "_音频" if is_audio else ("_带字幕" if is_sub else "_原版")
        name_tmpl = f'%(title)s{suffix}.%(ext)s' if is_audio else f'%(title)s{suffix}_%(height)sp.%(ext)s'

        opts = {
            'proxy': config.get('last_proxy') if config.get('proxy_enabled') else None,
            'ffmpeg_location': self.ffmpeg_path,
            'outtmpl': os.path.join(download_path, name_tmpl),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'logger': self.logger,
            'progress_hooks': [self.progress_hook] if self.progress_hook else [],
            'merge_output_format': 'mp4',
            'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}, {'key': 'FFmpegMetadata'}],
        }
        browser = config.get('cookie_browser', "无")
        if browser != "无":
            # 这里的格式是 (浏览器名, 用户目录, 密码, 容器)
            # 我们只需要传浏览器名，后面传 None 即可
            opts['cookiesfrombrowser'] = (browser.lower(), None, None, None)
            print(f"[DEBUG] 已注入浏览器 Cookie: {browser}")

        # 封面保存
        if config.get('thumb'):
            opts.update({'writethumbnail': True})
            opts['postprocessors'].append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})

        # 提取音频
        if is_audio:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'].insert(0, {
                'key': 'FFmpegExtractAudio', 
                'preferredcodec': 'mp3', 
                'preferredquality': '192'
            })
        else:
            opts['format'] = q_map.get(config.get('quality'), "bestvideo+bestaudio/best")
            # 字幕逻辑
            if is_sub:
                # 1. 广谱语言捕获：把所有可能的中文代号全加上，确保 100% 命中
                # 按照优先级排列，yt-dlp 会自动挑最好的嵌进去
                lang_list = ['zh-Hans', 'zh-CN', 'zh-TW', 'zh-Hant', 'zh', 'en']

                opts.update({
                    'writesubtitles': True, 
                    'writeautomaticsub': True, 
                    'subtitleslangs': lang_list,
                    'embedsubs': True,  # 坚持你的原方案：必须内嵌！
                
                    # 【新增防错机制】：嵌完字幕后清理临时文件，防止缓存冲突
                    'compat_opts': ['no-keep-subs'], 
                })
            
                    # 2. 严格的后处理顺序：必须先强制转为 srt，再执行内嵌
                opts['postprocessors'].extend([
                    # 第一步：把抓到的任何乱七八糟格式的字幕，统统转成标准的 srt
                    {'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'}, 
                    # 第二步：调用 FFmpeg 强行把 srt 塞进 mp4 容器里
                    {'key': 'FFmpegEmbedSubtitle', 'already_have_subtitle': False}
                ])
        
        return opts

    def download(self, url, config, download_path):
        """执行下载任务"""
        opts = self.get_ydl_opts(config, url, download_path)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            raise e