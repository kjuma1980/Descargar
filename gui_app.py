#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turbo Descargar v3.0 - Interfaz Gráfica Moderna
Descargador de Audio y Video con detección de Resoluciones Reales de YouTube
y Aceleración de Ancho de Banda al 100% (yt-dlp + CustomTkinter).
"""

import os
import sys
import multiprocessing

# Soporte para ejecutables congelados (evita instancias duplicadas en Windows)
multiprocessing.freeze_support()

import socket
import urllib.request
import json
import ssl

# Resolver DoH integrado para neutralizar secuestro/envenenamiento DNS en puertos UDP 53 (routers, DPN, túneles)
_orig_getaddrinfo = socket.getaddrinfo
_ssl_doh_ctx = ssl.create_default_context()
_ssl_doh_ctx.check_hostname = False
_ssl_doh_ctx.verify_mode = ssl.CERT_NONE

def _doh_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    host_str = str(host)
    if any(d in host_str for d in ('googlevideo.com', 'youtube.com', 'ytimg.com', 'ggpht.com')):
        try:
            req = urllib.request.Request(
                f'https://1.1.1.1/dns-query?name={host}&type=A',
                headers={'accept': 'application/dns-json', 'User-Agent': 'Mozilla/5.0'}
            )
            res = json.loads(urllib.request.urlopen(req, context=_ssl_doh_ctx, timeout=3).read())
            ips = [ans['data'] for ans in res.get('Answer', []) if ans.get('type') == 1]
            if ips:
                return _orig_getaddrinfo(ips[0], port, family, type, proto, flags)
        except Exception:
            pass
    return _orig_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = _doh_getaddrinfo

# Despachador CLI inmediato antes de inicializar librerías de interfaz gráfica
if "--internal-ytdlp" in sys.argv:
    idx = sys.argv.index("--internal-ytdlp")
    cli_args = sys.argv[idx + 1:]
    import yt_dlp
    sys.exit(yt_dlp.main(cli_args))

if len(sys.argv) > 2 and sys.argv[1] == "-m" and sys.argv[2] == "yt_dlp":
    import yt_dlp
    sys.exit(yt_dlp.main(sys.argv[3:]))


import re
import json
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Configuración visual
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TurboDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de ventana principal
        self.title("Turbo Descargar v3.0 - YouTube Downloader Ultra")
        self.geometry("880x800")
        self.minsize(800, 700)

        # Cargar configuración y preferencias del usuario
        self.config = self._load_config()
        saved_dir = self.config.get("download_dir")
        if saved_dir and os.path.exists(saved_dir):
            self.download_dir = saved_dir
        else:
            default_dl = os.path.join(os.path.expanduser("~"), "Videos", "TurboDescargar")
            try:
                os.makedirs(default_dl, exist_ok=True)
                self.download_dir = default_dl
            except Exception:
                try:
                    alt_dl = os.path.join(os.path.expanduser("~"), "Downloads", "TurboDescargar")
                    os.makedirs(alt_dl, exist_ok=True)
                    self.download_dir = alt_dl
                except Exception:
                    self.download_dir = os.path.expanduser("~")

        self.current_process = None
        self.is_downloading = False
        self.is_analyzing = False

        # Mapeo de opciones del menú a selectores reales de formato
        self.format_height_map = {}
        self.current_video_title = ""

        self._build_ui()
        self._check_environment()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # 1. ENCABEZADO
        self.header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("#1f2937", "#111827"))
        self.header_frame.pack(fill="x", padx=16, pady=(14, 8))

        header_top = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_top.pack(fill="x", padx=16, pady=(10, 2))

        self.title_label = ctk.CTkLabel(
            header_top,
            text="⚡ TURBO DESCARGAR v3.0",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#60a5fa"
        )
        self.title_label.pack(side="left")

        # Aplicar tema guardado
        saved_theme = self.config.get("theme", "Dark")
        if saved_theme == "Light":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")

        self.theme_switch = ctk.CTkSwitch(
            header_top,
            text="Modo Oscuro",
            command=self._toggle_theme,
            font=ctk.CTkFont(size=12)
        )
        if saved_theme != "Light":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        self.theme_switch.pack(side="right")

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Descargas a máxima velocidad con detección dinámica de resoluciones reales de YouTube (sin calidades forzadas)",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        self.subtitle_label.pack(anchor="w", padx=16, pady=(0, 10))

        # 2. ENTRADA DE ENLACE + ANALIZADOR
        self.url_frame = ctk.CTkFrame(self, corner_radius=10)
        self.url_frame.pack(fill="x", padx=16, pady=6)

        self.url_label = ctk.CTkLabel(
            self.url_frame,
            text="Enlace de YouTube o Archivo de Enlaces:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.url_label.pack(anchor="w", padx=14, pady=(10, 4))

        self.url_input_box = ctk.CTkFrame(self.url_frame, fg_color="transparent")
        self.url_input_box.pack(fill="x", padx=14, pady=(0, 6))

        self.url_entry = ctk.CTkEntry(
            self.url_input_box,
            placeholder_text="Pega aquí el enlace de YouTube y presiona Enter...",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self._start_analyze_thread())

        self.paste_btn = ctk.CTkButton(
            self.url_input_box,
            text="📋 Pegar",
            width=85,
            height=38,
            command=self._paste_and_analyze
        )
        self.paste_btn.pack(side="left", padx=(0, 6))

        self.analyze_btn = ctk.CTkButton(
            self.url_input_box,
            text="🔍 Cargar Calidades",
            width=140,
            height=38,
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._start_analyze_thread
        )
        self.analyze_btn.pack(side="left", padx=(0, 6))

        self.batch_btn = ctk.CTkButton(
            self.url_input_box,
            text="📄 Lista TXT",
            width=95,
            height=38,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self._load_txt_file
        )
        self.batch_btn.pack(side="left", padx=(0, 6))

        self.cookies_btn = ctk.CTkButton(
            self.url_input_box,
            text="🍪 Cookies",
            width=95,
            height=38,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self._manage_cookies
        )
        self.cookies_btn.pack(side="left")

        # Tarjeta informativa del video analizado
        self.info_card = ctk.CTkFrame(self.url_frame, fg_color=("#374151", "#1e293b"), corner_radius=8)
        self.info_label = ctk.CTkLabel(
            self.info_card,
            text="",
            font=ctk.CTkFont(size=12),
            justify="left",
            text_color="#93c5fd"
        )
        self.info_label.pack(anchor="w", padx=12, pady=8)

        # 3. OPCIONES DE FORMATO Y RESOLUCIÓN REAL
        self.options_frame = ctk.CTkFrame(self, corner_radius=10)
        self.options_frame.pack(fill="x", padx=16, pady=6)

        # Fila 1: Selector de Calidades Reales
        self.format_row = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.format_row.pack(fill="x", padx=14, pady=(10, 6))

        self.format_label = ctk.CTkLabel(
            self.format_row,
            text="Resolución Real:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.format_label.pack(side="left", padx=(0, 10))

        self.format_var = ctk.StringVar(value="🌟 Video: Máxima Resolución Real que permita el video")
        self.default_formats = [
            "🌟 Video: Máxima Resolución Real que permita el video",
            "🎵 Audio: MP3 Máxima Calidad (320 kbps)",
            "🎼 Audio: Calidad Original sin recodificar"
        ]
        self.format_menu = ctk.CTkOptionMenu(
            self.format_row,
            values=self.default_formats,
            variable=self.format_var,
            width=430,
            height=36
        )
        self.format_menu.pack(side="left", padx=(0, 14))

        self.switches_box = ctk.CTkFrame(self.format_row, fg_color="transparent")
        self.switches_box.pack(side="right")

        self.turbo_var = ctk.BooleanVar(value=self.config.get("turbo_mode", True))
        self.turbo_switch = ctk.CTkSwitch(
            self.switches_box,
            text="⚡ Turbo (100% Ancho de Banda)",
            variable=self.turbo_var,
            command=self._save_config,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.turbo_switch.pack(side="top", anchor="w", pady=(0, 4))

        self.no_playlist_var = ctk.BooleanVar(value=self.config.get("no_playlist", True))
        self.playlist_switch = ctk.CTkSwitch(
            self.switches_box,
            text="Solo este video (no playlist)",
            variable=self.no_playlist_var,
            command=self._save_config,
            font=ctk.CTkFont(size=12)
        )
        self.playlist_switch.pack(side="top", anchor="w")

        # Fila 2: Carpeta de Guardado
        self.dir_row = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.dir_row.pack(fill="x", padx=14, pady=(0, 10))

        self.dir_label = ctk.CTkLabel(
            self.dir_row,
            text="Carpeta destino:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.dir_label.pack(side="left", padx=(0, 10))

        self.dir_entry = ctk.CTkEntry(
            self.dir_row,
            height=34,
            font=ctk.CTkFont(size=12)
        )
        self.dir_entry.insert(0, self.download_dir)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.browse_btn = ctk.CTkButton(
            self.dir_row,
            text="📁 Cambiar",
            width=85,
            height=34,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self._browse_folder
        )
        self.browse_btn.pack(side="left", padx=(0, 6))

        self.open_dir_btn = ctk.CTkButton(
            self.dir_row,
            text="📂 Abrir Carpeta",
            width=110,
            height=34,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._open_download_dir
        )
        self.open_dir_btn.pack(side="left")

        # 4. BARRA DE PROGRESO Y ACCIONES
        self.action_frame = ctk.CTkFrame(self, corner_radius=10)
        self.action_frame.pack(fill="x", padx=16, pady=6)

        self.status_label = ctk.CTkLabel(
            self.action_frame,
            text="Estado: Pega un enlace de YouTube para cargar sus calidades reales.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#9ca3af"
        )
        self.status_label.pack(anchor="w", padx=14, pady=(10, 4))

        self.progress_bar = ctk.CTkProgressBar(self.action_frame, height=14)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=14, pady=6)

        self.btn_row = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.btn_row.pack(fill="x", padx=14, pady=(6, 12))

        self.download_btn = ctk.CTkButton(
            self.btn_row,
            text="🚀 Descargar Selección",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._start_download_thread
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(
            self.btn_row,
            text="🛑 Cancelar",
            width=100,
            height=42,
            fg_color="#ef4444",
            hover_color="#dc2626",
            state="disabled",
            command=self._cancel_download
        )
        self.cancel_btn.pack(side="left", padx=(0, 8))

        self.update_btn = ctk.CTkButton(
            self.btn_row,
            text="🔄 Actualizar yt-dlp",
            width=140,
            height=42,
            fg_color="#4b5563",
            hover_color="#374151",
            command=self._update_ytdlp
        )
        self.update_btn.pack(side="left")

        # 5. CONSOLA INTEGRADA
        self.console_frame = ctk.CTkFrame(self, corner_radius=10)
        self.console_frame.pack(fill="both", expand=True, padx=16, pady=(6, 12))

        self.console_header = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        self.console_header.pack(fill="x", padx=10, pady=(6, 2))

        self.toggle_console_var = ctk.BooleanVar(value=True)
        self.toggle_console_switch = ctk.CTkSwitch(
            self.console_header,
            text="Consola de salida en vivo",
            variable=self.toggle_console_var,
            command=self._toggle_console,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.toggle_console_switch.pack(side="left")

        self.clear_console_btn = ctk.CTkButton(
            self.console_header,
            text="Limpiar Consola",
            width=100,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#374151",
            hover_color="#4b5563",
            command=self._clear_console
        )
        self.clear_console_btn.pack(side="right")

        self.console_textbox = ctk.CTkTextbox(
            self.console_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            activate_scrollbars=True
        )
        self.console_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    def _check_environment(self):
        """Asegura variables de entorno para Deno, Python, FFmpeg y Aria2."""
        app_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        internal_dir = os.path.join(app_dir, "_internal")
        extra_paths = [
            internal_dir,
            app_dir,
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python310\Scripts"),
            os.path.expandvars(r"%LOCALAPPDATA%\deno\bin"),
            os.path.expandvars(r"%USERPROFILE%\.deno\bin"),
        ]
        current_path = os.environ.get("PATH", "")
        for p in extra_paths:
            if os.path.exists(p) and p not in current_path:
                current_path = p + os.pathsep + current_path
        os.environ["PATH"] = current_path

        self._log("⚡ Turbo Descargar v3.0 listo.")
        self._log(f"Carpeta de destino configurada: {self.download_dir}")
        self._log("Acelerador multihilo (16 hilos paralelos nativos): Activo al 100%")

        self._update_cookie_button()
        if self.config.get("browser_cookies"):
            self._log(f"🍪 Anti-Bot: Activo (usando navegador {self.config.get('browser_cookies').capitalize()})")
        elif self._get_cookie_file():
            self._log(f"🍪 Anti-Bot: Activo (usando archivo {os.path.basename(self._get_cookie_file())})")
        else:
            self._log("🍪 Anti-Bot: En espera (Haz clic en 'Cookies' si YouTube bloquea por bot)")

    def _get_config_path(self):
        config_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TurboDescargar")
        try:
            os.makedirs(config_dir, exist_ok=True)
        except Exception:
            pass
        return os.path.join(config_dir, "config.json")

    def _load_config(self):
        try:
            cpath = self._get_config_path()
            if os.path.isfile(cpath):
                with open(cpath, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_config(self):
        try:
            cur_dir = self.dir_entry.get().strip() if hasattr(self, "dir_entry") else self.download_dir
            if cur_dir:
                self.download_dir = cur_dir
            cfg = {
                "download_dir": self.download_dir,
                "turbo_mode": self.turbo_var.get() if hasattr(self, "turbo_var") else True,
                "no_playlist": self.no_playlist_var.get() if hasattr(self, "no_playlist_var") else True,
                "theme": "Dark" if (hasattr(self, "theme_switch") and self.theme_switch.get() == 1) else "Light",
                "browser_cookies": self.config.get("browser_cookies"),
                "cookie_file": self.config.get("cookie_file")
            }
            cpath = self._get_config_path()
            with open(cpath, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _get_cookie_file(self):
        saved = self.config.get("cookie_file")
        if saved and os.path.isfile(saved) and os.path.getsize(saved) > 0:
            return saved
        appdata_cookies = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TurboDescargar", "cookies.txt")
        if os.path.isfile(appdata_cookies) and os.path.getsize(appdata_cookies) > 0:
            return appdata_cookies
        app_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        local_cookies = os.path.join(app_dir, "cookies.txt")
        if os.path.isfile(local_cookies) and os.path.getsize(local_cookies) > 0:
            return local_cookies
        return None

    def _has_cookies(self):
        if self.config.get("browser_cookies"):
            return True
        if self._get_cookie_file():
            return True
        return False

    def _apply_cookie_opts(self, ydl_opts):
        b = self.config.get("browser_cookies")
        if b:
            ydl_opts['cookiesfrombrowser'] = (b, None, None, None)
            return True
        cfile = self._get_cookie_file()
        if cfile:
            ydl_opts['cookiefile'] = cfile
            return True
        return False

    def _update_cookie_button(self):
        if not hasattr(self, "cookies_btn"):
            return
        if self._has_cookies():
            b = self.config.get("browser_cookies")
            txt = f"🍪 {b.capitalize()}" if b else "🍪 Cookies ON"
            self.cookies_btn.configure(
                text=txt,
                fg_color="#059669",
                hover_color="#047857"
            )
        else:
            self.cookies_btn.configure(
                text="🍪 Cookies",
                fg_color="#374151",
                hover_color="#4b5563"
            )

    def _manage_cookies(self):
        win = ctk.CTkToplevel(self)
        win.title("Gestión de Cookies de YouTube (Anti-Bot)")
        win.geometry("530x430")
        win.resizable(False, False)
        win.grab_set()

        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - 265
            y = self.winfo_y() + (self.winfo_height() // 2) - 215
            win.geometry(f"+{x}+{y}")
        except Exception:
            pass

        title = ctk.CTkLabel(
            win,
            text="🍪 Bypass Anti-Bot con Cookies",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title.pack(padx=20, pady=(18, 6))

        desc = ctk.CTkLabel(
            win,
            text="YouTube bloquea a veces consultas automáticas pidiendo 'Sign in to confirm\nyou\\'re not a bot'. Conectar tus cookies permite descargar sin límites ni bloqueos.",
            font=ctk.CTkFont(size=12),
            justify="center",
            text_color="#94a3b8"
        )
        desc.pack(padx=20, pady=(0, 14))

        status_box = ctk.CTkFrame(win, fg_color=("#e2e8f0", "#1e293b"), corner_radius=8)
        status_box.pack(fill="x", padx=24, pady=6)

        def _get_status_text():
            if self.config.get("browser_cookies"):
                return f"✅ Activo: Usando sesión de {self.config.get('browser_cookies').capitalize()}"
            cfile = self._get_cookie_file()
            if cfile:
                return f"✅ Activo: Usando archivo {os.path.basename(cfile)}"
            return "⚪ Estado: Inactivo (Modo anónimo sin cookies)"

        status_lbl = ctk.CTkLabel(
            status_box,
            text=_get_status_text(),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981" if self._has_cookies() else "#94a3b8"
        )
        status_lbl.pack(padx=12, pady=10)

        def _use_firefox():
            try:
                import yt_dlp
                ydl = yt_dlp.YoutubeDL({'cookiesfrombrowser': ('firefox', None, None, None), 'quiet': True})
                self.config["browser_cookies"] = "firefox"
                self.config["cookie_file"] = None
                self._save_config()
                self._update_cookie_button()
                status_lbl.configure(text=_get_status_text(), text_color="#10b981")
                self._log("[ANTI-BOT] Sesión de Firefox activada con éxito para YouTube.")
                messagebox.showinfo("Éxito", "¡Sesión de Firefox vinculada correctamente!\nAnti-Bot activado.")
            except Exception as ex:
                messagebox.showerror("Error", f"No se pudieron leer las cookies de Firefox:\n{ex}")

        ff_btn = ctk.CTkButton(
            win,
            text="🦊 Conectar con Firefox (1 Clic Automático)",
            height=38,
            fg_color="#e11d48",
            hover_color="#be123c",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=_use_firefox
        )
        ff_btn.pack(fill="x", padx=24, pady=(12, 6))

        def _import_file():
            f = filedialog.askopenfilename(
                title="Selecciona archivo cookies.txt",
                filetypes=[("Archivos de cookies", "*.txt"), ("Todos los archivos", "*.*")]
            )
            if f and os.path.isfile(f):
                dest_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TurboDescargar")
                os.makedirs(dest_dir, exist_ok=True)
                dest_file = os.path.join(dest_dir, "cookies.txt")
                try:
                    shutil.copy2(f, dest_file)
                    self.config["cookie_file"] = dest_file
                    self.config["browser_cookies"] = None
                    self._save_config()
                    self._update_cookie_button()
                    status_lbl.configure(text=_get_status_text(), text_color="#10b981")
                    self._log(f"[ANTI-BOT] Archivo cookies.txt importado desde {f}.")
                    messagebox.showinfo("Éxito", "¡Archivo cookies.txt guardado y activado correctamente!")
                except Exception as ex:
                    messagebox.showerror("Error", f"Error al guardar cookies.txt: {ex}")

        file_btn = ctk.CTkButton(
            win,
            text="📂 Cargar archivo cookies.txt (Chrome / Edge / Brave)",
            height=38,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=_import_file
        )
        file_btn.pack(fill="x", padx=24, pady=6)

        def _clear_cookies():
            self.config["browser_cookies"] = None
            self.config["cookie_file"] = None
            appdata_cookies = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TurboDescargar", "cookies.txt")
            if os.path.isfile(appdata_cookies):
                try:
                    os.remove(appdata_cookies)
                except Exception:
                    pass
            self._save_config()
            self._update_cookie_button()
            status_lbl.configure(text=_get_status_text(), text_color="#94a3b8")
            self._log("[ANTI-BOT] Cookies eliminadas. Modo anónimo restaurado.")
            messagebox.showinfo("Cookies", "Se han eliminado las cookies configuradas.")

        clear_btn = ctk.CTkButton(
            win,
            text="🗑️ Desactivar Cookies (Modo Anónimo)",
            height=34,
            fg_color="#4b5563",
            hover_color="#374151",
            command=_clear_cookies
        )
        clear_btn.pack(fill="x", padx=24, pady=6)

        tip_lbl = ctk.CTkLabel(
            win,
            text="Tip para Chrome/Edge/Brave: Usa la extensión gratuita\n'Get cookies.txt LOCALLY' para exportar cookies de youtube.com en 1 clic.",
            font=ctk.CTkFont(size=11),
            text_color="#64748b"
        )
        tip_lbl.pack(padx=20, pady=(10, 0))

    def _get_ffmpeg_location(self):
        """Busca la ruta de ffmpeg.exe en la app o en el sistema."""
        app_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        candidates = [
            os.path.join(app_dir, "_internal"),
            os.path.join(app_dir, "_internal", "ffmpeg.exe"),
            os.path.join(app_dir, "ffmpeg.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
            shutil.which("ffmpeg.exe"),
            shutil.which("ffmpeg"),
        ]
        for c in candidates:
            if c and (os.path.isfile(c) or os.path.isdir(c)):
                if os.path.isdir(c):
                    if os.path.isfile(os.path.join(c, "ffmpeg.exe")):
                        return c
                else:
                    return c
        return None

    def _toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")
        self._save_config()

    def _toggle_console(self):
        if self.toggle_console_var.get():
            self.console_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        else:
            self.console_textbox.pack_forget()

    def _sanitize_url(self, text):
        if not text:
            return ""
        text = text.strip()
        if text.startswith("batch:"):
            return text
        # 1. Enlace estándar de YouTube (youtube.com o youtu.be)
        m = re.search(r'(https?://(?:www\.)?(?:youtube\.com/(?:watch\?[^\s]*v=|embed/|v/|shorts/)|youtu\.be/)([\w\-]{11}))', text)
        if m:
            return f"https://www.youtube.com/watch?v={m.group(2)}"
        # 2. Copiado desde log de consola [youtube] VIDEO_ID: ...
        m_log = re.search(r'\[youtube\]\s+([\w\-]{11})', text)
        if m_log:
            return f"https://www.youtube.com/watch?v={m_log.group(1)}"
        # 3. ID de video puro de 11 caracteres
        if re.fullmatch(r'[\w\-]{11}', text):
            return f"https://www.youtube.com/watch?v={text}"
        # 4. Cualquier otra URL válida http/https
        m_http = re.search(r'https?://[^\s"\'<>]+', text)
        if m_http:
            return m_http.group(0)
        return ""

    def _paste_and_analyze(self):
        try:
            text = self.clipboard_get().strip()
            clean_url = self._sanitize_url(text)
            if clean_url:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clean_url)
                self._start_analyze_thread()
            else:
                self.status_label.configure(
                    text="El portapapeles no contiene un enlace de YouTube válido.",
                    text_color="#f59e0b"
                )
        except Exception:
            pass

    def _load_txt_file(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de enlaces",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if file_path:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, f"batch:{file_path}")
            self.format_menu.configure(values=self.default_formats)
            self.format_var.set(self.default_formats[0])
            self.info_card.pack_forget()
            self._log(f"[INFO] Lista seleccionada: {file_path}")
            self.status_label.configure(text=f"Lista cargada: {os.path.basename(file_path)}", text_color="#10b981")

    def _browse_folder(self):
        selected = filedialog.askdirectory(title="Seleccionar carpeta de descargas", initialdir=self.download_dir)
        if selected:
            self.download_dir = selected
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, selected)
            self._save_config()

    def _open_download_dir(self):
        target = self.dir_entry.get().strip() or self.download_dir
        if os.path.exists(target):
            os.startfile(target)
        else:
            messagebox.showwarning("Aviso", "La carpeta seleccionada aún no existe.")

    def _clear_console(self):
        self.console_textbox.delete("1.0", "end")

    def _log(self, text):
        self.console_textbox.insert("end", text + "\n")
        self.console_textbox.see("end")

    def _start_analyze_thread(self):
        if self.is_analyzing:
            return

        raw_url = self.url_entry.get().strip()
        if not raw_url or raw_url.startswith("batch:"):
            return

        url = self._sanitize_url(raw_url)
        if not url:
            self.status_label.configure(
                text="Por favor ingresa un enlace de YouTube válido (ej: https://www.youtube.com/watch?v=...)",
                text_color="#ef4444"
            )
            return

        # Reflejar de inmediato la URL limpia en el campo de texto
        if url != raw_url:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, url)

        self.is_analyzing = True
        self.analyze_btn.configure(state="disabled", text="🔍 Consultando...")
        self.status_label.configure(text="Estado: Consultando resoluciones reales en YouTube...", text_color="#60a5fa")

        def _worker():
            try:
                import yt_dlp
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'skip_download': True
                }
                self._apply_cookie_opts(ydl_opts)

                info = None
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception as ex_first:
                    err_msg = str(ex_first).lower()
                    if any(w in err_msg for w in ("bot", "sign in", "confirm you", "403", "captcha")):
                        # 1. Probar bypass automático con Firefox si aún no hay cookies configuradas
                        if not self.config.get("browser_cookies") and not self._get_cookie_file():
                            try:
                                self.after(0, self._log, "[ANTI-BOT] YouTube solicitó verificación. Probando sesión de Firefox automáticamente...")
                                retry_opts = dict(ydl_opts)
                                retry_opts['cookiesfrombrowser'] = ('firefox', None, None, None)
                                with yt_dlp.YoutubeDL(retry_opts) as ydl_ff:
                                    info = ydl_ff.extract_info(url, download=False)
                                    self.config["browser_cookies"] = "firefox"
                                    self._save_config()
                                    self.after(0, self._update_cookie_button)
                                    self.after(0, self._log, "[ANTI-BOT] ¡Bypass automático exitoso con Firefox! Sesión guardada.")
                            except Exception:
                                pass

                        # 2. Si todavía no hay info, intentar clientes móviles alternativos
                        if not info:
                            try:
                                self.after(0, self._log, "[ANTI-BOT] Probando cliente alternativo...")
                                alt_opts = dict(ydl_opts)
                                alt_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'visionos', 'default']}}
                                with yt_dlp.YoutubeDL(alt_opts) as ydl_alt:
                                    info = ydl_alt.extract_info(url, download=False)
                            except Exception:
                                pass

                    if not info:
                        raise ex_first

                title = info.get("title", "Video de YouTube")
                uploader = info.get("uploader", "Desconocido")
                duration = info.get("duration_string", "")
                self.current_video_title = title

                formats = info.get("formats", [])
                height_map = {}
                for f in formats:
                    h = f.get("height")
                    if not h or f.get("vcodec") == "none":
                        continue
                    fps = f.get("fps") or 30
                    f_id = f.get("format_id")
                    proto = (f.get("protocol") or "").lower()
                    is_https = proto.startswith("http") and not ("m3u8" in proto or "hls" in proto)

                    if h not in height_map:
                        height_map[h] = {
                            "height": h,
                            "fps": int(fps),
                            "format_id": f_id,
                            "is_https": is_https
                        }
                    else:
                        existing = height_map[h]
                        # 1. Priorizar HTTPS directo sobre m3u8 (evita fragmentos perdidos y desincronización)
                        if is_https and not existing.get("is_https"):
                            height_map[h] = {
                                "height": h,
                                "fps": int(fps),
                                "format_id": f_id,
                                "is_https": is_https
                            }
                        # 2. Si ambos tienen el mismo tipo de protocolo, comparar fps
                        elif is_https == existing.get("is_https") and fps > existing["fps"]:
                            height_map[h] = {
                                "height": h,
                                "fps": int(fps),
                                "format_id": f_id,
                                "is_https": is_https
                            }

                # Construir opciones basadas en las resoluciones REALES del archivo
                sorted_heights = sorted(height_map.keys(), reverse=True)
                new_options = []
                self.format_height_map.clear()

                for h in sorted_heights:
                    info_h = height_map[h]
                    fps_str = f" {info_h['fps']}fps" if info_h["fps"] > 30 else ""
                    if h >= 2160:
                        label = f"🎬 4K 2160p{fps_str} (Ultra HD 3840x2160)"
                    elif h >= 1440:
                        label = f"🎬 1440p{fps_str} (2K Quad HD 2560x1440)"
                    elif h >= 1080:
                        label = f"🎬 1080p{fps_str} (Full HD 1920x1080)"
                    elif h >= 720:
                        label = f"🎬 720p{fps_str} (HD 1280x720)"
                    elif h >= 480:
                        label = f"🎬 480p{fps_str} (SD)"
                    elif h >= 360:
                        label = f"🎬 360p{fps_str}"
                    else:
                        label = f"🎬 {h}p{fps_str}"

                    new_options.append(label)
                    self.format_height_map[label] = {
                        "height": h,
                        "format_id": info_h["format_id"]
                    }

                # Opciones de audio
                mp3_label = "🎵 Audio: MP3 Máxima Calidad (320 kbps)"
                orig_label = "🎼 Audio: Calidad Original sin recodificar"
                new_options.append(mp3_label)
                new_options.append(orig_label)
                self.format_height_map[mp3_label] = "mp3"
                self.format_height_map[orig_label] = "original"

                res_summary = ", ".join([f"{h}p" for h in sorted_heights])
                card_text = f"🎬 {title}\n👤 Canal: {uploader} | ⏱️ Duración: {duration}\n📺 Resoluciones reales disponibles en YouTube: {res_summary}"

                self.after(0, self._apply_real_formats, new_options, card_text)
                self.after(0, self._log, f"[INFO] Calidades reales cargadas para: '{title}' ({res_summary})")

            except Exception as e:
                err_text = str(e)
                self.after(0, self._log, f"[ERROR AL CARGAR CALIDADES] {err_text}")
                if any(w in err_text.lower() for w in ("bot", "sign in", "confirm you", "403")):
                    tip_msg = "YouTube activó verificación anti-bot. Haz clic en '🍪 Cookies' para activar Firefox o cookies.txt."
                    self.after(0, lambda: self.status_label.configure(text=tip_msg, text_color="#f59e0b"))
                    self.after(0, self._log, f"[ANTI-BOT] {tip_msg}")
                else:
                    self.after(0, lambda: self.status_label.configure(text=f"Error consultando calidades: {err_text}", text_color="#ef4444"))
            finally:
                self.is_analyzing = False
                self.after(0, lambda: self.analyze_btn.configure(state="normal", text="🔍 Cargar Calidades"))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_real_formats(self, options, card_text):
        if options:
            self.format_menu.configure(values=options)
            # Seleccionar automáticamente la máxima resolución real disponible
            self.format_var.set(options[0])
            self.info_label.configure(text=card_text)
            self.info_card.pack(fill="x", padx=14, pady=(0, 10))
            self.status_label.configure(
                text=f"¡Resoluciones reales cargadas! Máxima detectada: {options[0].split('(')[0].strip()}",
                text_color="#10b981"
            )

    def _start_download_thread(self):
        if self.is_downloading:
            return

        raw_url = self.url_entry.get().strip()
        if not raw_url:
            messagebox.showwarning("Atención", "Por favor ingresa un enlace de YouTube o selecciona un archivo TXT.")
            return

        target_url = raw_url if raw_url.startswith("batch:") else self._sanitize_url(raw_url)
        if not target_url:
            messagebox.showwarning("Atención", "El enlace ingresado no parece una URL válida de YouTube.")
            return

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ Descargando...")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.status_label.configure(text="Estado: Iniciando descarga...", text_color="#60a5fa")

        thread = threading.Thread(target=self._run_download, args=(target_url,), daemon=True)
        thread.start()

    def _get_ytdlp_cmd(self):
        """
        Obtiene el comando para ejecutar yt-dlp con protección DoH garantizada.
        Prioriza el despachador interno que incluye bypass de censura/envenenamiento DNS.
        """
        # 1. Si es ejecutable congelado (PyInstaller), usar el despachador interno empaquetado
        if getattr(sys, 'frozen', False):
            return [sys.executable, "--internal-ytdlp"]

        # 2. Si se ejecuta desde Python directamente, invocar el módulo con el mismo intérprete
        py_exe = sys.executable
        if py_exe and os.path.isfile(py_exe) and not py_exe.lower().endswith("turbodescargar.exe"):
            return [py_exe, "-m", "yt_dlp"]

        # 3. Buscar yt-dlp.exe explícitamente en el PATH como respaldo
        exe = shutil.which("yt-dlp.exe")
        if exe and os.path.isfile(exe) and not exe.lower().endswith((".bat", ".cmd")):
            return [exe]

        return [sys.executable, "--internal-ytdlp"]

    def _run_download(self, target_url):
        # Guardar carpeta y preferencias automáticamente al iniciar descarga
        self._save_config()

        out_dir = os.path.realpath(self.dir_entry.get().strip() or self.download_dir)
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            pass

        selected_option = self.format_var.get()
        ignore_playlist = self.no_playlist_var.get()

        out_template = os.path.join(out_dir, "%(title)s.%(ext)s")

        cmd = list(self._get_ytdlp_cmd()) + ["--newline"]

        # Vincular ffmpeg garantizado para unión de audio y video
        ffmpeg_bin = self._get_ffmpeg_location()
        if ffmpeg_bin:
            cmd.extend(["--ffmpeg-location", ffmpeg_bin])

        if ignore_playlist:
            cmd.append("--no-playlist")

        # ⚡ ACELERADOR DE ANCHO DE BANDA AL 100% (Modo Turbo Nativo)
        if self.turbo_var.get():
            cmd.extend([
                "--concurrent-fragments", "16",
                "--buffer-size", "16M"
            ])

        # Parámetros de red resilientes y plantilla de progreso determinista
        cmd.extend([
            "--socket-timeout", "5",
            "--retries", "3",
            "--fragment-retries", "3",
            "--no-colors",
            "--progress-template", "download:[PGBAR]%(progress._percent_str)s|%(progress._total_bytes_estimate_str,progress._total_bytes_str)s|%(progress._speed_str)s|%(progress._eta_str)s"
        ])

        # Manejo de Cookies Anti-Bot
        b = self.config.get("browser_cookies")
        if b:
            cmd.extend(["--cookies-from-browser", b])
        else:
            cfile = self._get_cookie_file()
            if cfile:
                cmd.extend(["--cookies", cfile])

        # Selector de audio universalmente compatible con contenedores MP4:
        # Priorizar m4a/aac (reproducible en todos los reproductores de Windows/móviles/smartTVs sin quedar mudo)
        # y como respaldo opus/bestaudio
        audio_pref = "bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio"

        # Asignar formato REAL seleccionado
        target_info = self.format_height_map.get(selected_option)

        if selected_option.startswith("🎵") or target_info == "mp3" or "MP3" in selected_option:
            cmd.extend(["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"])
        elif selected_option.startswith("🎼") or target_info == "original" or "Original" in selected_option:
            cmd.extend(["--extract-audio", "--audio-format", "best"])
        elif isinstance(target_info, dict):
            target_h = target_info.get("height")
            fmt_id = target_info.get("format_id")
            # Selección estricta y compatible:
            # 1. format_id detectado + audio compatible (m4a/aac)
            # 2. mejor video de esa altura directo por http + audio compatible
            # 3. mejor video de esa altura o menor + mejor audio
            fmt_selector = (
                f"{fmt_id}+{audio_pref}/"
                f"bestvideo[height={target_h}][protocol^=http]+{audio_pref}/"
                f"bestvideo[height={target_h}]+bestaudio/"
                f"bestvideo[height<={target_h}]+bestaudio/best"
            )
            cmd.extend([
                "-f", fmt_selector,
                "--merge-output-format", "mp4"
            ])
        elif isinstance(target_info, int):
            fmt_selector = (
                f"bestvideo[height={target_info}][protocol^=http]+{audio_pref}/"
                f"bestvideo[height={target_info}]+bestaudio/"
                f"bestvideo[height<={target_info}]+bestaudio/best"
            )
            cmd.extend([
                "-f", fmt_selector,
                "--merge-output-format", "mp4"
            ])
        else:
            fmt_selector = f"bestvideo[protocol^=http]+{audio_pref}/bestvideo+bestaudio/best"
            cmd.extend([
                "-f", fmt_selector,
                "--merge-output-format", "mp4"
            ])

        cmd.extend(["-o", out_template])

        # Manejo de archivo batch o URL única
        if target_url.startswith("batch:"):
            batch_path = target_url.replace("batch:", "").strip()
            cmd.extend(["-a", batch_path])
            self.after(0, self._log, f"\n[INICIO] Descargando lista: {batch_path}")
        else:
            cmd.append(target_url)
            self.after(0, self._log, f"\n[INICIO] Descargando: {target_url}\n[CALIDAD] {selected_option}")

        self.after(0, self._log, f"[COMANDO] {' '.join(cmd)}\n")

        pgbar_re = re.compile(r'\[PGBAR\]\s*([\d\.]+)%\|([^|]*)\|([^|]*)\|([^|\r\n]*)')
        progress_re = re.compile(r'\[download\]\s+([\d\.]+)%(?:\s+of\s+~?\s*([^\s]+))?(?:\s+at\s+([^\s]+))?(?:\s+(?:ETA\s+|in\s+)([^\s]+))?')
        aria2_re = re.compile(r'\[#[0-9a-fA-F]+\s+([^\s/]+)/([^\s(]+)\(([\d\.]+)%\)\s+CN:\d+\s+DL:([^\s]+)(?:\s+ETA:([^\s\]]+))?')

        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                bufsize=1
            )

            for raw_chunk in self.current_process.stdout:
                # Tratar múltiples actualizaciones en caso de retornos de carro \r
                segments = [s.strip() for s in raw_chunk.replace('\r', '\n').split('\n') if s.strip()]
                for clean_line in segments:
                    # Limpiar secuencias de escape ANSI por seguridad
                    clean_line_no_ansi = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', clean_line)

                    # Si es la línea de plantilla de progreso determinista [PGBAR]
                    pg_match = pgbar_re.search(clean_line_no_ansi)
                    if pg_match:
                        percent_str, total_size, speed, eta = pg_match.groups()
                        try:
                            p_val = float(percent_str) / 100.0
                            size_str = total_size.strip() if total_size.strip() and total_size.strip() != "N/A" else ""
                            spd_str = speed.strip() if speed.strip() else ""
                            eta_str = eta.strip() if eta.strip() else ""
                            parts = [f"{percent_str}%"]
                            if size_str: parts.append(f"de {size_str}")
                            if spd_str: parts.append(f"a {spd_str}")
                            if eta_str: parts.append(f"(Restante: {eta_str})")
                            status_msg = f"Descargando: {' '.join(parts)}"
                            self.after(0, self._update_progress, p_val, status_msg)
                        except ValueError:
                            pass
                        continue

                    self.after(0, self._log, clean_line)

                    # Detección de progreso nativo yt-dlp (fallback)
                    match = progress_re.search(clean_line_no_ansi)
                    if match:
                        percent_str, total_size, speed, eta = match.groups()
                        try:
                            p_val = float(percent_str) / 100.0
                            size_info = f" de {total_size}" if total_size else ""
                            spd_info = f" a {speed}" if speed else ""
                            eta_info = f" (Restante: {eta})" if eta else ""
                            status_msg = f"Descargando: {percent_str}%{size_info}{spd_info}{eta_info}"
                            self.after(0, self._update_progress, p_val, status_msg)
                        except ValueError:
                            pass
                        continue

                    # Detección de progreso acelerador aria2c
                    aria_match = aria2_re.search(clean_line_no_ansi)
                    if aria_match:
                        _cur, total_size, percent_str, speed, eta = aria_match.groups()
                        try:
                            p_val = float(percent_str) / 100.0
                            eta_str = eta if eta else "en curso"
                            status_msg = f"Turbo aria2c: {percent_str}% de {total_size} a {speed} (Restante: {eta_str})"
                            self.after(0, self._update_progress, p_val, status_msg)
                        except ValueError:
                            pass
                        continue

                    if "[ExtractAudio]" in clean_line:
                        self.after(0, self._update_status, "Extrayendo audio a máxima fidelidad...", "#f59e0b")
                    elif "[Merger]" in clean_line:
                        self.after(0, self._update_status, "Uniendo pistas de video y audio en MP4...", "#f59e0b")

            self.current_process.wait()
            returncode = self.current_process.returncode

            if returncode == 0:
                self.after(0, self._on_download_complete, True, "¡Descarga finalizada con éxito!")
            else:
                self.after(0, self._on_download_complete, False, f"Proceso finalizado con código {returncode}. Revisa la consola.")

        except Exception as e:
            self.after(0, self._on_download_complete, False, f"Error durante la descarga: {str(e)}")
        finally:
            self.current_process = None

    def _update_progress(self, val, msg):
        self.progress_bar.set(val)
        self.status_label.configure(text=f"Estado: {msg}", text_color="#60a5fa")

    def _update_status(self, msg, color="#60a5fa"):
        self.status_label.configure(text=f"Estado: {msg}", text_color=color)

    def _on_download_complete(self, success, message):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="🚀 Descargar Selección")
        self.cancel_btn.configure(state="disabled")

        if success:
            self.progress_bar.set(1.0)
            self.status_label.configure(text=f"Estado: {message}", text_color="#10b981")
            self._log(f"\n[ÉXITO] {message}\n")
            if messagebox.askyesno("Descarga Finalizada", f"{message}\n\n¿Deseas abrir la carpeta de descargas ahora?"):
                self._open_download_dir()
        else:
            self.status_label.configure(text=f"Estado: {message}", text_color="#ef4444")
            self._log(f"\n[ERROR] {message}\n")

    def _cancel_download(self):
        if self.current_process and self.is_downloading:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.current_process.pid)], capture_output=True)
                else:
                    self.current_process.terminate()
                self._log("\n[AVISO] Proceso cancelado por el usuario.\n")
                self.status_label.configure(text="Estado: Descarga cancelada", text_color="#ef4444")
            except Exception as e:
                self._log(f"[ERROR] Error al cancelar: {e}")
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="🚀 Descargar Selección")
        self.cancel_btn.configure(state="disabled")

    def _on_close(self):
        self._save_config()
        if self.current_process:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.current_process.pid)], capture_output=True)
                else:
                    self.current_process.kill()
            except Exception:
                pass
        self.destroy()
        sys.exit(0)

    def _update_ytdlp(self):
        def _task():
            self._log("\n[*] Comprobando actualizaciones de yt-dlp...")
            self.update_btn.configure(state="disabled", text="⏳ Actualizando...")
            try:
                res = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8"
                )
                self.after(0, self._log, res.stdout)
                if res.returncode == 0:
                    self.after(0, lambda: messagebox.showinfo("Actualización", "yt-dlp actualizado a la versión más reciente."))
                else:
                    self.after(0, self._log, res.stderr)
            except Exception as e:
                self.after(0, self._log, f"[ERROR] {e}")
            finally:
                self.after(0, lambda: self.update_btn.configure(state="normal", text="🔄 Actualizar yt-dlp"))

        threading.Thread(target=_task, daemon=True).start()

if __name__ == "__main__":
    app = TurboDownloaderApp()
    app.mainloop()
