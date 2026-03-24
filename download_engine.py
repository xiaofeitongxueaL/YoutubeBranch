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
                opts.update({
                    'writesubtitles': True, 
                    'writeautomaticsub': True, 
                    'subtitleslangs': ['zh-Hans', 'en'], 
                    'embedsubs': True
                })
                opts['postprocessors'].extend([
                    {'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'}, 
                    {'key': 'FFmpegEmbedSubtitle'}
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
    
    def get_quick_info(self, url, config):
        """抓取预览：强制只读第1项，绝不加载整个列表"""
        proxy = config.get('last_proxy') if config.get('proxy_enabled') else None
        if proxy and not proxy.startswith('http'):
            proxy = f"http://{proxy}"

        ydl_opts = {
            'proxy': proxy,
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'socket_timeout': 5,             # 5秒强制超时
            'nocheckcertificate': True,
            'extract_flat': 'in_playlist',   # 只抓取列表元数据
            'playlist_items': '1',           # 【核心】只抓取第1个视频，防止卡死
            'lazy_playlist': True,           # 懒加载模式
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info: return None

                # 处理列表/Mix 情况
                if 'entries' in info or info.get('_type') == 'playlist':
                    title = info.get('title', '未知列表')
                    uploader = info.get('uploader') or info.get('uploader_id') or "YouTube Mix"
                    return {
                        'title': f"项目: {title}",
                        'duration': "列表/混合频道",
                        'uploader': uploader
                    }

                # 处理单个视频情况
                return {
                    'title': info.get('title', '未知标题'),
                    'duration': self._format_seconds(info.get('duration')),
                    'uploader': info.get('uploader') or info.get('channel') or "未知作者"
                }
        except Exception as e:
            print(f"[DEBUG] 预览抓取崩溃: {str(e)}")
            return None