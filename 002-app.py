import re
import html
import argparse
import subprocess
from pathlib import Path

import whisper
from yt_dlp import YoutubeDL


def descargar_audio(url: str, 
	salida: str = "downloads"
	):      

    Path(salida).mkdir(exist_ok=True)

    opciones = {
        "format": "bestaudio/best",
        "outtmpl": f"{salida}/%(title)s.%(ext)s",
        "quiet": False,
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

       # Limpiar caracteres que podrían causar problemas
        import re
        titulo_limpio = re.sub(r'[<>:"/\\|?*]', '', titulo)
        titulo_limpio = titulo_limpio.strip()
        
        # Buscar el archivo generado
        archivos = list(Path(salida).glob(f"{titulo_limpio}*.mp3"))
        
        # Si no encuentra archivos, buscar archivos mp3 recientes
        if not archivos:
            todos_mp3 = list(Path(salida).glob("*.mp3"))
            if todos_mp3:
                # Tomar el archivo más reciente
                archivo = max(todos_mp3, key=lambda x: x.stat().st_mtime)
            else:
                # Buscar cualquier archivo de audio
                archivos_audio = list(Path(salida).glob("*.webm")) + list(Path(salida).glob("*.m4a"))
                if archivos_audio:
                    archivo = max(archivos_audio, key=lambda x: x.stat().st_mtime)
                else:
                    # Mostrar todos los archivos en el directorio para depuración
                    print(f"Archivos en {salida}:", list(Path(salida).glob("*")))
                    raise FileNotFoundError(f"No se encontró ningún archivo de audio en {salida}")
        else:
            archivo = archivos[0]
            
    return archivo


def transcribir(audio_path: str, modelo_whisper: str = "base"):
    print(f"📝 Transcribiendo: {audio_path}")

    model = whisper.load_model(modelo_whisper)

    result = model.transcribe(
        str(audio_path),
        language="es"
    )

    texto = result["text"]

    txt_path = Path(audio_path).with_suffix(".txt")

    txt_path.write_text(
        texto,
        encoding="utf-8"
    )

    return texto, txt_path


def resumir_con_ollama(
        texto: str,
        modelo: str = "deepseek-r1:8b" #cambiar si es necesario
):

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


def main():

    parser = argparse.ArgumentParser(
        description="YouTube -> Transcripción -> Resumen con Ollama"
    )

    parser.add_argument(
        "--url",
        required=True,
        help="URL del vídeo de YouTube"
    )

    parser.add_argument(
        "--whisper",
        default="base",
        help="Modelo Whisper: tiny/base/small/medium/large"
    )

    parser.add_argument(
        "--ollama",
        default="deepseek-r1:8b",
        help="Modelo Ollama"
    )

    args = parser.parse_args()

    print("⬇️ Descargando audio...")
    audio = descargar_audio(args.url)

    texto, txt_path = transcribir(
        audio,
        args.whisper
    )

    print(f"✅ Transcripción guardada en: {txt_path}")

    print("🤖 Generando resumen con Ollama...")

    resumen = resumir_con_ollama(
        texto,
        args.ollama
    )
 
    resumen = limpiar_texto(resumen)

    resumen_path = txt_path.with_name(
        txt_path.stem + "_resumen.md"
    )

    resumen_path.write_text(
        resumen,
        encoding="utf-8"
    )

    print("\n========== RESUMEN ==========\n")
    print(resumen)

    print(f"\n📄 Resumen guardado en: {resumen_path}")

def limpiar_texto(texto):

    # Eliminar ANSI escape sequences
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    texto = ansi_escape.sub('', texto)

    # Eliminar bloques <think>
    texto = re.sub(
        r'<think>.*?</think>',
        '',
        texto,
        flags=re.DOTALL
    )

    # Desescapar HTML
    texto = html.unescape(texto)

    # Limpiar espacios excesivos
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    return texto.strip()

if __name__ == "__main__":
    main()

