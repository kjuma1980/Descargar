@echo off
setlocal
chcp 65001 >nul
title Turbo Descargar v3.0 - Modo Consola + GUI
:: Asegurar que las variables de entorno de Deno, Python y FFmpeg est??n disponibles
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Links;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%LOCALAPPDATA%\deno\bin;%USERPROFILE%\.deno\bin"

cd /d "%~dp0"
echo Iniciando Turbo Descargar con consola externa activa...
python gui_app.py
pause
