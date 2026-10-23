"""
Extrae las ilustraciones anatómicas del PDF de estiramientos y las guarda
como PNG (legibles por Tkinter) junto a un JPG original.

Uso: python extraer_estiramientos.py
"""
import io
import os
import sys

from PIL import Image
from pypdf import PdfReader

PDF = r"D:\Gan_profesional1\Deporte\Documentos\Estiramientos_por_grupo_muscular.pdf"
DESTINO = r"D:\Biblioteca\Nutrición_deportiva\estiramientos_img"
ANCHO_MAX = 1100

# página del PDF -> (numero, grupo, nombre_archivo)
MAPA = {
    3: ("01", "Brazos", "antebrazo"),
    4: ("02", "Brazos", "triceps"),
    5: ("03", "Hombros", "deltoides_anterior"),
    6: ("04", "Hombros", "manguito_rotadores"),
    7: ("05", "Hombros", "hombros"),
    8: ("06", "Pectorales", "pectoral_mayor"),
    9: ("07", "Espalda", "dorsal_ancho_redondo_mayor"),
    10: ("08", "Espalda", "barra_fija"),
    11: ("09", "Espalda", "deltoides_trapecio_cuello"),
    12: ("10", "Espalda", "trapecio_cuello"),
    13: ("11", "Piernas", "squat"),
    14: ("12", "Piernas", "cuadriceps"),
    15: ("13", "Piernas", "isquiotibiales"),
    16: ("14", "Piernas", "pantorrilla"),
    17: ("15", "Gluteos", "gluteo_mayor_isquiotibiales"),
    18: ("16", "Gluteos", "gluteos"),
    19: ("17", "Abdominales", "parte_superior_cuerpo"),
    20: ("18", "Abdominales", "abdominales"),
}


def main():
    os.makedirs(DESTINO, exist_ok=True)
    reader = PdfReader(PDF)
    indice = {}
    for numero_pagina, (num, grupo, slug) in MAPA.items():
        pagina = reader.pages[numero_pagina - 1]
        imagenes = list(pagina.images)
        if not imagenes:
            print(f"[AVISO] pagina {numero_pagina} sin imagen")
            continue
        datos = imagenes[0].data
        with Image.open(io.BytesIO(datos)) as img:
            img = img.convert("RGB")
            ancho, alto = img.size
            jpg = os.path.join(DESTINO, f"{num}_{slug}.jpg")
            png = os.path.join(DESTINO, f"{num}_{slug}.png")
            img.save(jpg, "JPEG", quality=92)
            if ancho > ANCHO_MAX:
                nuevo_alto = round(alto * ANCHO_MAX / ancho)
                img = img.resize((ANCHO_MAX, nuevo_alto), Image.LANCZOS)
            img.save(png, "PNG", optimize=True)
        indice[num] = {
            "grupo": grupo,
            "nombre_archivo": f"{num}_{slug}",
            "ruta_png": png,
            "ruta_jpg": jpg,
            "ancho": img.size[0],
            "alto": img.size[1],
        }
        print(f"{num} {grupo:12s} {slug:28s} {ancho}x{alto} -> {os.path.basename(png)}")

    # Portada
    portada = list(reader.pages[0].images)
    if portada:
        with Image.open(io.BytesIO(portada[0].data)) as img:
            img = img.convert("RGB")
            img.save(os.path.join(DESTINO, "portada.png"), "PNG", optimize=True)
            print("portada guardada")

    import json
    with open(os.path.join(DESTINO, "indice.json"), "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, indent=2)
    print(f"\n{len(indice)} ilustraciones en {DESTINO}")


if __name__ == "__main__":
    main()
