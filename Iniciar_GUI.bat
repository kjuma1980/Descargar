@echo off
setlocal
chcp 65001 >nul
:: Asegurar que las variables de entorno de Deno, Python y FFmpeg est??n disponibles
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Links;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%LOCALAPPDATA%\deno\bin;%USERPROFILE%\.deno\bin"

cd /d "%~dp0"
start pythonw gui_app.py
exit /b
