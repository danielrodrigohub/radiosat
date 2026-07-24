#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
#  build_mac.sh — Build RadioSAT XP para macOS
# ══════════════════════════════════════════════════════════════════════════════
set -e

echo "═══════════════════════════════════════════════════"
echo "  RadioSAT XP — Build macOS"
echo "═══════════════════════════════════════════════════"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 no encontrado"
    exit 1
fi

# Verificar/crear venv
if [ ! -d ".venv" ]; then
    echo "→ Creando entorno virtual..."
    python3 -m venv .venv
fi

# Instalar dependencias
echo "→ Instalando dependencias..."
.venv/bin/pip install -r requirements.txt --quiet

# Limpiar builds anteriores
echo "→ Limpiando builds anteriores..."
rm -rf build/ dist/

# Ejecutar PyInstaller
echo "→ EjecutPyInstaller..."
.venv/bin/pyinstaller radiosat.spec --clean --noconfirm

# Verificar que el .app se creó
if [ -d "dist/RadioSAT.app" ]; then
    echo ""
    echo "✓ Build completado: dist/RadioSAT.app"
    echo ""

    # Crear DMG
    echo "→ Creando DMG..."
    mkdir -p dist/dmg
    cp -R dist/RadioSAT.app dist/dmg/
    ln -sf /Applications dist/dmg/Applications

    hdiutil create -volname "RadioSAT XP" \
        -srcfolder dist/dmg \
        -ov -format UDZO \
        dist/RadioSAT.dmg

    rm -rf dist/dmg

    echo ""
    echo "✓ DMG creado: dist/RadioSAT.dmg"
    echo ""
    echo "Tamaño del .app:"
    du -sh dist/RadioSAT.app
    echo ""
    echo "Tamaño del .dmg:"
    du -sh dist/RadioSAT.dmg
else
    echo "ERROR: No se creó dist/RadioSAT.app"
    echo "Revisa los logs de PyInstaller arriba"
    exit 1
fi
