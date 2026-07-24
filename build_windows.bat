@echo off
REM ══════════════════════════════════════════════════════════════════════════════
REM  build_windows.bat — Build RadioSAT XP para Windows
REM ══════════════════════════════════════════════════════════════════════════════

echo ════════════════════════════════════════════════════
echo   RadioSAT XP — Build Windows
echo ════════════════════════════════════════════════════

REM Verificar Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python no encontrado. Instala Python 3.10+ desde python.org
    pause
    exit /b 1
)

REM Verificar/crear venv
if not exist ".venv" (
    echo → Creando entorno virtual...
    python -m venv .venv
)

REM Instalar dependencias
echo → Instalando dependencias...
.venv\Scripts\pip install -r requirements.txt --quiet

REM Limpiar builds anteriores
echo → Limpiando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM Ejecutar PyInstaller
echo → Ejecutando PyInstaller...
.venv\Scripts\pyinstaller radiosat.spec --clean --noconfirm

REM Verificar
if exist "dist\RadioSAT\RadioSAT.exe" (
    echo.
    echo ✓ Build completado: dist\RadioSAT\
    echo.
    echo Contenido:
    dir dist\RadioSAT\ /b
    echo.
    echo Tamaño total:
    powershell -Command "(Get-ChildItem -Recurse 'dist\RadioSAT' | Measure-Object -Property Length -Sum).Sum / 1MB"
    echo MB
    echo.
    echo Ahora ejecuta radiosat.iss con Inno Setup para crear el instalador.
) else (
    echo ERROR: No se creó dist\RadioSAT\RadioSAT.exe
    echo Revisa los logs de PyInstaller arriba
)

pause
