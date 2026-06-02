# YouTube → Transcripción → Resumen con Ollama

## Características
✅ Descarga vídeos usando yt-dlp  
✅ Convierte audio a texto con Whisper  
✅ Resume usando Ollama + DeepSeek  
✅ Guarda transcripción y resumen automáticamente

---
# Instalación

## 1. Instalar Python (si estas en Windows :(
https://www.python.org/downloads/

---

# 2. Instalar FFmpeg
## Ubuntu/Debian, tambien actualizar yt-dlp por tener versiones viejas

sudo apt update
sudo apt install ffmpeg
pip install -U yt-dlp

## macOS
brew install ffmpeg

## Windows
https://www.gyan.dev/ffmpeg/builds/
Añadir `ffmpeg/bin` al PATH.
---

# 3. Instalar Ollama

## Windows/macOS

https://ollama.com/download

## Linux
curl -fsSL https://ollama.com/install.sh | sh

Verificar:
ollama --version

---

# 4. Instalar DeepSeek

## Recomendado (5,3GB)

ollama pull deepseek-r1:8b

## Otros modelos
ollama pull deepseek-r1:1.5b
ollama pull deepseek-r1:14b (más pesado, OJO)

---

# 5. Crear entorno virtual

python -m venv venv

## Windows
venv\Scripts\activate

## Linux/macOS
source venv/bin/activate

---

# 6. Instalar dependencias
pip install -r requirements.txt

---

# Ejecutar
python3 app.py --url "https://youtube.com/watch?v=XXXX"

Ejemplo:

python app.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

---

  # Cambiar Whisper
  python app.py --url "URL" --whisper medium

  Modelos:

  - tiny
  - base
  - small
  - medium
  - large

  ---

  # Cambiar modelo Ollama
  python app.py --url "URL" --ollama deepseek-r1:14b

  ---

  # Salida

  La app genera:

  downloads/
   ├── video.mp3
   ├── video.txt
   └── video_resumen.md

