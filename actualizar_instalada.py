"""Actualiza la app INSTALADA en este PC — uso del autor.

Flujo de trabajo: sigues modificando el código en
D:\\Biblioteca\\Nutrición_deportiva, y cuando quieras llevar los cambios
a la copia instalada (la que abre el acceso directo del escritorio):

    python actualizar_instalada.py            # compila + actualiza
    python actualizar_instalada.py --rapido   # usa el último exe compilado

Qué hace:
  1. Compila el exe con PyInstaller (igual que nutricion_deportiva.spec).
  2. Sincroniza los datos del proyecto (SMAE, JSONs, imágenes, BD de
     pruebas) a dist\\NutricionDeportiva, porque la compilación borra
     el contenido de dist.
  3. Copia dist\\NutricionDeportiva a la carpeta de instalación
     (%LOCALAPPDATA%\\Programs\\NutricionDeportiva) SIN tocar la base
     de datos instalada: la BD que vive junto a la app instalada es la
     de uso diario y NUNCA se sobreescribe con la del proyecto.

Nota: los .db nuevos (respaldos) y logs nunca se copian. Si una versión
nueva agrega archivos de datos, aparecen solos en la instalada.
"""
import os
import shutil
import stat
import subprocess
import sys

from version import VERSION

ORIGEN = os.path.join("dist", "NutricionDeportiva")
DESTINO = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Programs", "NutricionDeportiva",
)
PYTHON = os.path.join("venv", "Scripts", "python.exe")

# Datos que la app espera junto al exe (igual que la instalación manual).
ARCHIVOS_DATOS = (
    "Nutrición_deportiva.db",  # BD del proyecto: solo para dist (pruebas)
    "SMAE-5.xlsx",
    "mets.csv",
    "icono_app.ico",
    "abdominales_ejercicios.json",
    "brazos_ejercicios.json",
    "calentamiento_powerlifting.json",
    "catalogo_smae_web.json",
    "espalda_ejercicios.json",
    "gluteos_ejercicios.json",
    "hombros_ejercicios.json",
    "menus_lista_smae_web.json",
    "pectorales_ejercicios.json",
    "piernas_ejercicios.json",
    "platillos_smae_web.json",
)
CARPETAS_DATOS = (
    "assets",
    "estiramientos_img",
    "img_platillos_nuevo",
    "recomendaciones",
)

# Al pasar a la INSTALADA: la BD de uso diario jamás se sobreescribe.
EXCLUIR_SUFIJOS = (".db",)
EXCLUIR_NOMBRES = ("app_err.log", "app_out.log", "app_run_tmp.log")


def _excluir(nombre):
    return (
        nombre.lower().endswith(EXCLUIR_SUFIJOS)
        or nombre in EXCLUIR_NOMBRES
    )


def _copiar(origen, destino):
    """Copia sobre-escribiendo; algunos assets están en solo lectura."""
    if os.path.exists(destino):
        os.chmod(destino, stat.S_IWRITE)
    shutil.copy2(origen, destino)


def compilar():
    print("Compilando con PyInstaller (tarda ~4-5 minutos)...")
    r = subprocess.run([
        PYTHON, "-m", "PyInstaller",
        "nutricion_deportiva.spec", "--noconfirm",
    ])
    if r.returncode != 0:
        raise SystemExit("Falló la compilación; revisa la salida de arriba.")


def sincronizar_datos():
    """Deja los datos del proyecto dentro de dist (la compilación los borra)."""
    faltan = [
        a for a in ARCHIVOS_DATOS if not os.path.isfile(a)
    ] + [
        c for c in CARPETAS_DATOS if not os.path.isdir(c)
    ]
    if faltan:
        raise SystemExit("Faltan en el proyecto: " + ", ".join(faltan))
    for a in ARCHIVOS_DATOS:
        _copiar(a, os.path.join(ORIGEN, a))
    for c in CARPETAS_DATOS:
        shutil.copytree(
            c, os.path.join(ORIGEN, c), dirs_exist_ok=True,
            copy_function=_copiar,
        )
    print("Datos del proyecto sincronizados en dist.")


def actualizar_instalada():
    if not os.path.isdir(DESTINO):
        raise SystemExit(
            f"No existe {DESTINO}: instala la app primero."
        )
    exe = os.path.join(DESTINO, "NutricionDeportiva.exe")
    try:
        with open(exe, "r+b"):
            pass
    except PermissionError:
        raise SystemExit(
            "La app instalada está ABIERTA. Ciérrala y vuelve a ejecutar "
            "este script (no se copió nada todavía)."
        )
    total = 0
    for raiz, _dirs, archivos in os.walk(ORIGEN):
        rel = os.path.relpath(raiz, ORIGEN)
        destino = os.path.normpath(os.path.join(DESTINO, rel))
        os.makedirs(destino, exist_ok=True)
        for a in archivos:
            if _excluir(a):
                continue
            _copiar(os.path.join(raiz, a), os.path.join(destino, a))
            total += 1
    bd = os.path.join(DESTINO, "Nutrición_deportiva.db")
    print(f"Instalada actualizada a v{VERSION}: {total} archivos copiados.")
    print(f"BD de uso diario intacta ({'existe' if os.path.isfile(bd) else '¡NO EXISTE!'}).")


def main():
    rapido = "--rapido" in sys.argv
    if not os.path.isdir(ORIGEN) or rapido is False:
        compilar()
    else:
        print("Modo --rapido: se usa el exe ya compilado en dist.")
    if not os.path.isdir(ORIGEN):
        raise SystemExit(f"No existe {ORIGEN}: compila primero.")
    sincronizar_datos()
    actualizar_instalada()
    print("Listo: abre la app desde el acceso directo del escritorio.")


if __name__ == "__main__":
    main()
