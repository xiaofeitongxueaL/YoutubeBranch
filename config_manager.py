import os
import json
import sys

class ConfigManager:
    def __init__(self):
        # --- 核心路径锁定 (兼容打包后的路径) ---
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.config_file = os.path.join(self.base_dir, "config.json")
        self.ffmpeg_bin = os.path.join(self.base_dir, "bin")
        
        # 初始化加载配置
        self.config = self.load_config()

    def get_ffmpeg_path(self):
        """返回 FFmpeg 所在的 bin 目录"""
        return self.ffmpeg_bin

    def load_config(self):
        """读取配置文件"""
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        default = {
            "last_path": desktop, 
            "last_proxy": "http://127.0.0.1:7890", 
            "proxy_enabled": False, 
            "sub": False, 
            "audio": False, 
            "thumb": False, 
            "shutdown": False, 
            "quality": "最高画质",
            "cookie_browser":"无"
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 修复路径残留问题
                    if "VS Code" in data.get("last_path", ""): 
                        data["last_path"] = desktop
                    return {**default, **data}
            except Exception:
                pass
        return default

    def save_config(self, data):
        """保存当前配置到文件"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            # 同时更新内存中的配置
            self.config.update(data)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def get(self, key, default=None):
        """获取单个配置项的值"""
        return self.config.get(key, default)