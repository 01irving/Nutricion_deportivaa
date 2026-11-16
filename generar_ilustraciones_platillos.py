# -*- coding: utf-8 -*-
"""
Genera ILUSTRACIONES planas para los platillos que no tienen imagen y
las guarda como imagen_blob en la BD (los platillos que ya tienen
imagen se dejan intactos).

Cada platillo se clasifica por palabras clave de su nombre (bebida,
taco, huevo, pollo, atún, arroz, pasta, ensalada, sopa, sándwich,
fruta, postre o plato genérico) y se dibuja una ilustración de 480x360
con el nombre del platillo.

Uso:
    python generar_ilustraciones_platillos.py [--db <ruta>] [--dry-run]
         [--max N]
"""
import io
import os
import sqlite3
import sys
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

RUTA = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(RUTA, 'Nutrición_deportiva.db')
DRY = '--dry-run' in sys.argv
MAX = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else None
SOLO = sys.argv[sys.argv.index('--tiempo') + 1] if '--tiempo' in sys.argv else None
if '--db' in sys.argv:
    DB = sys.argv[sys.argv.index('--db') + 1]

ANCHO, ALTO = 480, 360
FUENTE = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 24)
FUENTE_CHICA = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 16)

# paleta
FONDOS = [(248, 243, 232), (240, 246, 240), (245, 240, 246), (240, 244, 250),
          (250, 244, 238), (242, 246, 244)]
VERDE = (106, 168, 79)
VERDE_CLARO = (150, 200, 120)
ROJO = (205, 92, 92)
NARANJA = (243, 156, 18)
AMARILLO = (247, 202, 24)
MARRON = (160, 110, 60)
MARRON_CLARO = (222, 184, 135)
BLANCO = (252, 252, 250)
GRIS = (120, 120, 120)
ROSA = (240, 170, 180)
AZUL = (100, 149, 200)

# categorías en orden de prioridad: los platillos compuestos (tacos,
# sándwich, pollo con arroz) ganan sobre los ingredientes sueltos
# (verduras, frutas) que solo ilustran platillos de un solo ingrediente
CATEGORIAS = (
    (('batido', 'licuado', 'jugo de', 'agua de', 'agua con', 'té', 'te '),
     'bebida'),
    (('gelatina', 'flan', 'postre', 'nieve', 'helado'), 'postre'),
    (('taco', 'tacos', 'quesadilla', 'enchilada', 'chilaquiles'), 'taco'),
    (('sándwich', 'sandwich', 'torta ', 'baguette', 'burrito'), 'sandwich'),
    (('sopa', 'crema de', 'caldo', 'consomé'), 'sopa'),
    (('huevo', 'huevos'), 'huevo'),
    (('atún', 'atun', 'salmón', 'salmon', 'pescado', 'camarón', 'camaron',
      'mojarra', 'robalo', 'tilapia', 'langostino'), 'pescado'),
    (('pollo', 'pavo', ' res ', 'cerdo', 'lomo', 'jamón', 'jamon',
      ' filete', 'milanesa'), 'carne'),
    (('arroz',), 'arroz'),
    (('pasta', 'espagueti', 'espaguetí', 'fideos', 'macarron', 'macarrón'),
     'pasta'),
    (('frijol', 'lenteja', 'garbanzo', 'alubia', 'legumbre'), 'legumbre'),
    (('pan ', 'pan integral', 'galleta', 'avena', 'cereal'), 'pan'),
    (('fruta', 'manzana', 'papaya', 'guayaba', 'fresa', 'uva', 'mango',
      'mandarina', 'naranja', 'sandía', 'sandia', 'melón', 'melon',
      'pera', 'kiwi', 'plátano', 'platano', 'tuna'), 'fruta'),
    (('ensalada', 'verduras', 'verdura', 'brócoli', 'espinaca', 'nopal',
      'acelga', 'lechuga', 'col '), 'ensalada'),
)


def categoria_de(nombre):
    nombre = ' ' + nombre.lower() + ' '
    for palabras, cat in CATEGORIAS:
        if any(p in nombre for p in palabras):
            return cat
    return 'plato'


def centrar_texto(draw, y, texto, fuente, color, ancho=ANCHO):
    caja = draw.textbbox((0, 0), texto, font=fuente)
    x = (ancho - (caja[2] - caja[0])) // 2 - caja[0]
    draw.text((x, y), texto, font=fuente, fill=color)


