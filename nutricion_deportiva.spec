# -*- mode: python ; coding: utf-8 -*-
# Empaquetado de Nutrición Deportiva (tkinter) como app de escritorio.
#
# Los datos del usuario (BD, SMAE-5.xlsx, imágenes, JSON, recomendaciones)
# NO se incluyen dentro del paquete: la app los busca junto al .exe
# (ver rutas.py). Después de compilar, copiarlos a dist\NutricionDeportiva\.
#
# Con CONSOLE_BUILD=1 se genera con consola (diagnóstico de arranque).

import os

a = Analysis(
    ['nutricion_deportiva.py'],
    pathex=[],
    binaries=[],
    datas=[('icono_app.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Instalados en el venv para scripts de extracción/sincronización,
        # no los usa la app: los excluimos para no inflar el paquete.
        'numpy', 'onnxruntime', 'pymupdf', 'pymupdf4llm', 'fitz',
        'networkx', 'psutil', 'yaml', 'tabulate',
        'matplotlib', 'scipy', 'pandas', 'pytest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NutricionDeportiva',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=bool(int(os.environ.get("CONSOLE_BUILD", "0"))),
    icon='icono_app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='NutricionDeportiva',
)
