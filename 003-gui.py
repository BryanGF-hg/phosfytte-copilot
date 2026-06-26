import re
import html
import argparse
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

import whisper
from yt_dlp import YoutubeDL


class YouTubeSummarizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Summarizer")
        self.root.geometry("900x700")
        
        # Variables
        self.url_var = tk.StringVar()
        self.whisper_model_var = tk.StringVar(value="base")
        self.ollama_model_var = tk.StringVar(value="deepseek-r1:8b")
        self.status_var = tk.StringVar(value="Listo")
        self.progress_var = tk.DoubleVar(value=0)
        
        # Variables para almacenar resultados
        self.transcription_text = ""
        self.summary_text = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Título
        title_label = ttk.Label(
            main_frame, 
            text="📹 YouTube Video Summarizer", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # URL Input
        url_frame = ttk.Frame(main_frame)
        url_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        url_frame.columnconfigure(1, weight=1)
        
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, padx=(0, 10))
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=60)
        url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Model Options
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Whisper model
        ttk.Label(options_frame, text="Whisper Model:").grid(row=0, column=0, padx=(0, 10))
        whisper_combo = ttk.Combobox(
            options_frame,
            textvariable=self.whisper_model_var,
            values=["tiny - 39MB", "base - 74MB", "small - 244MB", "medium - 769MB", "large - 1.5GB"],
            state="readonly",
            width=10
        )
        whisper_combo.grid(row=0, column=1, padx=(0, 20))
        
        # Ollama model
        ttk.Label(options_frame, text="Ollama Model:").grid(row=0, column=2, padx=(0, 10))
        ollama_combo = ttk.Combobox(
            options_frame,
            textvariable=self.ollama_model_var,
            values=["deepseek-r1:8b", "llama3.2", "mistral", "phi", "tinyllama"],
            state="readonly",
            width=15
        )
        ollama_combo.grid(row=0, column=3)
        
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
            text="📝 Resumir Transcripción",
            command=self.summarize_transcription,
            state="disabled"
        )
        self.summarize_btn.grid(row=0, column=1, padx=5)
        
        self.save_btn = ttk.Button(
            buttons_frame,
            text="💾 Guardar",
            command=self.save_results,
            state="disabled"
        )
        self.save_btn.grid(row=0, column=2, padx=5)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            length=400
        )
        self.progress_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Status
        status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            font=('Arial', 10)
        )
        status_label.grid(row=5, column=0, pady=5)
        
        # Notebook para tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Tab de transcripción
        trans_frame = ttk.Frame(notebook)
        notebook.add(trans_frame, text="📄 Transcripción")
        
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
        
        self.summary_text_widget = scrolledtext.ScrolledText(
            summary_frame,
            wrap=tk.WORD,
            height=15,
            font=('Courier', 10)
        )
        self.summary_text_widget.pack(fill=tk.BOTH, expand=True)
        
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
        self.save_btn.config(state="disabled")
        
        # Limpiar textos anteriores
        self.trans_text.delete(1.0, tk.END)
        self.summary_text_widget.delete(1.0, tk.END)
        self.transcription_text = ""
        self.summary_text = ""
        
        # Ejecutar en thread separado
        thread = threading.Thread(target=self._process_video_thread, args=(url,))
        thread.daemon = True
        thread.start()
    
    def _process_video_thread(self, url):
        """Thread para procesar el video"""
        try:
            self.update_status("⬇️ Descargando audio...", 10)
            
            # Descargar audio
            audio = self.descargar_audio(url)
            
            self.update_status("📝 Transcribiendo audio...", 30)
            
            # Transcribir
            texto, txt_path = self.transcribir(audio, self.whisper_model_var.get())
            
            # Guardar transcripción en la GUI
            self.transcription_text = texto
            self.root.after(0, self._update_transcription, texto)
            
            self.update_status(f"✅ Transcripción completada: {txt_path}", 70)
            
            # Habilitar botón de resumen
            self.root.after(0, lambda: self.summarize_btn.config(state="normal"))
            self.root.after(0, lambda: self.save_btn.config(state="normal"))
            self.root.after(0, lambda: self.process_btn.config(state="normal"))
            
            self.update_status("✅ Proceso completado. Puedes resumir o guardar.", 100)
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.process_btn.config(state="normal"))
            self.update_status(f"❌ {error_msg}", 0)
    
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
        self.save_btn.config(state="disabled")
        
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
            self.root.after(0, lambda: self.save_btn.config(state="normal"))
            
        except Exception as e:
            error_msg = f"Error al generar resumen: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.summarize_btn.config(state="normal"))
            self.root.after(0, lambda: self.process_btn.config(state="normal"))
            self.root.after(0, lambda: self.save_btn.config(state="normal"))
            self.update_status(f"❌ {error_msg}", 0)
    
    def _update_summary(self, texto):
        """Actualiza el widget de resumen en el thread principal"""
        self.summary_text_widget.delete(1.0, tk.END)
        self.summary_text_widget.insert(1.0, texto)
    
    def save_results(self):
        """Guarda los resultados en archivos"""
        if not self.transcription_text and not self.summary_text:
            messagebox.showwarning("Advertencia", "No hay datos para guardar")
            return
        
        # Diálogo para elegir carpeta
        folder = filedialog.askdirectory(title="Seleccionar carpeta para guardar")
        if not folder:
            return
        
        try:
            # Guardar transcripción
            if self.transcription_text:
                trans_path = Path(folder) / "transcripcion.txt"
                trans_path.write_text(self.transcription_text, encoding="utf-8")
            
            # Guardar resumen
            if self.summary_text:
                summary_path = Path(folder) / "resumen.md"
                summary_path.write_text(self.summary_text, encoding="utf-8")
            
            messagebox.showinfo("Éxito", f"Archivos guardados en:\n{folder}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron guardar los archivos: {str(e)}")
    
    # Funciones del script original adaptadas
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
