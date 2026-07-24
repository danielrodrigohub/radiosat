# Build RadioSAT XP — Guía de Empaquetado

Instrucciones para crear los instaladores de **macOS** y **Windows**.

---

## Requisitos Previos

### Comunes
- Python 3.10+
- FFmpeg instalado y en el PATH

### macOS
- Xcode Command Line Tools (`xcode-select --install`)

### Windows
- [Inno Setup 6+](https://jrsoftware.org/isinfo.php) (para crear el instalador)
- [FFmpeg estático](https://www.gyan.dev/ffmpeg/builds/) (colocar `ffmpeg.exe` en el PATH)

---

## Estructura de Archivos

```
Radiosat/
├── assets/
│   ├── icon.png          # Icono fuente 1024x1024
│   ├── icon.icns         # Icono macOS
│   └── icon.ico          # Icono Windows
├── winxpicons/           # Iconos Windows XP (bundled)
├── icons/                # Iconos alternativos (bundled)
├── main.py               # Aplicación principal
├── radiosat.spec         # Configuración PyInstaller
├── radiosat.iss          # Script Inno Setup (Windows)
├── build_mac.sh          # Script build macOS
├── build_windows.bat     # Script build Windows
├── requirements.txt      # Dependencias Python
└── LICENSE.txt
```

---

## Build macOS (.app + .dmg)

### Opción 1: Script automático
```bash
./build_mac.sh
```

### Opción 2: Manual
```bash
# 1. Crear/activar venv
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar PyInstaller
pyinstaller radiosat.spec --clean --noconfirm

# 4. Verificar
ls -la dist/RadioSAT.app

# 5. Crear DMG (opcional)
hdiutil create -volname "RadioSAT XP" \
    -srcfolder dist/RadioSAT.app \
    -ov -format UDZO \
    dist/RadioSAT.dmg
```

### Salida
- `dist/RadioSAT.app` — Aplicación macOS
- `dist/RadioSAT.dmg` — Imagen de disco para distribución

### Notas macOS
- Para distribuir sin advertencias de Gatekeeper, firmar con:
  ```bash
  codesign --force --deep --sign "Developer ID Application: TU NOMBRE" dist/RadioSAT.app
  ```
- Los datos del usuario se guardan en `~/.radiosat/`

---

## Build Windows (.exe + Instalador)

### Paso 1: Crear el ejecutable

#### Opción 1: Script automático
```batch
build_windows.bat
```

#### Opción 2: Manual
```batch
:: 1. Crear/activar venv
python -m venv .venv
.venv\Scripts\activate

:: 2. Instalar dependencias
pip install -r requirements.txt

:: 3. Ejecutar PyInstaller
pyinstaller radiosat.spec --clean --noconfirm

:: 4. Verificar
dir dist\RadioSAT\
```

### Paso 2: Crear el instalador con Inno Setup

1. Abrir **Inno Setup Compiler**
2. Archivo → Abrir → Seleccionar `radiosat.iss`
3. Compilar → Build (F9)
4. El instalador se crea en `installer/RadioSAT_Setup.exe`

### Salida
- `dist/RadioSAT/` — Carpeta con el ejecutable y dependencias
- `installer/RadioSAT_Setup.exe` — Instalador Windows

### Notas Windows
- Los datos del usuario se guardan en `%USERPROFILE%\.radiosat\`
- FFmpeg debe estar en el PATH o colocarlo junto al ejecutable
- El instalador crea accesos directos en Escritorio y Menú Inicio

---

## FFmpeg (Opcional)

Para incluir FFmpeg empaquetado:

### macOS
```bash
# Copiar FFmpeg al bundle después del build
cp $(which ffmpeg) dist/RadioSAT.app/Contents/MacOS/
```

### Windows
```batch
:: Copiar FFmpeg al directorio de distribución
copy "C:\path\to\ffmpeg.exe" dist\RadioSAT\
```

---

## Troubleshooting

### "Module not found" durante el build
Añadir el módulo faltante a `hiddenimports` en `radiosat.spec`.

### La app no encuentra los iconos
Verificar que `winxpicons/` y `icons/` están incluidos en `datas` del spec.

### macOS: "App is damaged"
```bash
xattr -cr dist/RadioSAT.app
```

### Windows: Antivirus bloquea el .exe
Es un falso positivo común con PyInstaller. Firmar el .exe con un certificado de código reduce las falsas alarmas.

---

## Optimización

Para reducir el tamaño del instalador:

1. **Reducir iconos**: Solo incluir los iconos realmente usados en `winxpicons/`
2. **UPX**: Comprimir binarios (ya habilitado en el spec)
3. **Excluir módulos**: Añadir más exclusiones en `excludes` del spec