def envolver(nombre, limite=26):
    """Parte el nombre en renglones cortos para la tarjeta."""
    palabras = nombre.split()
    renglones, actual = [], ''
    for p in palabras:
        prueba = (actual + ' ' + p).strip()
        if len(prueba) > limite and actual:
            renglones.append(actual)
            actual = p
        else:
            actual = prueba
    if actual:
        renglones.append(actual)
    return renglones[:3]


def base(nombre, fondo):
    img = Image.new('RGB', (ANCHO, ALTO), fondo)
    d = ImageDraw.Draw(img)
    # tarjeta blanca redondeada
    d.rounded_rectangle((24, 20, ANCHO - 24, ALTO - 78), radius=22,
                        fill=BLANCO, outline=(225, 220, 210), width=2)
    # plato
    d.ellipse((90, 60, 390, 250), fill=(255, 255, 255),
              outline=(220, 214, 205), width=3)
    d.ellipse((110, 78, 370, 232), fill=(248, 246, 242))
    renglones = envolver(nombre)
    y = ALTO - 66
    for r in renglones:
        centrar_texto(d, y, r, FUENTE, (70, 70, 70))
        y += 30
    return img, d


def dib_bebida(nombre, fondo, color_liquido=ROSA):
    img, d = base(nombre, fondo)
    # vaso
    d.polygon([(200, 95), (280, 95), (270, 220), (210, 220)],
              fill=(235, 240, 245), outline=(200, 205, 210), width=2)
    d.polygon([(206, 120), (274, 120), (267, 214), (213, 214)],
              fill=color_liquido)
    # pajita
    d.line([(258, 78), (274, 110)], fill=ROJO, width=5)
    # burbujas
    for (x, y, r) in ((222, 190, 6), (248, 180, 5), (236, 200, 4)):
        d.ellipse((x - r, y - r, x + r, y + r), outline=BLANCO, width=2)
    # rebanada de fruta en el borde
    d.ellipse((186, 96, 212, 122), fill=AMARILLO, outline=NARANJA, width=3)
    return img


