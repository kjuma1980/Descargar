# Turbo Descargar v3.0 para Windows (PowerShell 5.1 y 7+)
# Descarga audio MP3 y video MP4 a mÃ¡xima velocidad usando todo el ancho de banda

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { $Host.UI.RawUI.WindowTitle = "Turbo Descargar v3.0 - Windows" } catch {}

# Refrescar PATH para incluir Deno, Python Scripts, FFmpeg y Aria2
$env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$OutputDir = Join-Path $ScriptDir "Descargas"
if (-not (Test-Path -Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

function Check-Dependencies {
    $ytdlp = Get-Command yt-dlp -ErrorAction SilentlyContinue
    if (-not $ytdlp) {
        Write-Host "[!] yt-dlp no se encuentra en el PATH." -ForegroundColor Yellow
        Write-Host "[*] Intentando instalar yt-dlp..." -ForegroundColor Cyan
        $pip = Get-Command pip -ErrorAction SilentlyContinue
        if ($pip) {
            pip install --upgrade yt-dlp
        } else {
            winget install yt-dlp
        }
    } else {
        Write-Host "[OK] yt-dlp detectado: $($ytdlp.Source)" -ForegroundColor Green
    }

    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if (-not $ffmpeg) {
        Write-Host "[!] ffmpeg no detectado en PATH." -ForegroundColor Yellow
    } else {
        Write-Host "[OK] ffmpeg detectado: $($ffmpeg.Source)" -ForegroundColor Green
    }

    $deno = Get-Command deno -ErrorAction SilentlyContinue
    if ($deno) {
        Write-Host "[OK] Motor JavaScript (Deno) detectado: $($deno.Source)" -ForegroundColor Green
    }

    $aria = Get-Command aria2c -ErrorAction SilentlyContinue
    if ($aria) {
        Write-Host "[OK] Acelerador Multi-conexiÃ³n (aria2c) detectado: $($aria.Source)" -ForegroundColor Green
    }

    Start-Sleep -Seconds 1
}

function Show-Header {
    try { Clear-Host } catch {}
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host "             TURBO DESCARGAR v3.0 (WINDOWS)            " -ForegroundColor Yellow
    Write-Host "      [Modo Turbo Activo: 16 Hilos / Ancho Completo]   " -ForegroundColor Green
    Write-Host "=======================================================" -ForegroundColor Cyan
    if ($global:CurrentLink) {
        Write-Host "[*] Enlace actual: $global:CurrentLink" -ForegroundColor Green
    } else {
        Write-Host "[*] Enlace actual: [Ninguno seleccionado]" -ForegroundColor DarkGray
    }
    Write-Host "[*] Carpeta destino: $OutputDir" -ForegroundColor DarkGray
    Write-Host "=======================================================" -ForegroundColor Cyan
}

Check-Dependencies

$global:CurrentLink = ""

# Argumentos base de aceleraciÃ³n de ancho de banda
$turboArgs = @(
    "--no-playlist",
    "--concurrent-fragments", "16",
    "--buffer-size", "16M",
    "--extractor-args", "youtube:player_client=android,web"
)
if (Get-Command aria2c -ErrorAction SilentlyContinue) {
    $turboArgs += @("--downloader", "aria2c", "--downloader-args", "aria2c:-x 16 -s 16 -k 1M -j 16")
}

function Start-App {
    while ($true) {
        Show-Header
        Write-Host " 1. Anadir o cambiar enlace de YouTube" -ForegroundColor White
        Write-Host " 2. Descargar AUDIO a Maxima Calidad (MP3 320kbps)" -ForegroundColor White
        Write-Host " 3. Descargar VIDEO a Maxima Resolucion (4K/2K/1080p)" -ForegroundColor White
        Write-Host " 4. Descargar lista desde enlaces.txt (Audio MP3)" -ForegroundColor White
        Write-Host " 5. Descargar lista desde enlaces.txt (Video Maxima Resolucion)" -ForegroundColor White
        Write-Host " 6. Iniciar Interfaz Grafica Moderna (GUI)" -ForegroundColor White
        Write-Host " 7. Actualizar yt-dlp" -ForegroundColor White
        Write-Host " 8. Abrir carpeta de descargas" -ForegroundColor White
        Write-Host " 9. Salir" -ForegroundColor White
        Write-Host "=======================================================" -ForegroundColor Cyan

        $op = Read-Host "Elige una opcion (1-9)"
        switch ($op.Trim()) {
            "1" {
                $link = Read-Host "`nPega el enlace de YouTube"
                if (![string]::IsNullOrWhiteSpace($link)) {
                    $global:CurrentLink = $link.Trim()
                    Write-Host "[OK] Enlace guardado." -ForegroundColor Green
                } else {
                    Write-Host "[!] Enlace vacio." -ForegroundColor Yellow
                }
                Start-Sleep -Seconds 1
            }
            "2" {
                if (-not $global:CurrentLink) {
                    Write-Host "`n[!] Primero debes anadir un enlace con la opcion 1." -ForegroundColor Red
                    Read-Host "Presiona Enter para continuar"
                    continue
                }
                Write-Host "`n[*] Descargando audio a mÃ¡xima calidad (Turbo 16 hilos)..." -ForegroundColor Cyan
                yt-dlp @turboArgs --extract-audio --audio-format mp3 --audio-quality 0 -o "$OutputDir/%(title)s.%(ext)s" $global:CurrentLink
                Write-Host "`n[OK] Descarga finalizada." -ForegroundColor Green
                Read-Host "Presiona Enter para continuar"
            }
            "3" {
                if (-not $global:CurrentLink) {
                    Write-Host "`n[!] Primero debes anadir un enlace con la opcion 1." -ForegroundColor Red
                    Read-Host "Presiona Enter para continuar"
                    continue
                }
                Write-Host "`n[*] Descargando video en la MAXIMA resolucion permitida (Turbo 16 hilos)..." -ForegroundColor Cyan
                yt-dlp @turboArgs -f "bestvideo+bestaudio/best" --merge-output-format mp4 -o "$OutputDir/%(title)s.%(ext)s" $global:CurrentLink
                Write-Host "`n[OK] Descarga finalizada." -ForegroundColor Green
                Read-Host "Presiona Enter para continuar"
            }
            "4" {
                $listPath = Join-Path $ScriptDir "enlaces.txt"
                if (Test-Path $listPath) {
                    Write-Host "`n[*] Descargando lista en MP3 desde enlaces.txt (Turbo)..." -ForegroundColor Cyan
                    yt-dlp @turboArgs -a $listPath --extract-audio --audio-format mp3 --audio-quality 0 -o "$OutputDir/%(title)s.%(ext)s"
                    Write-Host "`n[OK] Descargas finalizadas." -ForegroundColor Green
                } else {
                    Write-Host "`n[!] No se encontro el archivo enlaces.txt" -ForegroundColor Red
                }
                Read-Host "Presiona Enter para continuar"
            }
            "5" {
                $listPath = Join-Path $ScriptDir "enlaces.txt"
                if (Test-Path $listPath) {
                    Write-Host "`n[*] Descargando lista en Maxima Resolucion desde enlaces.txt (Turbo)..." -ForegroundColor Cyan
                    yt-dlp @turboArgs -a $listPath -f "bestvideo+bestaudio/best" --merge-output-format mp4 -o "$OutputDir/%(title)s.%(ext)s"
                    Write-Host "`n[OK] Descargas finalizadas." -ForegroundColor Green
                } else {
                    Write-Host "`n[!] No se encontro el archivo enlaces.txt" -ForegroundColor Red
                }
                Read-Host "Presiona Enter para continuar"
            }
            "6" {
                Start-Process pythonw (Join-Path $ScriptDir "gui_app.py")
            }
            "7" {
                Write-Host "`n[*] Actualizando yt-dlp..." -ForegroundColor Cyan
                python -m pip install --upgrade yt-dlp
                Read-Host "Presiona Enter para continuar"
            }
            "8" {
                Start-Process explorer.exe $OutputDir
            }
            "9" {
                Write-Host "`nGracias por usar Turbo Descargar. Hasta pronto!`n" -ForegroundColor Green
                Start-Sleep -Seconds 1
                return
            }
            Default {
                Write-Host "`n[!] Opcion no valida: '$op'" -ForegroundColor Red
                Start-Sleep -Seconds 1
            }
        }
    }
}

Start-App
