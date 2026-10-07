@echo off
setlocal
chcp 65001 >nul
title Turbo Descargar v3.0 - Windows

:: Asegurar que PATH incluya winget, python, deno y aria2c
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Links;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%LOCALAPPDATA%\deno\bin;%USERPROFILE%\.deno\bin"

:: Si se invoca con argumentos desde consola o script, actuar como puente directo a yt-dlp.exe
if not "%~1"=="" (
    yt-dlp.exe %*
    exit /b %errorlevel%
)

:: Opciones de aceleracion maxima de ancho de banda (Multi-hilo Nativo)
set "TURBO_ARGS=--concurrent-fragments 16 --buffer-size 16M"

set "OUTDIR=%~dp0Descargas"
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

set "LINK="

:MENU
cls
echo =======================================================
echo    TURBO DESCARGAR v3.0 - WINDOWS (MODO CONSOLA)
echo    [Modo Turbo Activo: 16 hilos / Ancho de banda 100%%]
echo =======================================================
if "%LINK%"=="" (
    echo [*] Enlace actual: [Ninguno seleccionado]
) else (
    echo [*] Enlace actual: %LINK%
)
echo [*] Carpeta destino: %OUTDIR%
echo =======================================================
echo  1. Anadir o cambiar enlace de YouTube
echo  2. Descargar AUDIO a Maxima Calidad (MP3 320kbps)
echo  3. Descargar VIDEO a Maxima Resolucion (4K/2K/1080p)
echo  4. Descargar lista desde enlaces.txt (Audio MP3)
echo  5. Descargar lista desde enlaces.txt (Video Maxima Resolucion)
echo  6. Abrir Interfaz Grafica Moderna (GUI)
echo  7. Actualizar yt-dlp
echo  8. Abrir carpeta de descargas
echo  9. Salir
echo =======================================================

set "OPCION="
set /p "OPCION=Elige una opcion (1-9): "

if "%OPCION%"=="" goto MENU
if "%OPCION%"=="1" goto SET_LINK
if "%OPCION%"=="2" goto DL_MP3
if "%OPCION%"=="3" goto DL_MP4
if "%OPCION%"=="4" goto DL_LIST_MP3
if "%OPCION%"=="5" goto DL_LIST_MP4
if "%OPCION%"=="6" goto LAUNCH_GUI
if "%OPCION%"=="7" goto UPDATE_YTDLP
if "%OPCION%"=="8" goto OPEN_DIR
if "%OPCION%"=="9" goto EXIT

echo.
echo [!] Opcion no valida: "%OPCION%"
ping 127.0.0.1 -n 2 >nul
goto MENU

:SET_LINK
echo.
set "LINK="
set /p "LINK=Pega el enlace de YouTube: "
if "%LINK%"=="" (
    echo No ingresaste ningun enlace.
    pause
    goto MENU
)
echo [OK] Enlace guardado con exito.
ping 127.0.0.1 -n 2 >nul
goto MENU

:DL_MP3
if "%LINK%"=="" (
    echo.
    echo [!] Primero debes anadir un enlace con la opcion 1.
    pause
    goto MENU
)
echo.
echo [*] Descargando audio a Maxima Calidad (MP3 320kbps)...
yt-dlp.exe --no-playlist %TURBO_ARGS% --extract-audio --audio-format mp3 --audio-quality 0 -o "%OUTDIR%/%%(title)s.%%(ext)s" "%LINK%"
echo.
echo [OK] Descarga finalizada.
pause
goto MENU

:DL_MP4
if "%LINK%"=="" (
    echo.
    echo [!] Primero debes anadir un enlace con la opcion 1.
    pause
    goto MENU
)
echo.
echo [*] Descargando video en la MAXIMA resolucion permitida (Multi-hilos)...
yt-dlp.exe --no-playlist %TURBO_ARGS% -f "bestvideo+bestaudio/best" --merge-output-format mp4 -o "%OUTDIR%/%%(title)s.%%(ext)s" "%LINK%"
echo.
echo [OK] Descarga finalizada.
pause
goto MENU

:DL_LIST_MP3
if not exist "%~dp0enlaces.txt" (
    echo.
    echo [!] No se encontro el archivo enlaces.txt
    pause
    goto MENU
)
echo.
echo [*] Descargando lista de enlaces.txt en formato MP3...
yt-dlp.exe --no-playlist %TURBO_ARGS% -a "%~dp0enlaces.txt" --extract-audio --audio-format mp3 --audio-quality 0 -o "%OUTDIR%/%%(title)s.%%(ext)s"
echo.
echo [OK] Descargas finalizadas.
pause
goto MENU

:DL_LIST_MP4
if not exist "%~dp0enlaces.txt" (
    echo.
    echo [!] No se encontro el archivo enlaces.txt
    pause
    goto MENU
)
echo.
echo [*] Descargando lista de enlaces.txt a Maxima Resolucion...
yt-dlp.exe --no-playlist %TURBO_ARGS% -a "%~dp0enlaces.txt" -f "bestvideo+bestaudio/best" --merge-output-format mp4 -o "%OUTDIR%/%%(title)s.%%(ext)s"
echo.
echo [OK] Descargas finalizadas.
pause
goto MENU

:LAUNCH_GUI
start pythonw "%~dp0gui_app.py"
goto MENU

:UPDATE_YTDLP
echo.
echo [*] Actualizando yt-dlp...
python -m pip install --upgrade yt-dlp
pause
goto MENU

:OPEN_DIR
start "" "%OUTDIR%"
goto MENU

:EXIT
echo.
echo Gracias por usar Turbo Descargar. Hasta pronto.
ping 127.0.0.1 -n 2 >nul
exit /b
