import re
import html
import subprocess
import threading
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import os
from datetime import datetime

import whisper
from yt_dlp import YoutubeDL


class YouTubeSummarizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Phofytte - YouTube Summarizer")
        self.root.geometry("1100x800")
        
        # Configurar colores (verde claro con negro/morado)
        self.colors = {
            "bg_primary": "#0a0a0f",  # Negro con tono morado
            "bg_secondary": "#1a1a2e",  # Morado oscuro
            "bg_card": "#16213e",  # Azul morado oscuro
            "bg_input": "#1e1e32",
            "fg_primary": "#e0e0e0",
            "fg_secondary": "#b8b8d0",
            "green_light": "#4ade80",  # Verde claro
            "green_dark": "#22c55e",
            "purple": "#8b5cf6",
            "border": "#2d2d44",
            "hover": "#2a2a4a",
            "text_shadow": "#4ade80",
        }
        
        # Variables
        self.url_var = tk.StringVar()
        self.whisper_model_var = tk.StringVar(value="base")
        self.ollama_model_var = tk.StringVar(value="deepseek-r1:8b")
        self.status_var = tk.StringVar(value="💡 Listo")
        self.progress_var = tk.DoubleVar(value=0)
        self.auto_summarize_var = tk.BooleanVar(value=False)
        self.video_title = ""
        self.video_id = ""
        
        # Variables para almacenar resultados
        self.transcription_text = ""
        self.summary_text = ""
        self.audio_file_path = None
        self.current_url = ""
        
        # Configuración de atajos de teclado
        self.keyboard_shortcuts = {
            "paste": "Control-v",
            "process": "Control-p",
            "summarize": "Control-r",
            "copy_trans": "Control-Shift-c",
            "copy_summary": "Control-Shift-s",
            "save_trans": "Control-Shift-x",
            "save_summary": "Control-Shift-z",
            "close": "Control-q",
            "help": "F1"
        }
        
        self.setup_ui()
        self.apply_styles()
        self.setup_keyboard_shortcuts()
        
    def setup_ui(self):
        # Configurar ventana principal
        self.root.configure(bg=self.colors["bg_primary"])
        
        # Frame principal con padding
        main_frame = tk.Frame(
            self.root,
            bg=self.colors["bg_primary"],
            padx=30,
            pady=30
        )
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== BARRA SUPERIOR =====
        top_bar = tk.Frame(main_frame, bg=self.colors["bg_primary"], height=50)
        top_bar.pack(fill=tk.X, pady=(0, 20))
        top_bar.pack_propagate(False)
        
        # Título de la aplicación
        title_label = tk.Label(
            top_bar,
            text="Phofytte",
            font=('Segoe UI', 18, 'bold'),
            bg=self.colors["bg_primary"],
            fg=self.colors["green_light"]
        )
        title_label.pack(side=tk.LEFT)
        
        # Botón de cerrar (X) - estilo moderno
        close_btn = tk.Button(
            top_bar,
            text="✕",
            font=('Segoe UI', 14),
            bg=self.colors["bg_primary"],
            fg=self.colors["fg_secondary"],
            relief=tk.FLAT,
            cursor="hand2",
            command=self.root.quit
        )
        close_btn.pack(side=tk.RIGHT, padx=(0, 0))
        
        # ===== MENÚ DESPLEGABLE (Esquina superior derecha) =====
        menu_frame = tk.Frame(top_bar, bg=self.colors["bg_primary"])
        menu_frame.pack(side=tk.RIGHT, padx=(20, 10))
        
        # Botón de menú (hamburguesa)
        self.menu_btn = tk.Menubutton(
            menu_frame,
            text="☰",
            font=('Segoe UI', 20),
            bg=self.colors["bg_primary"],
            fg=self.colors["green_light"],
            relief=tk.FLAT,
            cursor="hand2",
            activebackground=self.colors["hover"]
        )
        self.menu_btn.pack()
        
        # Menú desplegable
        menu = tk.Menu(
            self.menu_btn,
            tearoff=0,
            bg=self.colors["bg_secondary"],
            fg=self.colors["fg_primary"],
            activebackground=self.colors["hover"],
            activeforeground=self.colors["green_light"],
            font=('Segoe UI', 10)
        )
        self.menu_btn.config(menu=menu)
        
        # Opciones del menú
        menu.add_command(
            label="📥 Download Playlist",
            command=self.download_playlist
        )
        menu.add_separator()
        menu.add_command(
            label="⚙️ Settings",
            command=self.show_settings_window
        )
        menu.add_command(
            label="⌨️ Keyboard Shortcuts",
            command=self.show_shortcuts_window
        )
        menu.add_command(
            label="📋 Video History",
            command=self.show_history
        )
        menu.add_command(
            label="🎨 Theme",
            command=self.show_theme_options
        )
        menu.add_separator()
        menu.add_command(
            label="❓ Help (F1)",
            command=self.show_help
        )
        
        # ===== SHORTCUT BUTTON =====
        shortcut_frame = tk.Frame(main_frame, bg=self.colors["bg_primary"])
        shortcut_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Botón pegar con shortcut CTRL+V
        paste_btn = tk.Button(
            shortcut_frame,
            text="📋 Click to paste video link from clipboard",
            font=('Segoe UI', 11),
            bg=self.colors["bg_card"],
            fg=self.colors["fg_secondary"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8,
            command=self.paste_from_clipboard
        )
        paste_btn.pack(side=tk.LEFT)
        
        # Indicador CTRL+V
        ctrlv_label = tk.Label(
            shortcut_frame,
            text="CTRL+V",
            font=('Segoe UI', 10, 'bold'),
            bg=self.colors["bg_card"],
            fg=self.colors["green_light"],
            relief=tk.FLAT,
            padx=10,
            pady=4
        )
        ctrlv_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # ===== URL INPUT =====
        url_frame = tk.Frame(main_frame, bg=self.colors["bg_primary"])
        url_frame.pack(fill=tk.X, pady=(0, 15))
        
        url_entry = tk.Entry(
            url_frame,
            textvariable=self.url_var,
            font=('Segoe UI', 11),
            bg=self.colors["bg_input"],
            fg=self.colors["fg_primary"],
            relief=tk.FLAT,
            insertbackground=self.colors["green_light"],
            highlightthickness=2,
            highlightcolor=self.colors["green_light"],
            highlightbackground=self.colors["border"]
        )
        url_entry.pack(fill=tk.X, ipady=10)  # Usar ipady en lugar de pady
        
        # ===== MODEL SELECTORS =====
        models_frame = tk.Frame(main_frame, bg=self.colors["bg_primary"])
        models_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Whisper model
        whisper_frame = tk.Frame(models_frame, bg=self.colors["bg_primary"])
        whisper_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        whisper_label = tk.Label(
            whisper_frame,
            text="Whisper:",
            font=('Segoe UI', 10),
            bg=self.colors["bg_primary"],
            fg=self.colors["fg_secondary"]
        )
        whisper_label.pack(side=tk.LEFT, padx=(0, 10))
        
        whisper_combo = ttk.Combobox(
            whisper_frame,
            textvariable=self.whisper_model_var,
            values=["tiny", "base", "small", "medium", "large"],
            state="readonly",
            width=12,
            font=('Segoe UI', 10)
        )
        whisper_combo.pack(side=tk.LEFT)
        self.style_combobox(whisper_combo)
        
        # Ollama model
        ollama_frame = tk.Frame(models_frame, bg=self.colors["bg_primary"])
        ollama_frame.pack(side=tk.LEFT)
        
        ollama_label = tk.Label(
            ollama_frame,
            text="Ollama:",
            font=('Segoe UI', 10),
            bg=self.colors["bg_primary"],
            fg=self.colors["fg_secondary"]
        )
        ollama_label.pack(side=tk.LEFT, padx=(0, 10))
        
        ollama_combo = ttk.Combobox(
            ollama_frame,
            textvariable=self.ollama_model_var,
            values=["deepseek-r1:8b", "llama3.2", "mistral", "phi", "tinyllama"],
            state="readonly",
            width=15,
            font=('Segoe UI', 10)
        )
        ollama_combo.pack(side=tk.LEFT)
        self.style_combobox(ollama_combo)
        
        # ===== ACTION BUTTONS =====
        actions_frame = tk.Frame(main_frame, bg=self.colors["bg_primary"])
        actions_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Procesar video
        self.process_btn = self.create_styled_button(
            actions_frame,
            "▶ Procesa video (Ctrl+P)",
            self.process_video,
            self.colors["green_light"],
            self.colors["bg_secondary"]
        )
        self.process_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Resumir
        self.summarize_btn = self.create_styled_button(
            actions_frame,
            "📝 Resumir (Ctrl+R)",
            self.summarize_transcription,
            self.colors["purple"],
            self.colors["bg_secondary"],
            state="disabled"
        )
        self.summarize_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Auto-resumir checkbox
        auto_frame = tk.Frame(actions_frame, bg=self.colors["bg_primary"])
        auto_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        auto_check = tk.Checkbutton(
            auto_frame,
            text="Auto-resumir",
            variable=self.auto_summarize_var,
            font=('Segoe UI', 10),
            bg=self.colors["bg_primary"],
            fg=self.colors["fg_secondary"],
            selectcolor=self.colors["bg_secondary"],
            relief=tk.FLAT,
            cursor="hand2"
        )
        auto_check.pack()
        
        # ===== CONTENT TABS =====
        # Crear notebook personalizado
        notebook_frame = tk.Frame(
            main_frame,
            bg=self.colors["bg_secondary"],
            padx=2,
            pady=2
        )
        notebook_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tabs
        tabs_frame = tk.Frame(notebook_frame, bg=self.colors["bg_secondary"])
        tabs_frame.pack(fill=tk.X)
        
        # Tab 1 - Transcripción
        trans_tab_btn = tk.Button(
            tabs_frame,
            text="📄 Transcripción",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors["bg_secondary"],
            fg=self.colors["green_light"],
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor="hand2",
            command=lambda: self.switch_tab(0)
        )
        trans_tab_btn.pack(side=tk.LEFT)
        
        # Tab 2 - Resumen
        summary_tab_btn = tk.Button(
            tabs_frame,
            text="📋 Resumen",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors["bg_secondary"],
            fg=self.colors["fg_secondary"],
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor="hand2",
            command=lambda: self.switch_tab(1)
        )
        summary_tab_btn.pack(side=tk.LEFT)
        
        # Contenedor de tabs
        self.tab_container = tk.Frame(notebook_frame, bg=self.colors["bg_card"])
        self.tab_container.pack(fill=tk.BOTH, expand=True)
        
        # Tab de Transcripción
        self.trans_frame = tk.Frame(self.tab_container, bg=self.colors["bg_card"])
        self.trans_frame.pack(fill=tk.BOTH, expand=True)
        
        # Botones de transcripción
        trans_controls = tk.Frame(self.trans_frame, bg=self.colors["bg_card"])
        trans_controls.pack(fill=tk.X, pady=(10, 5), padx=10)
        
        copy_trans_btn = self.create_small_button(
            trans_controls,
            "📋 Copiar (Ctrl+Shift+C)",
            lambda: self.copy_to_clipboard(self.transcription_text, "transcripción")
        )
        copy_trans_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        save_trans_btn = self.create_small_button(
            trans_controls,
            "💾 Guardar (Ctrl+Shift+X)",
            lambda: self.save_single_file(self.transcription_text, "transcripcion", ".txt")
        )
        save_trans_btn.pack(side=tk.LEFT)
        
        # Text area - Transcripción
        self.trans_text = scrolledtext.ScrolledText(
            self.trans_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg=self.colors["bg_input"],
            fg=self.colors["fg_primary"],
            insertbackground=self.colors["green_light"],
            relief=tk.FLAT,
            padx=10,
            pady=10,
            height=15
        )
        self.trans_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Tab de Resumen
        self.summary_frame = tk.Frame(self.tab_container, bg=self.colors["bg_card"])
        
        # Botones de resumen
        summary_controls = tk.Frame(self.summary_frame, bg=self.colors["bg_card"])
        summary_controls.pack(fill=tk.X, pady=(10, 5), padx=10)
        
        copy_summary_btn = self.create_small_button(
            summary_controls,
            "📋 Copiar (Ctrl+Shift+S)",
            lambda: self.copy_to_clipboard(self.summary_text, "resumen")
        )
        copy_summary_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        save_summary_btn = self.create_small_button(
            summary_controls,
            "💾 Guardar (Ctrl+Shift+Z)",
            lambda: self.save_single_file(self.summary_text, "resumen", ".md")
        )
        save_summary_btn.pack(side=tk.LEFT)
        
        # Text area - Resumen
        self.summary_text_widget = scrolledtext.ScrolledText(
            self.summary_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg=self.colors["bg_input"],
            fg=self.colors["fg_primary"],
            insertbackground=self.colors["green_light"],
            relief=tk.FLAT,
            padx=10,
            pady=10,
            height=15
        )
        self.summary_text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # ===== STATUS BAR =====
        status_frame = tk.Frame(main_frame, bg=self.colors["bg_primary"])
        status_frame.pack(fill=tk.X, pady=(15, 0))
        
        # Barra de progreso
        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=100,
            length=300,
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 15))
        
        # Estado
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=('Segoe UI', 10),
            bg=self.colors["bg_primary"],
            fg=self.colors["fg_secondary"]
        )
        status_label.pack(side=tk.LEFT)
        
        # Configurar estilo de la barra de progreso
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Custom.Horizontal.TProgressbar",
            background=self.colors["green_light"],
            troughcolor=self.colors["bg_input"],
            bordercolor=self.colors["bg_primary"],
            lightcolor=self.colors["green_light"],
            darkcolor=self.colors["green_dark"]
        )
        
        self.current_tab = 0
        self.tab_buttons = [trans_tab_btn, summary_tab_btn]
        
    def style_combobox(self, combobox):
        """Aplica estilo a los combobox"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "TCombobox",
            fieldbackground=self.colors["bg_input"],
            background=self.colors["bg_input"],
            foreground=self.colors["fg_primary"],
            selectbackground=self.colors["bg_secondary"],
            selectforeground=self.colors["green_light"],
            borderwidth=0,
            relief="flat"
        )
        combobox.configure(style="TCombobox")
        
    def create_styled_button(self, parent, text, command, color, bg, state="normal"):
        """Crea botones con estilo personalizado"""
        btn = tk.Button(
            parent,
            text=text,
            font=('Segoe UI', 11, 'bold'),
            bg=bg,
            fg=color,
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            command=command,
            state=state
        )
        
        # Efecto hover
        def on_enter(e):
            btn.config(bg=self.colors["hover"])
        def on_leave(e):
            btn.config(bg=bg)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def create_small_button(self, parent, text, command):
        """Crea botones pequeños para las tabs"""
        btn = tk.Button(
            parent,
            text=text,
            font=('Segoe UI', 9),
            bg=self.colors["bg_input"],
            fg=self.colors["green_light"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=4,
            command=command
        )
        
        def on_enter(e):
            btn.config(bg=self.colors["hover"])
        def on_leave(e):
            btn.config(bg=self.colors["bg_input"])
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def apply_styles(self):
        """Aplica estilos adicionales"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Vertical.TScrollbar",
            background=self.colors["bg_secondary"],
            troughcolor=self.colors["bg_primary"],
            bordercolor=self.colors["bg_primary"],
            arrowcolor=self.colors["fg_secondary"],
            relief="flat"
        )
    
    def setup_keyboard_shortcuts(self):
        """Configura los atajos de teclado"""
        self.root.bind('<Control-v>', lambda e: self.paste_from_clipboard())
        self.root.bind('<Control-p>', lambda e: self.process_video())
        self.root.bind('<Control-r>', lambda e: self.summarize_transcription())
        self.root.bind('<Control-Shift-c>', lambda e: self.copy_to_clipboard(self.transcription_text, "transcripción"))
        self.root.bind('<Control-Shift-s>', lambda e: self.copy_to_clipboard(self.summary_text, "resumen"))
        self.root.bind('<Control-Shift-x>', lambda e: self.save_single_file(self.transcription_text, "transcripcion", ".txt"))
        self.root.bind('<Control-Shift-z>', lambda e: self.save_single_file(self.summary_text, "resumen", ".md"))
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<F1>', lambda e: self.show_help())
    
    def switch_tab(self, tab_index):
        """Cambia entre tabs"""
        self.current_tab = tab_index
        
        # Ocultar todas las tabs
        self.trans_frame.pack_forget()
        self.summary_frame.pack_forget()
        
        # Mostrar la tab seleccionada
        if tab_index == 0:
            self.trans_frame.pack(fill=tk.BOTH, expand=True)
            self.tab_buttons[0].config(fg=self.colors["green_light"])
            self.tab_buttons[1].config(fg=self.colors["fg_secondary"])
        else:
            self.summary_frame.pack(fill=tk.BOTH, expand=True)
            self.tab_buttons[0].config(fg=self.colors["fg_secondary"])
            self.tab_buttons[1].config(fg=self.colors["green_light"])
    
    def paste_from_clipboard(self):
        """Pega el contenido del portapapeles en el campo URL"""
        try:
            clipboard_text = self.root.clipboard_get()
            if clipboard_text:
                self.url_var.set(clipboard_text.strip())
                self.update_status("📋 URL pegada desde el portapapeles")
        except:
            self.update_status("⚠️ No se pudo acceder al portapapeles")
    
    def download_playlist(self):
        """Función para descargar playlists"""
        messagebox.showinfo(
            "Download Playlist",
            "Funcionalidad en desarrollo.\nPróximamente podrás descargar playlists completas."
        )
    
    def show_settings_window(self):
        """Ventana de configuración"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("⚙️ Configuración - Phofytte")
        settings_window.geometry("600x500")
        settings_window.configure(bg=self.colors["bg_primary"])
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Frame principal
        main_frame = tk.Frame(settings_window, bg=self.colors["bg_primary"], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title = tk.Label(
            main_frame,
            text="⚙️ Configuración",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors["bg_primary"],
            fg=self.colors["green_light"]
        )
        title.pack(pady=(0, 20))
        
        # Carpeta de descargas
        folder_frame = tk.Frame(main_frame, bg=self.colors["bg_primary"])
        folder_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            folder_frame,
            text="📂 Carpeta de descargas:",
            font=('Segoe UI', 10),
            bg=self.colors["bg_primary"],
            fg=self.colors["fg_secondary"]
        ).pack(anchor=tk.W)
        
        folder_entry = tk.Entry(
            folder_frame,
            font=('Segoe UI', 10),
            bg=self.colors["bg_input"],
            fg=self.colors["fg_primary"],
            relief=tk.FLAT,
            insertbackground=self.colors["green_light"]
        )
        folder_entry.pack(fill=tk.X, ipady=5, pady=5)
        folder_entry.insert(0, "downloads/")
        
        # Atajos de teclado
        shortcuts_frame = tk.Frame(main_frame, bg=self.colors["bg_primary"])
        shortcuts_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        tk.Label(
            shortcuts_frame,
            text="⌨️ Atajos de teclado",
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors["bg_primary"],
            fg=self.colors["green_light"]
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Lista de atajos
        shortcuts_list = tk.Frame(shortcuts_frame, bg=self.colors["bg_secondary"])
        shortcuts_list.pack(fill=tk.BOTH, expand=True)
        
        shortcuts = [
            ("Pegar URL", "Ctrl+V"),
            ("Procesar video", "Ctrl+P"),
            ("Resumir", "Ctrl+R"),
            ("Copiar transcripción", "Ctrl+Shift+C"),
            ("Copiar resumen", "Ctrl+Shift+S"),
            ("Guardar transcripción", "Ctrl+Shift+X"),
            ("Guardar resumen", "Ctrl+Shift+Z"),
            ("Cerrar", "Ctrl+Q"),
            ("Ayuda", "F1")
        ]
        
        for i, (action, shortcut) in enumerate(shortcuts):
            row = tk.Frame(shortcuts_list, bg=self.colors["bg_secondary"])
            row.pack(fill=tk.X, pady=2)
            
            tk.Label(
                row,
                text=action,
                font=('Segoe UI', 10),
                bg=self.colors["bg_secondary"],
                fg=self.colors["fg_primary"],
                width=20,
                anchor=tk.W
            ).pack(side=tk.LEFT, padx=10)
            
            tk.Label(
                row,
                text=shortcut,
                font=('Segoe UI', 10, 'bold'),
                bg=self.colors["bg_secondary"],
                fg=self.colors["green_light"],
                width=15,
                anchor=tk.W
            ).pack(side=tk.LEFT, padx=10)
        
        # Botón cerrar
        close_btn = tk.Button(
            main_frame,
            text="Cerrar",
            font=('Segoe UI', 10),
            bg=self.colors["bg_card"],
            fg=self.colors["green_light"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            command=settings_window.destroy
        )
        close_btn.pack(pady=10)
    
    def show_shortcuts_window(self):
        """Muestra ventana de atajos de teclado"""
        self.show_settings_window()
    
    def show_history(self):
        """Muestra historial"""
        history_window = tk.Toplevel(self.root)
        history_window.title("📋 Video History - Phofytte")
        history_window.geometry("600x400")
        history_window.configure(bg=self.colors["bg_primary"])
        history_window.transient(self.root)
        history_window.grab_set()
        
        main_frame = tk.Frame(history_window, bg=self.colors["bg_primary"], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            main_frame,
            text="📋 Historial de videos",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors["bg_primary"],
            fg=self.colors["green_light"]
        ).pack(pady=(0, 20))
        
        # Área de texto para historial
        history_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg=self.colors["bg_input"],
            fg=self.colors["fg_primary"],
            relief=tk.FLAT,
            padx=10,
            pady=10,
            height=15
        )
        history_text.pack(fill=tk.BOTH, expand=True)
        history_text.insert(1.0, "Aún no hay videos en el historial.\n\nLos videos procesados aparecerán aquí.")
        history_text.config(state=tk.DISABLED)
        
        close_btn = tk.Button(
            main_frame,
            text="Cerrar",
            font=('Segoe UI', 10),
            bg=self.colors["bg_card"],
            fg=self.colors["green_light"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            command=history_window.destroy
        )
        close_btn.pack(pady=10)
    
    def show_theme_options(self):
        """Muestra opciones de tema"""
        messagebox.showinfo(
            "🎨 Theme",
            "Temas disponibles:\n\n"
            "• 🌿 Verde claro (actual)\n"
            "• 🌙 Oscuro\n"
            "• ☀️ Claro\n"
            "• 💜 Morado\n\n"
            "Próximamente: Personalización de temas"
        )
    
    def show_help(self):
        """Muestra ayuda"""
        help_window = tk.Toplevel(self.root)
        help_window.title("❓ Ayuda - Phofytte")
        help_window.geometry("600x500")
        help_window.configure(bg=self.colors["bg_primary"])
        help_window.transient(self.root)
        help_window.grab_set()
        
        main_frame = tk.Frame(help_window, bg=self.colors["bg_primary"], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            main_frame,
            text="❓ Ayuda de Phofytte",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors["bg_primary"],
            fg=self.colors["green_light"]
        ).pack(pady=(0, 20))
        
        help_text = """