def dib_taco(nombre, fondo):
    img, d = base(nombre, fondo)
    # concha de taco (semicírculo doblado)
    d.pieslice((130, 110, 350, 260), 180, 360, fill=MARRON_CLARO,
               outline=MARRON, width=3)
    # relleno (lechuga, tomate, carne)
    for (x, y, r, c) in ((185, 158, 10, VERDE_CLARO), (215, 152, 9, ROJO),
                         (245, 158, 10, VERDE_CLARO), (275, 152, 9, ROJO),
                         (200, 168, 9, MARRON), (235, 168, 9, MARRON)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    return img


def dib_huevo(nombre, fondo):
    img, d = base(nombre, fondo)
    # sartén
    d.ellipse((120, 100, 360, 240), fill=(70, 70, 75),
              outline=(50, 50, 55), width=3)
    # claros (2 huevos estrellados)
    for cx, cy in ((195, 168), (285, 162)):
        d.ellipse((cx - 42, cy - 34, cx + 42, cy + 34), fill=BLANCO)
        d.ellipse((cx - 16, cy - 13, cx + 16, cy + 13), fill=AMARILLO,
                  outline=(230, 170, 40), width=2)
    # mango
    d.rectangle((348, 150, 395, 168), fill=(60, 60, 65))
    return img


def dib_carne(nombre, fondo):
    img, d = base(nombre, fondo)
    # muslo de pollo: elipse + hueso
    d.ellipse((170, 120, 320, 220), fill=MARRON_CLARO, outline=MARRON,
              width=3)
    d.ellipse((295, 195, 335, 230), fill=BLANCO, outline=(210, 205, 195),
              width=2)
    d.ellipse((320, 175, 360, 210), fill=BLANCO, outline=(210, 205, 195),
              width=2)
    # líneas de grill
    d.arc((195, 140, 295, 200), 20, 160, fill=MARRON, width=4)
    d.arc((195, 155, 295, 215), 20, 160, fill=MARRON, width=4)
    # guarnición: tomates cherry
    d.ellipse((140, 195, 168, 222), fill=ROJO)
    d.ellipse((330, 130, 358, 158), fill=ROJO)
    return img


def dib_pescado(nombre, fondo):
    img, d = base(nombre, fondo)
    # pescado
    d.ellipse((150, 130, 330, 210), fill=(150, 190, 220),
              outline=(90, 130, 165), width=3)
    d.polygon([(320, 170), (365, 140), (365, 200)], fill=(120, 165, 200),
              outline=(90, 130, 165))
    d.ellipse((185, 155, 205, 175), fill=(30, 40, 50))
    d.arc((200, 150, 300, 200), 200, 340, fill=(90, 130, 165), width=3)
    # rodaja de limón
    d.ellipse((120, 180, 158, 218), fill=AMARILLO, outline=NARANJA, width=3)
    return img


def dib_arroz(nombre, fondo, color=MARRON_CLARO):
    img, d = base(nombre, fondo)
    # bowl
    d.pieslice((130, 130, 350, 330), 180, 360, fill=AZUL,
               outline=(80, 120, 165), width=3)
    d.ellipse((150, 118, 330, 152), fill=(250, 248, 242))
    # montículo
    d.ellipse((170, 110, 310, 145), fill=color)
    for (x, y) in ((200, 125), (230, 120), (262, 124), (288, 120)):
        d.ellipse((x - 4, y - 3, x + 4, y + 3), fill=BLANCO)
    return img


def dib_pasta(nombre, fondo):
    img = dib_arroz(nombre, fondo, color=(240, 205, 130))
    d = ImageDraw.Draw(img)
    # hilos de pasta
    for y in (118, 124, 130):
        d.arc((185, y - 8, 300, y + 8), 0, 180, fill=(226, 180, 90), width=4)
    # albóndiga
    d.ellipse((225, 108, 265, 140), fill=MARRON, outline=(130, 88, 42),
              width=2)
    return img


def dib_ensalada(nombre, fondo):
    img, d = base(nombre, fondo)
    # bowl
    d.pieslice((130, 130, 350, 330), 180, 360, fill=VERDE,
               outline=(86, 140, 62), width=3)
    d.ellipse((150, 118, 330, 152), fill=(250, 248, 242))
    # hojas
    for (x, y) in ((195, 122), (235, 114), (275, 122)):
        d.ellipse((x - 22, y - 15, x + 22, y + 15), fill=VERDE_CLARO,
                  outline=(90, 150, 66), width=2)
    # jitomate
    d.ellipse((262, 126, 292, 150), fill=ROJO)
    return img


def dib_sopa(nombre, fondo):
    img, d = base(nombre, fondo)
    d.pieslice((130, 135, 350, 335), 180, 360, fill=(250, 248, 242),
               outline=(210, 205, 195), width=3)
    d.ellipse((150, 122, 330, 158), fill=(250, 236, 210))
    # vapor
    for x in (210, 245, 280):
        d.arc((x - 14, 78, x + 14, 118), 270, 90, fill=(190, 190, 190),
              width=4)
    # cuchara
    d.line([(320, 90), (330, 150)], fill=GRIS, width=6)
    d.ellipse((306, 60, 342, 96), fill=GRIS)
    return img


def dib_sandwich(nombre, fondo):
    img, d = base(nombre, fondo)
    # pan de arriba
    d.rounded_rectangle((140, 130, 340, 165), radius=18, fill=(240, 200, 140),
                        outline=MARRON, width=3)
    # relleno
    d.rectangle((148, 165, 332, 180), fill=VERDE_CLARO)
    d.rectangle((148, 180, 332, 194), fill=ROSA)
    d.rectangle((148, 194, 332, 208), fill=AMARILLO)
    # pan de abajo
    d.rounded_rectangle((140, 208, 340, 243), radius=18,
                        fill=(228, 188, 126), outline=MARRON, width=3)
    # palillo
    d.line([(240, 122), (240, 252)], fill=ROJO, width=5)
    d.ellipse((234, 116, 246, 128), fill=ROJO)
    return img


def dib_fruta(nombre, fondo):
    img, d = base(nombre, fondo)
    # manzana
    d.ellipse((185, 125, 300, 240), fill=ROJO, outline=(170, 70, 70),
              width=3)
    d.polygon([(240, 128), (248, 100), (254, 128)], fill=MARRON)
    d.ellipse((250, 102, 288, 124), fill=VERDE_CLARO)
    # brillo
    d.arc((205, 140, 280, 230), 130, 190, fill=(235, 160, 160), width=5)
    return img


def dib_legumbre(nombre, fondo):
    img, d = base(nombre, fondo)
    d.pieslice((130, 130, 350, 330), 180, 360, fill=BLANCO,
               outline=(210, 205, 195), width=3)
    d.ellipse((150, 118, 330, 152), fill=(250, 240, 228))
    for (x, y) in ((200, 122), (240, 118), (280, 122)):
        d.ellipse((x - 14, y - 9, x + 14, y + 9), fill=MARRON,
                  outline=(120, 80, 40), width=2)
    return img


def dib_postre(nombre, fondo):
    img, d = base(nombre, fondo)
    # molde/copa de gelatina
    d.polygon([(170, 120), (310, 120), (290, 230), (190, 230)],
              fill=(240, 130, 160), outline=(200, 100, 125), width=3)
    d.ellipse((160, 106, 320, 134), fill=(248, 150, 172),
              outline=(200, 100, 125), width=3)
    # fresa encima
    d.ellipse((228, 92, 258, 120), fill=ROJO)
    d.line([(243, 90), (243, 78)], fill=VERDE, width=3)
    return img


def dib_plato(nombre, fondo):
    img, d = base(nombre, fondo)
    # campana de plato servido
    d.ellipse((170, 125, 310, 225), fill=(245, 238, 228),
              outline=(210, 203, 192), width=3)
    d.arc((170, 125, 310, 225), 180, 360, fill=(190, 183, 172), width=4)
    d.ellipse((200, 150, 280, 200), fill=VERDE_CLARO)
    d.ellipse((215, 158, 265, 192), fill=MARRON_CLARO)
    return img


DIBUJOS = {
    'bebida': lambda n, f: dib_bebida(n, f, ROSA),
    'postre': dib_postre,
    'taco': dib_taco,
    'sandwich': dib_sandwich,
    'pan': dib_sandwich,
    'ensalada': dib_ensalada,
    'sopa': dib_sopa,
    'arroz': dib_arroz,
    'pasta': dib_pasta,
    'huevo': dib_huevo,
    'pescado': dib_pescado,
    'carne': dib_carne,
    'legumbre': dib_legumbre,
    'fruta': dib_fruta,
    'plato': dib_plato,
}


def generar(nombre):
    cat = categoria_de(nombre)
    color_fondo = FONDOS[len(nombre) % len(FONDOS)]
    img = DIBUJOS.get(cat, dib_plato)(nombre, color_fondo)
    bufer = io.BytesIO()
    img.save(bufer, 'JPEG', quality=88)
    return bufer.getvalue(), cat


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    pendientes = con.execute(
        'SELECT COUNT(*) FROM platillos WHERE imagen_blob IS NULL'
    ).fetchone()[0]
    print(f'platillos sin imagen: {pendientes}')

    if not DRY:
        respaldo = DB.replace(
            '.db', f'_respaldo_ilustraciones_{datetime.now():%Y%m%d_%H%M%S}.db')
        import shutil
        shutil.copy(DB, respaldo)
        print(f'Respaldo: {respaldo}')

    consulta = ('SELECT id_platillo, nombre, tiempo_comida FROM platillos '
                'WHERE imagen_blob IS NULL ORDER BY tiempo_comida, nombre')
    parametros = []
    if SOLO:
        consulta += ' AND tiempo_comida LIKE ?'
        parametros.append('%' + SOLO + '%')
    if MAX:
        consulta += ' LIMIT ?'
        parametros.append(MAX)
    filas = con.execute(consulta, parametros).fetchall()

    histograma = {}
    generadas = 0
    for f in filas:
        blob, cat = generar(f['nombre'])
        histograma[cat] = histograma.get(cat, 0) + 1
        if DRY:
            continue
        with con:
            con.execute(
                'UPDATE platillos SET imagen_blob = ?, imagen_nombre = ?, '
                "actualizado_en = datetime('now', 'localtime') "
                'WHERE id_platillo = ?',
                (sqlite3.Binary(blob),
                 f'Ilustración generada — {cat}',
                 f['id_platillo']))
        generadas += 1
        if generadas % 50 == 0:
            print(f'  generadas: {generadas}')

    print('categorias:', dict(sorted(histograma.items(),
                                     key=lambda x: -x[1])))
    con.close()
    if DRY:
        print('DRY: no se escribió nada')
        return 0
    print(f'ilustraciones generadas: {generadas}')
    print('LISTO')
    return 0


if __name__ == '__main__':
    sys.exit(main())
