"""
Carga los platillos PRE-ENTRENO al catálogo, divididos por anticipación:

  - "Preentreno 30 min": algo líquido o muy ligero (batido whey + fruta).
  - "Preentreno 1-2 h":  comida normal de carbos + proteína y poca grasa.

Basado en el resumen del video "Basics of Diet" (Felix Harder, curso Alison):
la comida pre y post entreno llevan 0.45-0.55 g/kg de proteína y de
carbohidratos, evitando la grasa justo antes de entrenar.

Los alimentos de paquete se definieron con valores promedio de etiqueta
(NOM-051, México): whey 1 scoop 30 g ≈ 120 kcal / 24 g proteína
(eatthismuch.com); barrita de proteína 50 g ≈ 190 kcal / 17 g proteína
(análisis Proyecto VERA / XGEAR 57 g: 21 g prot).

Uso:
    python cargar_preentreno.py [--dry-run]
"""
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime

from cargar_menu_gimnasio import (
    CAMPOS,
    C,
    DB,
    X,
    construir_ingredientes,
    cargar_catalogo,
)

DRY = '--dry-run' in sys.argv

# --- Alimentos de paquete (valores promedio de etiqueta, por equivalente) --
WHEY = X('Whey proteina (1 scoop 30 g)', 'Leche descremada', 1,
         'scoop (30 g)', 30, 120, 24, 1.5, 3, 0, 1, 0, 0, 0, 0.1, 125,
         160, 65)
BARRITA = X('Barrita de proteina (1 pieza 50 g)', 'Cereales con grasa', 1,
            'barrita (50 g)', 50, 190, 17, 5, 15, 3, 2, 0, 0, 0, 1.2, 100,
            180, 140)
YOGURT_GRIEGO = X('Yogurt griego natural sin azúcar', 'Leche entera', 0.5,
                  'taza', 120, 115, 10.6, 5.6, 4.2, 0, 4.2, 30, 0, 8, 0.1,
                  120, 160, 40)

WHEY_FUENTE = ('Fuente: video Basics of Diet (Felix Harder, Alison); '
               'valores de whey: etiqueta promedio por scoop de 30 g '
               '(eatthismuch.com).')