📹 Phofytte - YouTube Video Summarizer

Cómo usar:
1. Pega una URL de YouTube en el campo de texto
2. Selecciona los modelos de Whisper y Ollama
3. Haz clic en "Procesa video" o presiona Ctrl+P
4. El audio se transcribirá automáticamente
5. Puedes resumir la transcripción con Ollama (Ctrl+R)
6. Copia o guarda los resultados con los botones o atajos

Atajos de teclado:
• Ctrl+V - Pegar URL del portapapeles
• Ctrl+P - Procesar video
• Ctrl+R - Resumir
• Ctrl+Shift+C - Copiar transcripción
• Ctrl+Shift+S - Copiar resumen
• Ctrl+Shift+X - Guardar transcripción
• Ctrl+Shift+Z - Guardar resumen
• Ctrl+Q - Cerrar aplicación
• F1 - Abrir esta ayuda

Características:
✅ Descarga automática de audio
✅ Transcripción con Whisper
✅ Resumen con IA (Ollama)
✅ Soporte para múltiples modelos
✅ Auto-resumen opcional
✅ Guardado en varios formatos
        """
        
        help_text_area = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg=self.colors["bg_input"],
            fg=self.colors["fg_primary"],
            relief=tk.FLAT,
            padx=10,
            pady=10,
            height=15
        )
        help_text_area.pack(fill=tk.BOTH, expand=True)
        help_text_area.insert(1.0, help_text)
        help_text_area.config(state=tk.DISABLED)
        
        close_btn = tk.Button(
            main_frame,
            text="Cerrar",
            font=('Segoe UI', 10),
            bg=self.colors["bg_card"],
            fg=self.colors["green_light"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            command=help_window.destroy
        )
        close_btn.pack(pady=10)
    
    def update_status(self, message, progress=None):
        """Actualiza el estado y la barra de progreso"""
        self.status_var.set(message)
        if progress is not None:
            self.progress_var.set(progress)
        self.root.update_idletasks()
    
    def copy_to_clipboard(self, text, name):
        """Copia texto al portapapeles"""
        if not text:
            messagebox.showwarning("Advertencia", f"No hay {name} para copiar")
            return
        
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        messagebox.showinfo("Éxito", f"✅ {name.capitalize()} copiado al portapapeles")
        self.update_status(f"📋 {name.capitalize()} copiado")
    
    def save_single_file(self, text, name, extension):
        """Guarda un archivo individual"""
        if not text:
            messagebox.showwarning("Advertencia", f"No hay {name} para guardar")
            return
        
        folder = filedialog.askdirectory(title=f"Seleccionar carpeta para guardar {name}")
        if not folder:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = Path(folder) / f"{name}_{timestamp}{extension}"
            file_path.write_text(text, encoding="utf-8")
            messagebox.showinfo("Éxito", f"✅ {name.capitalize()} guardado en:\n{file_path}")
            self.update_status(f"💾 {name.capitalize()} guardado")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {str(e)}")
    
    def process_video(self):
        """Procesa el video (descarga + transcripción)"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Por favor ingresa una URL de YouTube")
            return
        
        self.current_url = url
        
        # Deshabilitar botones
        self.process_btn.config(state="disabled")
        self.summarize_btn.config(state="disabled")
        
        # Limpiar textos
        self.trans_text.delete(1.0, tk.END)
        self.summary_text_widget.delete(1.0, tk.END)
        self.transcription_text = ""
        self.summary_text = ""
        self.audio_file_path = None
        
        # Ejecutar en thread
        thread = threading.Thread(target=self._process_video_thread, args=(url,))
        thread.daemon = True
        thread.start()
    
    def _process_video_thread(self, url):
        """Thread para procesar el video"""
        try:
            self.update_status("⬇️ Descargando audio...", 10)
            
            audio = self.descargar_audio(url)
            self.audio_file_path = audio
            
            self.update_status("📝 Transcribiendo audio...", 30)
            
            texto, txt_path = self.transcribir(audio, self.whisper_model_var.get())
            
            self.transcription_text = texto
            self.root.after(0, self._update_transcription, texto)
            
            self.update_status("✅ Transcripción completada", 70)
            
            if self.auto_summarize_var.get():
                self.root.after(100, self.summarize_transcription)
            else:
                self.root.after(0, lambda: self.summarize_btn.config(state="normal"))
                self.root.after(0, lambda: self.process_btn.config(state="normal"))
                self.update_status("✅ Proceso completado. Puedes resumir o guardar.", 100)
            
            self.root.after(0, self.delete_audio_file)
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.process_btn.config(state="normal"))
            self.root.after(0, lambda: self.summarize_btn.config(state="normal"))
            self.update_status(f"❌ {error_msg}", 0)
    
    def delete_audio_file(self):
        """Elimina el archivo de audio"""
        if self.audio_file_path and self.audio_file_path.exists():
            try:
                self.audio_file_path.unlink()
                print(f"🗑️ Archivo de audio eliminado: {self.audio_file_path}")
            except Exception as e:
                print(f"⚠️ No se pudo eliminar el audio: {e}")
    
    def _update_transcription(self, texto):
        """Actualiza el widget de transcripción"""
        self.trans_text.delete(1.0, tk.END)
        self.trans_text.insert(1.0, texto)
        self.switch_tab(0)
    
    def summarize_transcription(self):
        """Resume la transcripción usando Ollama"""
        if not self.transcription_text:
            messagebox.showwarning("Advertencia", "No hay transcripción para resumir")
            return
        
        self.summarize_btn.config(state="disabled")
        self.process_btn.config(state="disabled")
        
        thread = threading.Thread(target=self._summarize_thread)
        thread.daemon = True
        thread.start()
    
    def _summarize_thread(self):
        """Thread para generar el resumen"""
        try:
            self.update_status("🤖 Generando resumen con Ollama...", 50)
            
            resumen = self.resumir_con_ollama(
                self.transcription_text,
                self.ollama_model_var.get()
            )
            
            resumen = self.limpiar_texto(resumen)
            self.summary_text = resumen
            
            self.root.after(0, self._update_summary, resumen)
            
            self.update_status("✅ Resumen completado", 100)
            self.root.after(0, lambda: self.summarize_btn.config(state="normal"))
            self.root.after(0, lambda: self.process_btn.config(state="normal"))
            
        except Exception as e:
            error_msg = f"Error al generar resumen: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.summarize_btn.config(state="normal"))
            self.root.after(0, lambda: self.process_btn.config(state="normal"))
            self.update_status(f"❌ {error_msg}", 0)
    
    def _update_summary(self, texto):
        """Actualiza el widget de resumen"""
        self.summary_text_widget.delete(1.0, tk.END)
        self.summary_text_widget.insert(1.0, texto)
        self.switch_tab(1)
    
    # Funciones del script original
    def descargar_audio(self, url: str, salida: str = "downloads"):
        Path(salida).mkdir(exist_ok=True)
        
        opciones = {
            "format": "bestaudio/best",
            "outtmpl": f"{salida}/%(title)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "cookiefrombrowser": ("firefox",),
            "concurrent_fragment_downloads": 1,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
        
        with YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
            titulo = info.get("title", "audio")
            
            import re
            titulo_limpio = re.sub(r'[<>:"/\\|?*]', '', titulo)
            titulo_limpio = titulo_limpio.strip()
            
            archivos = list(Path(salida).glob(f"{titulo_limpio}*.mp3"))
            
            if not archivos:
                todos_mp3 = list(Path(salida).glob("*.mp3"))
                if todos_mp3:
                    archivo = max(todos_mp3, key=lambda x: x.stat().st_mtime)
                else:
                    archivos_audio = list(Path(salida).glob("*.webm")) + list(Path(salida).glob("*.m4a"))
                    if archivos_audio:
                        archivo = max(archivos_audio, key=lambda x: x.stat().st_mtime)
                    else:
                        raise FileNotFoundError(f"No se encontró ningún archivo de audio en {salida}")
            else:
                archivo = archivos[0]
                
        return archivo
    
    def transcribir(self, audio_path: str, modelo_whisper: str = "base"):
        print(f"📝 Transcribiendo: {audio_path}")
        
        model = whisper.load_model(modelo_whisper)
        
        result = model.transcribe(
            str(audio_path),
            language="es"
        )
        
        texto = result["text"]
        
        txt_path = Path(audio_path).with_suffix(".txt")
        txt_path.write_text(texto, encoding="utf-8")
        
        return texto, txt_path
    
    def resumir_con_ollama(self, texto: str, modelo: str = "deepseek-r1:8b"):
        prompt = f"""
Eres un asistente experto en resumir contenido. Primero entiende el video en su idioma original y luego traducelo al idioma ESPAÑOL

Haz lo siguiente:
1. Resume el contenido
2. Extrae ideas clave
3. Genera una lista de acciones
4. Devuelve todo en formato markdown
5. NO uses <think>.

TRANSCRIPCIÓN:
{texto}
"""
        
        comando = [
            "ollama",
            "run",
            modelo,
            prompt
        ]
        
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        if resultado.returncode != 0:
            raise RuntimeError(resultado.stderr)
        
        return resultado.stdout
    
    def limpiar_texto(self, texto):
        # Eliminar ANSI escape sequences
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
        texto = ansi_escape.sub('', texto)
        
        # Eliminar bloques <think>
        texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL)
        
        # Desescapar HTML
        texto = html.unescape(texto)
        
        # Limpiar espacios excesivos
        texto = re.sub(r'\n{3,}', '\n\n', texto)
        
        return texto.strip()


def main():
    root = tk.Tk()
    app = YouTubeSummarizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
