# -*- coding: utf-8 -*-
"""
Carga los platillos POS-ENTRENO al catálogo, divididos por ventana de
administración después del gym:

  - "Posentreno 0-30 min": rápido/líquido (batido + fruta) — carbohidratos
    0.6-1.0 g/kg en los primeros 30 min y 20-40 g de proteína.
  - "Posentreno 30-60 min": sólido ligero de proteína + carbohidratos.
  - "Posentreno 1-2 h": comida completa (proteína 0.4-0.5 g/kg,
    carbohidratos 1.0-1.2 g/kg y verdura).

Basado en artículos científicos:

  * Kerksick CM, et al. 2017. "International society of sports nutrition
    position stand: nutrient timing". J Int Soc Sports Nutr 14:38
    (PMC5596471): carbohidratos 0.6-1.0 g/kg dentro de los primeros
    30 minutos tras ejercicio extenuante, repitiendo cada 2 h; para
    reponer glucógeno rápido 1.0-1.2 g/kg/h las primeras 3-5 h; proteína
    en dosis de 20-40 g.
  * Aragon AA, Schoenfeld BJ 2013. "Nutrient timing revisited: is there a
    post-exercise anabolic window?" J Int Soc Sports Nutr 10:5
    (PMC3577439): proteína de alta calidad 0.4-0.5 g/kg antes y después
    del entrenamiento; la comida pre y la post no deben separarse más de
    3-4 h (la ventana anabólica es flexible).
  * Schoenfeld BJ, Aragon AA 2018 (JOSPT 48:3): si la comida pre fue
    1-2 h antes, la post pierde urgencia; entrenando en ayunas la
    proteína post sí importa pronto.

Uso:
    python cargar_posentreno.py [--dry-run]
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
from cargar_preentreno import WHEY, BARRITA, YOGURT_GRIEGO

DRY = '--dry-run' in sys.argv

# --db <ruta>: llenar OTRA base de datos (p. ej. la BD de la app
# instalada, que el actualizador nunca sobreescribe)
if '--db' in sys.argv:
    DB = sys.argv[sys.argv.index('--db') + 1]

# --- Alimentos de paquete adicionales (valores por equivalente) ----------
MIEL = X('Miel de abeja', 'Azucares sin grasa', 1, 'cucharada (21 g)', 21,
         64, 0.06, 0, 17.3, 0, 17.2, 0, 0, 0, 0.1, 11, 52, 4)

FUENTE_GENERAL = ('Basado en artículos científicos — Kerksick CM et al. '
                  '2017, ISSN position stand: nutrient timing (JISSN 14:38): '
                  'carbohidratos 0.6-1.0 g/kg en los primeros 30 min tras '
                  'ejercicio extenuante y 1.0-1.2 g/kg/h las primeras 3-5 h '
                  'para reponer glucógeno; proteína en tomas de 20-40 g. '
                  'Aragon AA & Schoenfeld BJ 2013, "Nutrient timing '
                  'revisited" (JISSN 10:5): proteína 0.4-0.5 g/kg antes y '
                  'después, con la comida pre y la post separadas 3-4 h como '
                  'máximo; entrenando en ayunas la proteína post es más '
                  'urgente (Schoenfeld & Aragon 2018, JOSPT 48:3). '
                  'Cantidades calculadas para ~80 kg.')

# ===========================================================================
# PLATILLOS — ing: (alimento, equivalentes)
# ===========================================================================
PLATILLOS = [
    # ------------------------- POSENTRENO 0-30 MIN ------------------------ #
    {
        'nombre': 'Batido recuperador de whey con plátano y avena',
        'tiempo': 'Posentreno 0-30 min',
        'ing': [(WHEY, 1), (C('Platano'), 3), (C('Avena en hojuelas'), 1)],
        'prep': ('Administración: 0-30 min después de entrenar.\n'
                 '1. Licuar 1 scoop de whey en 350 ml de agua con 1 plátano y '
                 'medio y 1 taza de avena en hojuelas.\n'
                 '2. Tomarlo de inmediato, frío.\n'
                 'Aporta ~29 g de proteína y ~58 g de carbohidratos '
                 '(≈0.7 g/kg para 80 kg): la proteína activa la síntesis '
                 'muscular y el carbohidrato repone glucógeno (ISSN 2017).\n'
                 + FUENTE_GENERAL),
    },
    {
        'nombre': 'Leche chocolateada con avena',
        'tiempo': 'Posentreno 0-30 min',
        'ing': [(C('leche descremada'), 2), (WHEY, 0.5), (C('Platano'), 1),
                (MIEL, 2)],
        'prep': ('Administración: 0-30 min después de entrenar.\n'
                 '1. Licuar 2 tazas de leche descremada con ½ scoop de '
                 'whey, 1 plátano y 2 cucharadas de miel.\n'
                 '2. Servir frío.\n'
                 'La leche + miel + plátano dan carbohidratos de '
                 'absorción rápida (relación ~3:1 carbohidratos:proteína, '
                 'la que mejor repone glucógeno según el ISSN).\n'
                 + FUENTE_GENERAL),
    },
    {
        'nombre': 'Licuado de yogurt griego con fresa y uva',
        'tiempo': 'Posentreno 0-30 min',
        'ing': [(YOGURT_GRIEGO, 2), (C('Fresa rebanada'), 1),
                (C('Uva roja'), 2)],
        'prep': ('Administración: 0-30 min después de entrenar, opción '
                 'sin suplemento.\n'
                 '1. Licuar 1 taza de yogurt griego natural con 1 taza de '
                 'fresas y 2 tazas de uvas.\n'
                 '2. Si queda espeso, agregar agua fría.\n'
                 'Proteína de calidad de lácteos + carbohidratos de fruta '
                 '(la proteína de la comida pre y la post no deben '
                 'separarse más de 3-4 h: Aragon & Schoenfeld 2013).\n'
                 + FUENTE_GENERAL),
    },
    {
        'nombre': 'Whey con galletas Marías y guayaba',
        'tiempo': 'Posentreno 0-30 min',
        'ing': [(WHEY, 1), (C('Galletas Marías'), 2), (C('Guayaba'), 1)],
        'prep': ('Administración: 0-30 min después de entrenar, opción '
                 'práctica para comer fuera del gimnasio.\n'
                 '1. Preparar 1 scoop de whey en 350 ml de agua.\n'
                 '2. Acompañar con 10 galletas Marías y 1 guayaba.\n'
                 'Carbohidratos simples que entran rápido justo cuando el '
                 'músculo los pide (ISSN 2017: 0.6-1.0 g/kg en los '
                 'primeros 30 min).\n'
                 + FUENTE_GENERAL),
    },
    # ------------------------ POSENTRENO 30-60 MIN ------------------------ #
    {
        'nombre': 'Sándwich integral de atún con mandarina',
        'tiempo': 'Posentreno 30-60 min',
        'ing': [(C('Pan integral'), 2), (C('Atún en agua drenado'), 2),
                (C('Mandarina reyna'), 1)],
        'prep': ('Administración: 30-60 min después de entrenar.\n'
                 '1. Escurrir una lata de atún en agua y desmenuzarlo '
                 'sobre 2 rebanadas de pan integral tostado (limón y '
                 'pimienta, sin mayonesa).\n'
                 '2. Terminar con 1 mandarina.\n'
                 '~30 g de proteína + carbohidratos: la dupla que acelera '
                 'la recuperación (ISSN 2017).\n'
                 + FUENTE_GENERAL),
    },
    {
        'nombre': 'Tacos de huevo con queso panela',
        'tiempo': 'Posentreno 30-60 min',
        'ing': [(C('Huevo entero fresco'), 3), (C('Tortilla de maíz'), 3),
                (C('Queso panela'), 1), (C('Salsa de chile'), 0.5)],
        'prep': ('Administración: 30-60 min después de entrenar.\n'
                 '1. Revolver 3 huevos y cocinarlos con poco aceite.\n'
                 '2. Calentar 3 tortillas de maíz y armar tacos con el '
                 'huevo y 1 rebanada de queso panela; salsa al gusto.\n'
                 'Tortilla (maíz) + huevo + panela: carbohidratos y '
                 'proteína en la ventana de recuperación.\n'
                 + FUENTE_GENERAL),
    },
    {
        'nombre': 'Pan integral con jamón de pavo y plátano',
        'tiempo': 'Posentreno 30-60 min',
        'ing': [(C('Pan integral'), 2), (C('Jamón de pavo'), 2),
                (C('Platano'), 2)],
        'prep': ('Administración: 30-60 min después de entrenar.\n'
                 '1. Armar un sándwich con 2 rebanadas de pan integral y '
                 '2 rebanadas de jamón de pavo (sin mayonesa).\n'
                 '2. Acompañar con 1 plátano grande (o 2 chicos).\n'
                 'El plátano repone potasio y carbohidratos junto al '
                 'glucógeno gastado (ISSN 2017).\n'
                 + FUENTE_GENERAL),
    },
    {
        'nombre': 'Barrita de proteína con jugo de naranja',
        'tiempo': 'Posentreno 30-60 min',
        'ing': [(BARRITA, 1), (C('Jugo de naranja natural'), 2)],
        'prep': ('Administración: 30-60 min después de entrenar, opción '
                 'de paquete.\n'
                 '1. Elegir una barrita con más proteína que azúcares en '
                 'la etiqueta.\n'
                 '2. Acompañar con 2 vasos de jugo de naranja natural.\n'
                 'El jugo aporta carbohidratos rápidos (vitamina C incluida) '
                 'para la ventana de recuperación.\n'
                 + FUENTE_GENERAL),
    },
    # ------------------------- POSENTRENO 1-2 H --------------------------- #
    {
        'nombre': 'Pechuga de pollo con arroz y verduras',
        'tiempo': 'Posentreno 1-2 h',
        'ing': [(C('Pechuga de pollo sin piel a la plancha'), 4),
                (C('Arroz cocido'), 4), (C('Brócoli crudo'), 1),
                (C('Zanahoria picada cruda'), 1),
                (C('Aceite de oliva extra virgen'), 1)],
        'prep': ('Administración: 1-2 h después de entrenar (comida '
                 'completa).\n'
                 '1. Cocinar 4 equivalentes de pechuga a la plancha.\n'
                 '2. Servir con 1 taza de arroz y verduras al '
                 'vapor (brócoli + zanahoria) con aceite de oliva.\n'
                 'Proteína 0.4-0.5 g/kg y carbohidratos ~1.0 g/kg: la '
                 'comida que mejor recupera para el siguiente entreno '
                 '(Aragon & Schoenfeld 2013; reponer glucógeno 1.0-1.2 '
                 'g/kg/h: ISSN 2017).\n'
                 + FUENTE_GENERAL),
    },
    {
        'nombre': 'Atún con espagueti integral y brócoli',
        'tiempo': 'Posentreno 1-2 h',
        'ing': [(C('Atún en agua drenado'), 2),
                (C('Espagueti integral cocido'), 4), (C('Brócoli crudo'), 1),
                (C('Aceite de oliva extra virgen'), 1)],
        'prep': ('Administración: 1-2 h después de entrenar.\n'
                 '1. Saltear 2 equivalentes de atún escurrido con '
                 'brócoli y aceite de oliva.\n'
                 '2. Mezclar con 1 ⅓ tazas de espagueti integral.\n'
                 'Carbohidrato integral + proteína de lata: opción '
                 'económica en la ventana de recuperación.\n'
                 + FUENTE_GENERAL),
    },
    {
        'nombre': 'Huevos con frijoles y tortillas',
        'tiempo': 'Posentreno 1-2 h',
        'ing': [(C('Huevo entero fresco'), 3),
                (C('Frijoles refritos, caseros o enlatados'), 2),
                (C('Tortilla de maíz'), 3)],
        'prep': ('Administración: 1-2 h después de entrenar.\n'
                 '1. Cocinar 3 huevos al gusto.\n'
                 '2. Calentar 2 equivalentes de frijoles y 3 tortillas.\n'
                 '3. Armar tacos o servir aparte.\n'
                 'Frijol + tortilla = proteína complementaria del maíz '
                 'con la leguminosa, con los carbohidratos que el músculo '
                 'necesita para reponer glucógeno.\n'
                 + FUENTE_GENERAL),
    },
    {
        'nombre': 'Pollo deshebrado con pasta integral',
        'tiempo': 'Posentreno 1-2 h',
        'ing': [(C('Pollo deshebrado'), 3.5),
                (C('Pasta integral cocida'), 4), (C('Jitomate bola'), 1),
                (C('Cebolla blanca rebanada'), 0.5),
                (C('Aceite de oliva extra virgen'), 1)],
        'prep': ('Administración: 1-2 h después de entrenar.\n'
                 '1. Guisar jitomate y cebolla con aceite de oliva; '
                 'mezclar con 3.5 equivalentes de pollo deshebrado.\n'
                 '2. Combinar con 1 ⅓ tazas de pasta integral.\n'
                 'Comida completa de recuperación: proteína magra, '
                 'carbohidrato integral y verdura (plato del buen comer '
                 'aplicado al post-entreno).\n'
                 + FUENTE_GENERAL),
    },
]


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    catalogo = cargar_catalogo(con)
    if not DRY:
        respaldo = DB.replace(
            '.db', f'_respaldo_posentreno_{datetime.now():%Y%m%d_%H%M%S}.db')
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
            "('posentreno_fuente', ?) ON CONFLICT(clave) DO UPDATE SET "
            "valor = excluded.valor", (FUENTE_GENERAL,))

    con.close()
    print(f'\n{FUENTE_GENERAL}')
    print('LISTO')
    return 0


if __name__ == '__main__':
    sys.exit(main())
