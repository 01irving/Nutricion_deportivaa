"""Crea el zip de DISTRIBUCIÓN — USO PRIVADO DEL AUTOR.

Empaca dist\\NutricionDeportiva (después de compilar el exe) pero SIN
la base de datos del autor ni archivos personales: el profesional que
la recibe crea su propia BD vacía al primer arranque y personaliza su
membrete. El zip se llama NutricionDeportiva_v{VERSION}_distribucion.zip.

Uso:
    python crear_zip_distribucion.py
"""
import os
import zipfile

from version import VERSION

ORIGEN = os.path.join("dist", "NutricionDeportiva")
DESTINO = os.path.join(
    "dist", f"NutricionDeportiva_v{VERSION}_distribucion.zip"
)

# Nada del autor sale en el zip de distribución.
EXCLUIR_SUFIJOS = (".db",)
EXCLUIR_NOMBRES = (
    "app_err.log", "app_out.log", "app_run_tmp.log",
)

LEEME = f"""NUTRICIÓN DEPORTIVA v{VERSION} — PRIMEROS PASOS
================================================

1. EJECUTA EL PROGRAMA
   Abre NutricionDeportiva.exe (dentro de esta carpeta). La primera
   vez puede tardar unos segundos.

2. VERSIÓN DE PRUEBA (30 DÍAS)
   La primera vez arranca tu período de prueba con TODAS las
   funciones. En el título de la ventana verás los días restantes.
   Al terminar necesitas una CLAVE DE ACTIVACIÓN.

3. ACTIVA TU COPIA
   El programa muestra tu CÓDIGO DE INSTALACIÓN. Envíalo a tu
   proveedor y pega la clave de activación que te devuelva.
   Se activa una sola vez en esta computadora.

4. CREA TU CONTRASEÑA
   La primera vez te pedirá crear una contraseña de acceso: la
   necesitarás cada vez que abras el programa. Para cambiarla,
   usa el botón PERSONALIZAR (arriba) → CAMBIAR CONTRASEÑA.
   Si la olvidas, contacta a tu proveedor para restablecerla.

5. PERSONALIZA TU ENCABEZADO
   Botón PERSONALIZAR: tu nombre, dirección, teléfono, redes y logo.
   Aparecen en la ventana y en los PDF que imprimas.

6. TUS DATOS
   La base de datos se crea vacía junto al exe la primera vez
   (Nutrición_deportiva.db). Ahí viven tus pacientes y tu
   personalización: RESPALDA ESE ARCHIVO regularmente.

ACTUALIZACIONES
---------------
Cuando recibas una versión nueva, descomprímela aparte y copia tu
archivo Nutrición_deportiva.db a la carpeta nueva (o extrae la
versión nueva ENCIMA de tu carpeta actual sin borrar tu BD): tus
datos se conservan y el resto se actualiza.
"""


def _excluir(nombre):
    if nombre.lower().endswith(EXCLUIR_SUFIJOS):
        return True
    if nombre in EXCLUIR_NOMBRES:
        return True
    if nombre.startswith("respaldo"):
        return True
    return False


def main():
    if not os.path.isdir(ORIGEN):
        raise SystemExit(
            f"No existe {ORIGEN}: compila primero el exe con PyInstaller."
        )
    total = 0
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        # el LEEME va dentro de la carpeta del programa
        z.writestr(f"NutricionDeportiva/LEEME.txt", LEEME)
        total += 1
        for raiz, _dirs, archivos in os.walk(ORIGEN):
            for a in archivos:
                if _excluir(a):
                    continue
                ruta = os.path.join(raiz, a)
                rel = os.path.relpath(ruta, os.path.dirname(ORIGEN))
                z.write(ruta, rel)
                total += 1
    print(f"Zip de distribución: {DESTINO}")
    print(f"Archivos incluidos: {total} (sin BD del autor)")
    print(f"Tamaño: {os.path.getsize(DESTINO) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
