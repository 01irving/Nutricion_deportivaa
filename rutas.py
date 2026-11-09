"""Ruta base de datos/recursos de la app.

Desde código fuente los recursos (BD, SMAE-5.xlsx, imágenes, JSON) viven junto
a este archivo. Empaquetado con PyInstaller resuelven junto al .exe, así el
usuario ve y respalda su base de datos sin entrar a carpetas internas.
"""
import os
import sys


def base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))
