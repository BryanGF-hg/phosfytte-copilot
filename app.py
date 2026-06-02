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

    archivo = next(Path(salida).glob(f"{titulo}*.mp3"))
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
        modelo: str = "deepseek-r1:8b"
):

    prompt = f"""
Eres un asistente experto en resumir contenido.

Haz lo siguiente:

1. Resume el contenido
2. Extrae ideas clave
3. Genera una lista de acciones
4. Devuelve todo en formato markdown

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


if __name__ == "__main__":
    main()

