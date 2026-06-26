estoy intentado compilar y hacer que en vez de ejecutar+compilar a traves de python sea un ejecutable porque ahora el paso de usar terminal (en cierta medida).

# pasos de recreacion

primero el script sh que luego se le da permisos, sirve pero sirve. no es exactamente lo que se busca pero sirve

```
#!/bin/bash
# phofytte.sh
cd "$(dirname "$0")"
python3 phofytte.py
```

```
sudo chmod +x phofytte.sh
```

segundo el pyinstaller tarda mucho y descargo un contenido grande (2GB) ademas de quedarse atascado en PKG:
``` 
pip install pyinstaller #--break-system-packages
pyinstaller --onefile --windowed --name="Phofytte" --icon="icon.ico" 005-gui\ v1.3.py
```

**solucion encontrada** usando **appimage** a traves de github con wget donde se le da permisos chmod, y usamos el programa python+ imagen en {.png,.svg,.xpm} como crear dos archivos un Apprun y un .desktop

## Apprun
```
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
python3 "$HERE/phofytte.py" "$@"
```
## Desktop
```
[Desktop Entry]
Name=Phofytte
Comment=YouTube Video Summarizer
Exec=python3 phofytte.py
Icon=icon
Terminal=false
Type=Application
Categories=AudioVideo;
```
