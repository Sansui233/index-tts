@echo off  
chcp 65001 >nul
echo  启动中，请耐心等待 哔哩哔哩@不吃鸟的虫子  https://b23.tv/7Y2BJkn
.\.venv\Scripts\activate.bat
conda activate index-tts
call python.exe .\webui2.py
pause