# ===========================================================================
# PLATILLOS — ing: (alimento, equivalentes)
# ===========================================================================
PLATILLOS = [
    # ------------------------- PREENTRENO 30 MIN -------------------------- #
    {
        'nombre': 'Batido de whey con plátano en agua',
        'tiempo': 'Preentreno 30 min',
        'ing': [(WHEY, 1), (C('Platano'), 2)],
        'prep': ('Opción líquida 15-30 min antes de entrenar.\n'
                 '1. Licuar 1 scoop de whey en 350 ml de agua con hielo.\n'
                 '2. Agregar 1 plátano y licuar hasta que quede terso.\n'
                 '3. Tomarlo lentamente al terminarlo.\n'
                 'Nota: cantidades para ~80 kg; ajusta el scoop a tu peso '
                 '(0.45-0.55 g/kg de proteína en la comida pre).\n'
                 + WHEY_FUENTE),
    },
    {
        'nombre': 'Batido de whey con leche descremada y uvas',
        'tiempo': 'Preentreno 30 min',
        'ing': [(WHEY, 1), (C('leche descremada'), 1), (C('Uva roja'), 1)],
        'prep': ('Opción líquida 15-30 min antes de entrenar.\n'
                 '1. Licuar 1 scoop de whey con 1 taza de leche descremada '
                 '(o agua si prefieres sin lácteos).\n'
                 '2. Agregar 1 taza de uvas y licuar.\n'
                 '3. Tomar frío.\n'
                 + WHEY_FUENTE),
    },
    {
        'nombre': 'Licuado de whey con papaya',
        'tiempo': 'Preentreno 30 min',
        'ing': [(WHEY, 1), (C('Papaya picada'), 1)],
        'prep': ('Opción líquida 15-30 min antes de entrenar.\n'
                 '1. Licuar 1 scoop de whey con 1 taza de papaya picada y '
                 '300 ml de agua fría.\n'
                 '2. Endulzar al gusto sin azúcar (o nada).\n'
                 '3. Tomarlo de inmediato.\n'
                 + WHEY_FUENTE),
    },
    {
        'nombre': 'Whey con galletas Marías',
        'tiempo': 'Preentreno 30 min',
        'ing': [(WHEY, 1), (C('Galletas Marías'), 0.4)],
        'prep': ('Opción práctica 30 min antes de entrenar.\n'
                 '1. Preparar el whey: 1 scoop en 350 ml de agua.\n'
                 '2. Acompañar con 2 galletas Marías.\n'
                 'Nota: opción rápida cuando no hay fruta ni licuadora; '
                 'las galletas aportan carbohidratos de fácil digestión.\n'
                 + WHEY_FUENTE),
    },
    # ------------------------ PREENTRENO 1-2 HORAS ------------------------ #
    {
        'nombre': 'Avena cocida con whey y plátano',
        'tiempo': 'Preentreno 1-2 h',
        'ing': [(C('Avena en hojuelas'), 1), (C('leche descremada'), 1),
                (WHEY, 1), (C('Platano'), 2)],
        'prep': ('Comida pre-entreno 1-2 h antes (carbos + proteína, poca '
                 'grasa).\n'
                 '1. Cocinar ½ taza de avena en hojuelas con 1 taza de '
                 'leche descremada y un poco de agua, 3-5 minutos.\n'
                 '2. Retirar del fuego, dejar entibiar y mezclar el scoop '
                 'de whey (no hierva para no dañar la proteína).\n'
                 '3. Servir con el plátano en rebanadas y canela al gusto.\n'
                 'Fuente: video Basics of Diet — avena con whey como '
                 'comida pre ~1 h antes; ' + WHEY_FUENTE.replace(
                     'Fuente: ', '')),
    },
    {
        'nombre': 'Sándwich integral de pollo',
        'tiempo': 'Preentreno 1-2 h',
        'ing': [(C('Pan integral'), 2),
                (C('Pechuga de pollo sin piel cocida'), 3),
                (C('Jitomate bola'), 0.5), (C('Mandarina reyna'), 1)],
        'prep': ('Comida pre-entreno 1-2 h antes.\n'
                 '1. Cocer o asar la pechuga sin piel y deshebrar o '
                 'rebanar (90 g).\n'
                 '2. Armar el sándwich con 2 rebanadas de pan integral, '
                 'el pollo y rebanadas de jitomate; mostaza o limón en '
                 'lugar de mayonesa (evita la grasa antes de entrenar).\n'
                 '3. Acompañar con 1 mandarina.\n'
                 'Fuente: video Basics of Diet — sándwich integral de '
                 'pollo como comida pre ~1 h antes.'),
    },
    {
        'nombre': 'Huevos con aguacate y pan integral',
        'tiempo': 'Preentreno 1-2 h',
        'ing': [(C('Huevo entero fresco'), 2), (C('Pan integral'), 2),
                (C('Aguacate California'), 1.5)],
        'prep': ('Comida pre-entreno 1-2 h antes (la grasa del aguacate '
                 'se digiere bien con este margen).\n'
                 '1. Preparar los huevos al gusto (revueltos o cocidos, '
                 'con poco aceite).\n'
                 '2. Servir con 2 rebanadas de pan integral tostado.\n'
                 '3. Acompañar con ½ aguacate en rebanadas, sal y limón.\n'
                 'Fuente: video Basics of Diet — huevos con aguacate como '
                 'comida pre ~1 h antes.'),
    },
    {
        'nombre': 'Yogurt griego con granola y fresas',
        'tiempo': 'Preentreno 1-2 h',
        'ing': [(YOGURT_GRIEGO, 2), (C('Granola baja en grasa'), 1),
                (C('Fresa rebanada'), 0.5)],
        'prep': ('Comida pre-entreno 1-2 h antes.\n'
                 '1. Servir 1 taza de yogurt griego natural sin azúcar.\n'
                 '2. Agregar 3 cucharadas de granola baja en grasa.\n'
                 '3. Coronar con ½ taza de fresas rebanadas.\n'
                 'Fuente: video Basics of Diet — yogurt griego entre las '
                 'proteínas de calidad.'),
    },
    {
        'nombre': 'Pan integral con atún y fruta',
        'tiempo': 'Preentreno 1-2 h',
        'ing': [(C('Pan integral'), 2), (C('Atún en agua drenado'), 1.5),
                (C('Mandarina reyna'), 1)],
        'prep': ('Comida pre-entreno 1-2 h antes.\n'
                 '1. Escurrir ½ lata de atún en agua y desmenuzarlo.\n'
                 '2. Servirlo sobre 2 rebanadas de pan integral tostado '
                 '(con limón y pimienta; sin mayonesa).\n'
                 '3. Acompañar con 1 mandarina.\n'
                 'Fuente: video Basics of Diet — enlatados de proteína '
                 'de calidad; carbos + proteína en la comida pre.'),
    },
    {
        'nombre': 'Licuado de avena, leche y plátano (sin whey)',
        'tiempo': 'Preentreno 1-2 h',
        'ing': [(C('leche descremada'), 2), (C('Avena en hojuelas'), 1),
                (C('Platano'), 2)],
        'prep': ('Comida pre-entreno 1-2 h antes, opción natural sin '
                 'suplemento.\n'
                 '1. Licuar 2 tazas de leche descremada con ½ taza de '
                 'avena en hojuelas y 1 plátano.\n'
                 '2. Agregar canela o vainilla al gusto.\n'
                 '3. Tomarlo fresco 1-2 h antes de entrenar.\n'
                 'Fuente: video Basics of Diet — la comida pre es carbos '
                 '+ proteína; la proteína puede venir de lácteos.'),
    },
    {
        'nombre': 'Barrita de proteína con plátano',
        'tiempo': 'Preentreno 1-2 h',
        'ing': [(BARRITA, 1), (C('Platano'), 1)],
        'prep': ('Comida pre-entreno 1-2 h antes, opción de paquete '
                 '(ideal para comer fuera de casa).\n'
                 '1. Elegir una barrita con más proteína que carbohidratos '
                 'en su etiqueta y sin azúcares añadidos.\n'
                 '2. Acompañar con ½ plátano (o 1 chico).\n'
                 '3. Tomar agua.\n'
                 'Fuente: etiquetas NOM-051 México; barritas comerciales '
                 '~200-270 kcal y 15-22 g proteína por pieza (Proyecto '
                 'VERA / XGEAR 57 g: 21 g prot).'),
    },
]

