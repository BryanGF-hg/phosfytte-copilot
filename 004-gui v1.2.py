import re
import html
import argparse
import subprocess
import threading
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import os

import whisper
from yt_dlp import YoutubeDL


class YouTubeSummarizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Summarizer")
        self.root.geometry("1000x750")
        
        # Configuración
        self.config_file = Path.home() / ".youtube_summarizer_config.json"
        self.config = self.load_config()
        
        # Variables
        self.url_var = tk.StringVar()
        self.whisper_model_var = tk.StringVar(value="base")
        self.ollama_model_var = tk.StringVar(value="deepseek-r1:8b")
        self.status_var = tk.StringVar(value="Listo")
        self.progress_var = tk.DoubleVar(value=0)
        self.auto_summarize_var = tk.BooleanVar(value=False)
        self.download_folder_var = tk.StringVar(value=self.config.get("download_folder", "downloads"))
        self.theme_var = tk.StringVar(value=self.config.get("theme", "claro"))
        
        # Variables para almacenar resultados
        self.transcription_text = ""
        self.summary_text = ""
        self.audio_file_path = None
        
        # Variables para el historial
        self.history = []
        
        self.setup_ui()
        
        # Verificar dependencias
        self.check_dependencies()
        
    def load_config(self):
        """Carga la configuración desde archivo"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self):
        """Guarda la configuración en archivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except:
            pass
    
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Menú
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 Archivo", menu=file_menu)
        file_menu.add_command(label="📂 Seleccionar carpeta de descargas", command=self.select_download_folder)
        file_menu.add_separator()
        file_menu.add_command(label="📋 Historial", command=self.show_history)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Salir", command=self.root.quit)
        
        # Menú Configuración
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="⚙️ Configuración", menu=config_menu)
       
        
        config_menu.add_command(label="🧹 Limpiar archivos temporales", command=self.clean_temp_files)
        
        # Menú Ayuda
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Ayuda", menu=help_menu)
        help_menu.add_command(label="📖 Acerca de", command=self.show_about)
        
        # Título
        title_label = ttk.Label(
            main_frame, 
            text="📹 YouTube Video Summarizer", 
            font=('Arial', 18, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # URL Input
        url_frame = ttk.Frame(main_frame)
        url_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        url_frame.columnconfigure(1, weight=1)
        
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, padx=(0, 10))
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=60)
        url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        url_entry.bind('<Return>', lambda e: self.process_video())
        
        # Model Options
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Whisper model
        ttk.Label(options_frame, text="Whisper:").grid(row=0, column=0, padx=(0, 5))
        whisper_combo = ttk.Combobox(
            options_frame,
            textvariable=self.whisper_model_var,
            values=["tiny - 39MB", "base - 74MB", "small - 244MB", "medium - 769MB", "large - 1.5GB"],
            state="readonly",
            width=12
        )
        whisper_combo.grid(row=0, column=1, padx=(0, 15))
        
        # Ollama model
        ttk.Label(options_frame, text="Ollama:").grid(row=0, column=2, padx=(0, 5))
        ollama_combo = ttk.Combobox(
            options_frame,
            textvariable=self.ollama_model_var,
            values=["deepseek-r1:8b", "llama3.2", "mistral", "phi", "tinyllama"],
            state="readonly",
            width=12
        )
        ollama_combo.grid(row=0, column=3, padx=(0, 15))
        
        # Auto-summarize checkbox
        self.auto_check = ttk.Checkbutton(
            options_frame,
            text="🤖 Auto-resumir",
            variable=self.auto_summarize_var
        )
        self.auto_check.grid(row=0, column=4, padx=(0, 10))
        
        # Botones
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, pady=10)
        
        self.process_btn = ttk.Button(
            buttons_frame,
            text="▶️ Procesar Video",
            command=self.process_video
        )
        self.process_btn.grid(row=0, column=0, padx=5)
        
        self.summarize_btn = ttk.Button(
            buttons_frame,
            text="📝 Resumir",
            command=self.summarize_transcription,
            state="disabled"
        )
        self.summarize_btn.grid(row=0, column=1, padx=5)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            length=500
        )
        self.progress_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Status
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        status_frame.columnconfigure(0, weight=1)
        
        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            font=('Arial', 10)
        )
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        # Notebook para tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Tab de transcripción
        trans_frame = ttk.Frame(notebook)
        notebook.add(trans_frame, text="📄 Transcripción")
        
        trans_controls = ttk.Frame(trans_frame)
        trans_controls.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            trans_controls,
            text="📋 Copiar",
            command=lambda: self.copy_to_clipboard(self.transcription_text, "transcripción")
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            trans_controls,
            text="💾 Guardar",
            command=lambda: self.save_single_file(self.transcription_text, "transcripcion", ".txt")
        ).pack(side=tk.LEFT, padx=2)
        
        self.trans_text = scrolledtext.ScrolledText(
            trans_frame,
            wrap=tk.WORD,
            height=15,
            font=('Courier', 10)
        )
        self.trans_text.pack(fill=tk.BOTH, expand=True)
        
        # Tab de resumen
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="📋 Resumen")
        
        summary_controls = ttk.Frame(summary_frame)
        summary_controls.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            summary_controls,
            text="📋 Copiar",
            command=lambda: self.copy_to_clipboard(self.summary_text, "resumen")
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            summary_controls,
            text="💾 Guardar",
            command=lambda: self.save_single_file(self.summary_text, "resumen", ".md")
        ).pack(side=tk.LEFT, padx=2)
        
        self.summary_text_widget = scrolledtext.ScrolledText(
            summary_frame,
            wrap=tk.WORD,
            height=15,
            font=('Courier', 10)
        )
        self.summary_text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Mostrar carpeta de descargas
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(folder_frame, text="📂 Descargas:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(folder_frame, textvariable=self.download_folder_var, foreground="gray").pack(side=tk.LEFT)
        
    def copy_to_clipboard(self, text, name):
        """Copia texto al portapapeles"""
        if not text:
            messagebox.showwarning("Advertencia", f"No hay {name} para copiar")
            return
        
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        messagebox.showinfo("Éxito", f"✅ {name.capitalize()} copiado al portapapeles")
    
    def save_single_file(self, text, name, extension):
        """Guarda un archivo individual"""
        if not text:
            messagebox.showwarning("Advertencia", f"No hay {name} para guardar")
            return
        
        folder = filedialog.askdirectory(title=f"Seleccionar carpeta para guardar {name}")
        if not folder:
            return
        
        try:
            file_path = Path(folder) / f"{name}{extension}"
            file_path.write_text(text, encoding="utf-8")
            messagebox.showinfo("Éxito", f"✅ {name.capitalize()} guardado en:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {str(e)}")
    
    def select_download_folder(self):
        """Selecciona carpeta de descargas"""
        folder = filedialog.askdirectory(title="Seleccionar carpeta de descargas")
        if folder:
            self.download_folder_var.set(folder)
            self.config["download_folder"] = folder
            self.save_config()
            messagebox.showinfo("Éxito", f"Carpeta de descargas actualizada:\n{folder}")
    
    def check_dependencies(self):
        """Verifica que las dependencias necesarias estén instaladas"""
        try:
            # Verificar Ollama
            result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                messagebox.showwarning(
                    "Dependencia faltante",
                    "Ollama no está instalado o no está en el PATH.\n"
                    "Por favor instala Ollama desde: https://ollama.com/"
                )
        except FileNotFoundError:
            messagebox.showwarning(
                "Dependencia faltante",
                "Ollama no está instalado.\n"
                "Por favor instala Ollama desde: https://ollama.com/"
            )
        
        try:
            # Verificar FFmpeg
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            if result.returncode != 0:
                messagebox.showwarning(
                    "Dependencia faltante",
                    "FFmpeg no está instalado.\n"
                    "Por favor instala FFmpeg."
                )
        except FileNotFoundError:
            messagebox.showwarning(
                "Dependencia faltante",
                "FFmpeg no está instalado.\n"
                "Por favor instala FFmpeg."
            )
    
    def clean_temp_files(self):
        """Limpia archivos temporales y de audio"""
        if messagebox.askyesno("Confirmar", "¿Eliminar todos los archivos de audio temporales?"):
            try:
                download_folder = Path(self.download_folder_var.get())
                if download_folder.exists():
                    # Eliminar archivos de audio
                    for ext in ["*.mp3", "*.wav", "*.m4a", "*.webm"]:
                        for file in download_folder.glob(ext):
                            try:
                                file.unlink()
                            except:
                                pass
                    
                    messagebox.showinfo("Éxito", "Archivos temporales eliminados")
                    self.update_status("🧹 Archivos temporales eliminados")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudieron eliminar los archivos: {str(e)}")
    
    def show_history(self):
        """Muestra el historial de procesamientos"""
        if not self.history:
            messagebox.showinfo("Historial", "No hay historial de procesamientos")
            return
        
        history_text = "\n".join(self.history[-10:])  # Últimos 10
        messagebox.showinfo("Historial", f"Últimos procesamientos:\n\n{history_text}")
    
    def show_about(self):
        """Muestra información sobre la aplicación"""
        about_text = """
📹 YouTube Video Summarizer
Versión 2.0

Una aplicación para descargar, transcribir y resumir videos de YouTube.

Tecnologías utilizadas:
• Whisper (OpenAI) - Transcripción
• Ollama - Resumen con IA
• yt-dlp - Descarga de videos
• tkinter - Interfaz gráfica
        """
        messagebox.showinfo("Acerca de", about_text)
    
    def update_status(self, message, progress=None):
        """Actualiza el estado y la barra de progreso"""
        self.status_var.set(message)
        if progress is not None:
            self.progress_var.set(progress)
        self.root.update_idletasks()
    
    def process_video(self):
        """Procesa el video (descarga + transcripción)"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Por favor ingresa una URL de YouTube")
            return
        
        # Deshabilitar botones durante el proceso
        self.process_btn.config(state="disabled")
        self.summarize_btn.config(state="disabled")
        
        # Limpiar textos anteriores
        self.trans_text.delete(1.0, tk.END)
        self.summary_text_widget.delete(1.0, tk.END)
        self.transcription_text = ""
        self.summary_text = ""
        self.audio_file_path = None
        
        # Ejecutar en thread separado
        thread = threading.Thread(target=self._process_video_thread, args=(url,))
        thread.daemon = True
        thread.start()
    
    def _process_video_thread(self, url):
        """Thread para procesar el video"""
        try:
            self.update_status("⬇️ Descargando audio...", 10)
            
            # Descargar audio
            audio, video_title = self.descargar_audio(url)
            self.audio_file_path = audio
            self.video_title = video_title
            
            self.update_status("📝 Transcribiendo audio...", 30)
            
            # Transcribir
            texto, txt_path = self.transcribir(audio, self.whisper_model_var.get())
            
            # Guardar transcripción en la GUI
            self.transcription_text = texto
            self.root.after(0, self._update_transcription, texto)
            
            self.update_status(f"✅ Transcripción completada", 70)
            
            # Auto-summarize si está activado
            if self.auto_summarize_var.get():
                self.root.after(100, self.summarize_transcription)
            else:
                # Habilitar botones
                self.root.after(0, lambda: self.summarize_btn.config(state="normal"))
                self.root.after(0, lambda: self.process_btn.config(state="normal"))
                self.update_status("✅ Proceso completado. Puedes resumir o guardar.", 100)
            
            # Guardar en historial
            self.history.append(f"✅ {self.video_title}")
            
            # Eliminar archivo de audio
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
        """Actualiza el widget de transcripción en el thread principal"""
        self.trans_text.delete(1.0, tk.END)
        self.trans_text.insert(1.0, texto)
    
    def summarize_transcription(self):
        """Resume la transcripción usando Ollama"""
        if not self.transcription_text:
            messagebox.showwarning("Advertencia", "No hay transcripción para resumir")
            return
        
        # Deshabilitar botones
        self.summarize_btn.config(state="disabled")
        self.process_btn.config(state="disabled")
        
        # Ejecutar en thread
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
            
            # Actualizar GUI
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
        """Actualiza el widget de resumen en el thread principal"""
        self.summary_text_widget.delete(1.0, tk.END)
        self.summary_text_widget.insert(1.0, texto)
    
    # Funciones del script original adaptadas
    def descargar_audio(self, url: str, salida: str = None):
        if salida is None:
            salida = self.download_folder_var.get()
            
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
                
        return archivo, titulo
    
    def transcribir(self, audio_path: str, modelo_whisper: str = "base"):
        # Extraer solo el nombre del modelo sin el tamaño
        modelo = modelo_whisper.split()[0] if modelo_whisper else "base"
        
        print(f"📝 Transcribiendo: {audio_path}")
        
        model = whisper.load_model(modelo)
        
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
