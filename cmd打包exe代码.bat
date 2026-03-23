@echo off
chcp 65001 >nul
echo ========================================
echo   正在开始打包 YouTubepythonPro1.0
echo ========================================

:: 1. 删除旧的打包文件夹防止冲突
rd /s /q build
rd /s /q dist

:: 2. 执行打包命令
pyinstaller --noconsole --onefile --collect-all customtkinter --name "YouTubeDownload" main.py

echo ========================================
echo   打包完成！请去 dist 文件夹查看 EXE。
echo ========================================
pause