FUENTE_GENERAL = ('División por anticipación basada en el video '
                  '"Basics of Diet" (Felix Harder, curso Fitness Coaching '
                  'Gym Workouts and Bodybuilding de Alison): pre ~1 h '
                  'comida normal de carbos + proteína (0.45-0.55 g/kg de '
                  'cada uno) y algo líquido 30 min antes (batido + '
                  'plátano), evitando la grasa justo antes de entrenar.')


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    catalogo = cargar_catalogo(con)
    if not DRY:
        respaldo = DB.replace(
            '.db', f'_respaldo_preentreno_{datetime.now():%Y%m%d_%H%M%S}.db')
        shutil.copy(DB, respaldo)
        print(f'Respaldo: {respaldo}')

    filas = []
    for p in PLATILLOS:
        ingredientes, tot = construir_ingredientes(p, catalogo)
        filas.append({**p, 'ingredientes': ingredientes, 'totales': tot})

    for f in filas:
        print(f'  {f["tiempo"]:20} | {f["nombre"]:44} | '
              f'{f["totales"]["energia_kcal"]:5.0f} kcal | '
              f'P {f["totales"]["proteina_g"]:4.1f} g | '
              f'HC {f["totales"]["hc_g"]:4.1f} g | '
              f'L {f["totales"]["lipidos_g"]:3.1f} g')
        for r in f['ingredientes']:
            print(f'        {r["eq_cantidad"]:>5g} eq  '
                  f'{r["cantidad_txt"]:20} {r["alimento"]}')
    if DRY:
        con.close()
        return 0

    with con:
        for f in filas:
            datos = (json.dumps(f['ingredientes'], ensure_ascii=False),
                     json.dumps(f['totales'], ensure_ascii=False),
                     f['prep'])
            fila = con.execute(
                'SELECT id_platillo FROM platillos WHERE nombre = ? AND '
                'tiempo_comida = ?', (f['nombre'], f['tiempo'])).fetchone()
            if fila:
                con.execute(
                    'UPDATE platillos SET ingredientes = ?, totales = ?, '
                    'modo_preparacion = ?, '
                    "actualizado_en = datetime('now', 'localtime') "
                    'WHERE id_platillo = ?', datos + (fila[0],))
            else:
                con.execute(
                    'INSERT INTO platillos (nombre, tiempo_comida, '
                    'ingredientes, totales, modo_preparacion, '
                    'imagen_nombre, imagen_blob, creado_en, actualizado_en) '
                    'VALUES (?, ?, ?, ?, ?, NULL, NULL, '
                    "datetime('now', 'localtime'), "
                    "datetime('now', 'localtime'))",
                    (f['nombre'], f['tiempo']) + datos)
        con.execute(
            "INSERT INTO configuracion (clave, valor) VALUES "
            "('preentreno_fuente', ?) ON CONFLICT(clave) DO UPDATE SET "
            "valor = excluded.valor", (FUENTE_GENERAL,))

    con.close()
    print(f'\n{FUENTE_GENERAL}')
    print('LISTO')
    return 0


if __name__ == '__main__':
    sys.exit(main())
