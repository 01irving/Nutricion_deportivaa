# -*- coding: utf-8 -*-
"""
Carga el «menusemanal1» — menú semanal de gimnasio (3 veces/semana) con
platillos mexicanos adaptados al SMAE.

Patrón del documento base ("Menú general para persona que acude 3 veces a
la semana al gimnasio", 2700 kcal, hombre adulto ~80 kg):

* Semana de 7 días × 5 tiempos (Desayuno, Colación Matutina, Comida,
  Colación Vespertina, Cena).
* Desayunos "a escoger" entre 3 opciones; colaciones fijas; comida y cena
  diarias; fruta en cada comida principal.
* Menús parecidos consultados para el diseño (proteína en cada toma,
  hidratos alrededor del entrenamiento):
  - alimmenta.com — "Menú semanal para ganar masa muscular y lista de la
    compra" (7 días, desayuno/colación/comida/cena).
  - sportlife / sabervivir — menús semanales de masa muscular con
    colaciones de yogurt griego y frutos secos.

Uso:
    python cargar_menusemanal1.py [--dry-run]

* Cada ingrediente es un alimento del SMAE con su número de equivalentes;
  la cantidad casera (cantidad_txt) se calcula como
  equivalentes × cantidad sugerida SMAE.
* Inserta/actualiza los platillos por nombre + tiempo y guarda la plantilla
  semanal «menusemanal1 · Gimnasio 3x/semana (SMAE mexicano)» en
  menus_guardados (upsert por nombre, como cargar_menu_gimnasio.py).
"""
import json
import os
import shutil
import sqlite3
import sys
import unicodedata

RUTA = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(RUTA, 'Nutrición_deportiva.db')
DRY = '--dry-run' in sys.argv

SUBGRUPOS = [
    "Verduras", "Frutas", "Cereales sin grasa", "Cereales con grasa",
    "Leguminosas", "AOA MBAG", "AOA BAG", "AOA MAG", "AOA AAG",
    "Leche descremada", "Leche semidescremada", "Leche entera",
    "Leche con azúcar", "Aceites y grasas",
    "Aceites y grasas con proteina", "Azucares sin grasa",
    "Azucares con grasa",
]
SUB_IDX = {g: i for i, g in enumerate(SUBGRUPOS)}

MICROS = ('fibra_g', 'azucar_g', 'vitamina_a_ug', 'vitamina_c_mg',
          'acido_folico_ug', 'hierro_mg', 'calcio_mg', 'potasio_mg',
          'sodio_mg')
MACROS = ('energia_kcal', 'proteina_g', 'lipidos_g', 'hc_g')
CAMPOS = MACROS + MICROS

FRACCIONES = [(0.0, ''), (0.125, '⅛'), (0.25, '¼'), (1 / 3, '⅓'),
              (0.375, '⅜'), (0.5, '½'), (0.625, '⅝'), (2 / 3, '⅔'),
              (0.75, '¾'), (0.875, '⅞'), (1.0, '')]


def normalizar(s):
    s = unicodedata.normalize('NFKD', str(s or '').strip().lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.split())


def cantidad_casera(eq, cantidad_sugerida, unidad):
    """Equivalentes × porción SMAE en medida casera: '1⅓ tazas', '150 g'."""
    total = eq * (cantidad_sugerida or 0)
    u = ' '.join(str(unidad or '').lower().split())
    if u in ('g', 'gr', 'gramos', 'ml'):
        return f'{round(total)} {"ml" if u == "ml" else "g"}'
    entero = int(total)
    resto = total - entero
    valor, frac = min(FRACCIONES, key=lambda f: abs(f[0] - resto))
    if abs(valor - resto) > 0.04:
        numero = f'{total:.1f}'.rstrip('0').rstrip('.')
    else:
        if valor == 1.0:
            entero += 1
        numero = (str(entero) if entero else '') + frac or '0'
    if total > 1.04 and u:
        palabras = u.split(' ')
        if palabras[0][-1] in 'aeiou':
            palabras[0] += 's'
        u = ' '.join(palabras)
    return f'{numero} {u}'.strip()


def cargar_catalogo(con):
    catalogo = {}
    for r in con.execute(
        'SELECT grupo, alimento, cantidad_sugerida, unidad, peso_bruto_g, '
        'peso_neto_g, ' + ', '.join(CAMPOS) + ' FROM smae_alimentos'
    ):
        if r['grupo'] not in SUB_IDX:   # libres / alcohol: fuera del menú
            continue
        catalogo[normalizar(r['alimento'])] = {
            'alimento': r['alimento'],
            'grupo': r['grupo'],
            'subgrupo_idx': SUB_IDX[r['grupo']],
            'unidad': r['unidad'] or '',
            'cantidad_sugerida': float(r['cantidad_sugerida'] or 0),
            'peso_bruto_g': float(r['peso_bruto_g'] or 0),
            'peso_neto_g': float(r['peso_neto_g'] or 0),
            **{c: float(r[c] or 0) for c in CAMPOS},
        }
    return catalogo


def C(nombre):
    """Referencia a un alimento del catálogo SMAE por nombre."""
    return ('cat', nombre)


def X(nombre, grupo, cantidad, unidad, peso, energia, prot, lip, hc,
      fibra=0, azucar=0, va=0, vc=0, fol=0, fe=0, ca=0, k=0, na=0):
    """Alimento con valores por equivalente que no está en el catálogo."""
    return ('custom', {
        'alimento': nombre, 'grupo': grupo, 'subgrupo_idx': SUB_IDX[grupo],
        'unidad': unidad, 'cantidad_sugerida': cantidad,
        'peso_bruto_g': peso, 'peso_neto_g': peso,
        'energia_kcal': energia, 'proteina_g': prot, 'lipidos_g': lip,
        'hc_g': hc, 'fibra_g': fibra, 'azucar_g': azucar,
        'vitamina_a_ug': va, 'vitamina_c_mg': vc, 'acido_folico_ug': fol,
        'hierro_mg': fe, 'calcio_mg': ca, 'potasio_mg': k, 'sodio_mg': na,
    })


# --- Alimentos que el catálogo SMAE no trae (valores por equivalente) -----
YOGURT_DESCREMADO = X('Yogurt natural descremado', 'Leche descremada', 1,
                      'taza', 245, 127, 13.0, 0.4, 17.4, 0, 17.4, 66, 1.4,
                      17, 0.1, 450, 579, 126)

ACEITE = C('Aceite de oliva extra virgen')   # 1 eq = 1 cucharadita

# ===========================================================================
# PLATILLOS MEXICANOS — ing: (alimento SMAE, equivalentes)
# ===========================================================================
PLATILLOS = [
    # ------------------------------ DESAYUNOS ----------------------------- #
    {
        'nombre': 'Avena con leche, plátano y amaranto',
        'tiempo': 'Desayuno', 'img': '',
        'ing': [(C('Avena cocida'), 3), (C('Leche descremada'), 2),
                (C('Platano'), 1), (C('Amaranto tostado'), 1)],
        'prep': ('Opción 1 de desayuno (a escoger).\n'
                 '1. Cocer la avena en la leche descremada con un chorrito '
                 'de agua 3-4 minutos.\n'
                 '2. Servir en un tazón con las rebanadas de plátano.\n'
                 '3. Espolvorear el amaranto tostado y canela al gusto.\n'
                 '4. Acompañar con café o té sin azúcar.\n'
                 'Base: menú semanal de masa muscular (alimmenta.com); '
                 'amaranto como cereal mexicano.'),
    },
    {
        'nombre': 'Huevos rancheros ligeros con frijol',
        'tiempo': 'Desayuno', 'img': '',
        'ing': [(C('Tortilla de maíz'), 3), (C('Huevo entero fresco'), 2),
                (C('Jitomate bola'), 1), (C('Cebolla blanca rebanada'), 0.5),
                (C('Chile serrano'), 0.2), (C('Frijoles enteros enlatados'),
                                            1.5), (ACEITE, 1.5),
                (C('Mandarina reyna'), 1)],
        'prep': ('Opción 2 de desayuno (a escoger).\n'
                 '1. Calentar las tortillas (tostar 20 s por lado en un '
                 'comal; se pueden passar por el aceite ligeramente).\n'
                 '2. Licuar el jitomate con cebolla, chile serrano y sal '
                 'para la salsa; hervir 5 minutos.\n'
                 '3. Cocinar los huevos estrellados con el aceite.\n'
                 '4. Montar: tortillas, huevo encima, salsa ranchera y '
                 'frijol de la olla al lado.\n'
                 'Base: desayuno de gimnasio del documento; versión '
                 'mexicana ligera.'),
    },
    {
        'nombre': 'Molletes integrales con queso panela',
        'tiempo': 'Desayuno', 'img': '',
        'ing': [(C('Pan integral'), 3),
                (C('Frijoles refritos, caseros o enlatados'), 2),
                (C('Queso panela'), 1.5), (C('Salsa de chile'), 0.5),
                (C('Naranja sin semilla'), 1), (ACEITE, 0.5)],
        'prep': ('Opción 3 de desayuno (a escoger).\n'
                 '1. Abrir el pan integral por la mitad y tostarlo.\n'
                 '2. Untar los frijoles refritos (sin manteca).\n'
                 '3. Cubrir con el queso panela desmoronado y gratinar 3 '
                 'minutos en el horno o comal.\n'
                 '4. Terminar con salsa de chile; acompañar con la naranja '
                 'y café o té.\n'
                 'Clásico mexicano adaptado: pan integral en lugar de '
                 'bolillo; frijol sin manteca.'),
    },
    # --------------------------- COLACIÓN MATUTINA ------------------------ #
    {
        'nombre': 'Yogurt con granola y papaya',
        'tiempo': 'Colación Matutina', 'img': '',
        'ing': [(YOGURT_DESCREMADO, 1), (C('Granola baja en grasa'), 1),
                (C('Papaya picada'), 2)],
        'prep': ('Colación matutina fija (como la «media mañana» del '
                 'documento).\n'
                 '1. Servir el yogurt natural descremado.\n'
                 '2. Agregar 1½ cucharadas de granola baja en grasa.\n'
                 '3. Acompañar con la papaya picada (o fruta de temporada).\n'
                 'Base: documento del menú; fruta mexicana de temporada.'),
    },
    # ------------------------------- COMIDAS ------------------------------ #
    {
        'nombre': 'Sopa de fideo con jitomate',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Pasta integral cocida'), 1.5), (C('Jitomate bola'), 1),
                (C('Cebolla blanca rebanada'), 0.25), (ACEITE, 1)],
        'prep': ('1. Licuar el jitomate con cebolla y media taza de agua; '
                 'colar.\n'
                 '2. Calentar el aceite y acitronar el fideo integral '
                 '(cocido) un minuto.\n'
                 '3. Agregar la salsa y el caldo; hervir 8 minutos y '
                 'sazonar.\n'
                 'Nota: el SMAE registra la pasta cocida; 1 eq = ½ taza.\n'
                 'Plato mexicano diario; base del documento.'),
    },
    {
        'nombre': 'Pollo a la mexicana',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Pechuga de pollo sin piel a la plancha'), 4),
                (C('Jitomate bola'), 1), (C('Cebolla blanca rebanada'), 0.5),
                (C('Chile serrano'), 0.2), (C('Cilantro picado crudo'), 0.1),
                (ACEITE, 1)],
        'prep': ('1. Cortar la pechuga en tiras y cocinar a la plancha con '
                 'el aceite, 5-6 minutos.\n'
                 '2. Agregar el jitomate picado, la cebolla y el chile '
                 'serrano; saltear 3 minutos.\n'
                 '3. Terminar con cilantro picado y sal.\n'
                 '120 g de proteína magra por ración (4 eq × 30 g).'),
    },
    {
        'nombre': 'Arroz rojo',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Arroz cocido'), 3), (C('Jitomate bola'), 0.5),
                (ACEITE, 0.5)],
        'prep': ('1. Licuar el jitomate con un poco de agua y colar.\n'
                 '2. Acitronar el arroz cocido con el aceite y agregar la '
                 'salsa.\n'
                 '3. Hervir 5 minutos a fuego bajo hasta que tome color '
                 'rojo; sazonar.\n'
                 '½ taza de arroz cocido por equivalente (SMAE).'),
    },
    {
        'nombre': 'Ensalada de nopales asados con queso panela',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Nopal cocido'), 2), (C('Jitomate bola'), 0.5),
                (C('Cebolla de cambray sin raíz'), 0.5), (C('Queso panela'),
                                                          1), (ACEITE, 1)],
        'prep': ('1. Asar los nopales en un comal hasta que suelten su '
                 'baba; enjuagar y cortar.\n'
                 '2. Mezclar con jitomate, cebollitas de cambray asadas y '
                 'el queso panela en cuadritos.\n'
                 '3. Aderezar con el aceite, limón, orégano y sal.\n'
                 'Guarnición mexicana con base verde (como las ensaladas '
                 'del documento).'),
    },
    {
        'nombre': 'Rajas poblanas con elote y crema ligera',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Chile poblano'), 2),
                (C('Elote amarillo desgranado cocido'), 1),
                (C('Crema ligera'), 1.5), (C('Cebolla blanca rebanada'), 0.5),
                (ACEITE, 0.5)],
        'prep': ('1. Tostar los chiles poblanos, envolverlos en una bolsa '
                 'para sudarlos y pelarlos; quitar venas y semillas.\n'
                 '2. Cortar en rajas y acitronar con la cebolla y el '
                 'aceite.\n'
                 '3. Agregar el elote desgranado y la crema ligera; cocinar '
                 '5 minutos a fuego bajo.\n'
                 'Clásico mexicano con crema ligera (menos grasa).'),
    },
    {
        'nombre': 'Frijoles de la olla',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Frijoles enteros enlatados'), 2),
                (C('Cebolla blanca rebanada'), 0.25), (ACEITE, 0.5)],
        'prep': ('1. Calentar los frijoles con su caldo (o de la olla) con '
                 'la cebolla y el aceite.\n'
                 '2. Machacar ligeramente, sazonar y servir calientes.\n'
                 '1½ eq ≈ ¾ de taza: hidrato + proteína vegetal de la '
                 'comida.'),
    },
    {
        'nombre': 'Arroz integral con ejotes y zanahoria',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Arroz integral cocido'), 3),
                (C('Ejotes cocidos picados'), 1.5),
                (C('Zanahoria picada cruda'), 0.5), (ACEITE, 1)],
        'prep': ('1. Saltear la zanahoria con el aceite 2 minutos.\n'
                 '2. Agregar los ejotes picados y el arroz integral.\n'
                 '3. Sazonar con sal y pimienta; servir caliente.\n'
                 'Cereal integral del día (como la quinoa/arroz integral '
                 'del documento).'),
    },
    {
        'nombre': 'Pescado a la veracruzana',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Filete de robalo'), 4), (C('Jitomate bola'), 1.5),
                (C('Cebolla blanca rebanada'), 1), (C('Chile jalapeño'),
                                                   0.25),
                (C('Aguacate mediano'), 1), (ACEITE, 1.5)],
        'prep': ('1. Sazonar los filetes con sal y pimienta.\n'
                 '2. En una sartén, acitronar la cebolla con el aceite; '
                 'agregar jitomate picado y rodajas de jalapeño.\n'
                 '3. Acomodar el pescado encima, tapar y cocinar a fuego '
                 'bajo 10-12 minutos.\n'
                 '4. Servir con el caldillo de jitomate.\n'
                 '150 g de pescado por ración (como el documento).'),
    },
    {
        'nombre': 'Sopa azteca ligera',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Tortilla de maíz'), 2), (C('Jitomate bola'), 1),
                (C('Cebolla blanca rebanada'), 0.5), (C('Chile pasilla'),
                                                     0.5), (C('Queso panela'),
                                                            0.5),
                (C('Aguacate mediano'), 1), (ACEITE, 1)],
        'prep': ('1. Tostar el chile pasilla y freírlo un momento en el '
                 'aceite; licuar con el jitomate, la cebolla y agua.\n'
                 '2. Hervir el caldo con la salsa 10 minutos.\n'
                 '3. Servir con tiras de tortilla de maíz tostada, queso '
                 'panela desmoronado y el aguacate en cubos.\n'
                 'Versión ligera: tortilla horneada (no frita).'),
    },
    {
        'nombre': 'Pechuga en salsa de chile morita',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Pechuga de pollo sin piel a la plancha'), 5),
                (C('Chile Morita'), 0.5), (C('Jitomate bola'), 0.5),
                (ACEITE, 0.5)],
        'prep': ('1. Desvenar y remojar el chile morita en agua caliente '
                 '10 minutos; licuar con el jitomate.\n'
                 '2. Cocinar la salsa a fuego bajo 5 minutos con el '
                 'aceite.\n'
                 '3. Salsear la pechuga a la plancha y servir.\n'
                 'Proteína magra con salsa mexicana de bajo aporte '
                 'calórico.'),
    },
    {
        'nombre': 'Tinga de pollo',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Pollo deshebrado'), 3), (C('Jitomate bola'), 1),
                (C('Cebolla blanca rebanada'), 1),
                (C('Chile chipotle seco'), 0.25), (ACEITE, 1.5)],
        'prep': ('1. Acitronar la cebolla en plumas con el aceite.\n'
                 '2. Agregar el jitomate licuado con el chipotle; cocinar '
                 '8 minutos.\n'
                 '3. Incorporar el pollo deshebrado y hervir 5 minutos.\n'
                 '4. Servir con arroz y lechuga.\n'
                 'Clásico mexicano; 3 eq ≈ 90-120 g de pollo.'),
    },
    {
        'nombre': 'Arroz blanco',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Arroz cocido'), 2.5)],
        'prep': ('½ taza de arroz cocido por equivalente: 2 eq = 1 taza.\n'
                 'Hidrato de la comida; cocer con cebolla y ajo al gusto '
                 'sin grasa extra.'),
    },
    {
        'nombre': 'Lentejas guisadas',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Lenteja cocida'), 3.5), (C('Cebolla blanca rebanada'),
                                             0.5), (C('Jitomate bola'), 0.5),
                (C('Zanahoria picada cruda'), 0.5), (C('Chile serrano'),
                                                    0.2), (ACEITE, 1)],
        'prep': ('1. Acitronar cebolla, zanahoria y chile con el '
                 'aceite.\n'
                 '2. Agregar el jitomate picado y las lentejas cocidas con '
                 'un poco de su caldo.\n'
                 '3. Hervir 10 minutos y sazonar.\n'
                 'Leguminosa del día (el documento usa crema de judías '
                 'blancas; aquí al estilo mexicano).'),
    },
    {
        'nombre': 'Mojarra empapelada con verduras',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Filete de mojarra'), 4), (C('Jitomate bola'), 0.5),
                (C('Cebolla blanca rebanada'), 0.25), (C('Chile poblano'),
                                                      1),
                (C('Calabacita alargada cruda'), 0.5), (ACEITE, 0.5)],
        'prep': ('1. Colocar el filete en papel aluminio con las verduras '
                 'en juliana, el aceite, limón y sal.\n'
                 '2. Cerrar el paquete y hornear a 180 °C por 15 minutos.\n'
                 '3. Abrir en la mesa (papillote mexicano).\n'
                 '150 g de pescado blanco por ración.'),
    },
    {
        'nombre': 'Sopa de conchitas con verduras',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Pasta integral cocida'), 2),
                (C('Zanahoria picada cruda'), 0.5),
                (C('Calabacita alargada cruda'), 0.5), (C('Jitomate bola'),
                                                       0.5), (ACEITE, 0.5)],
        'prep': ('1. Acitronar la conchita integral con el aceite 1 '
                 'minuto.\n'
                 '2. Agregar el caldo de pollo y las verduras picadas.\n'
                 '3. Hervir 10 minutos; sazonar.\n'
                 'Sopa mexicana de entrada (pasta integral para más '
                 'fibra).'),
    },
    {
        'nombre': 'Chile relleno de queso panela en caldillo',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Chile poblano'), 2), (C('Queso panela'), 2),
                (C('Huevo entero fresco'), 1.5), (C('Jitomate bola'), 1),
                (C('Cebolla blanca rebanada'), 0.25), (ACEITE, 1)],
        'prep': ('1. Tostar y pelar los chiles; abrir una ranura y quitar '
                 'semillas.\n'
                 '2. Rellenar con el queso panela en tiras.\n'
                 '3. Rebozar con el huevo batido (solo clara si se '
                 'prefiere) y cocinar en comal con el aceite.\n'
                 '4. Servir bañados en el caldillo de jitomate.\n'
                 'Clásico mexicano horneado/comal (no frito) para cuidar '
                 'grasas.'),
    },
    # --------------------------- COLACIÓN VESPERTINA ---------------------- #
    {
        'nombre': 'Frutos secos con yogurt griego',
        'tiempo': 'Colación Vespertina', 'img': '',
        'ing': [(C('Almendra'), 2.5), (C('Nuez'), 2.5),
                (C('Yogurt griego'), 1)],
        'prep': ('Colación vespertina fija (como la merienda del '
                 'documento: frutos secos + yogurt griego).\n'
                 '1. Servir el yogurt griego natural.\n'
                 '2. Agregar las almendras y las nueces picadas.\n'
                 'Sin azúcar añadido.'),
    },
    {
        'nombre': 'Tortillas de maíz al comal',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Tortilla de maíz'), 2)],
        'prep': ('2 tortillas de maíz calientes al comal para acompañar '
                 'el guisado (hidrato de la comida, estilo mexicano).'),
    },
    # -------------------------------- CENAS ------------------------------- #
    {
        'nombre': 'Quesadillas integrales de queso panela',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Tortilla de harina integral'), 4),
                (C('Queso panela Lala Light'), 2), (C('Lechuga Romana'),
                                                    0.5),
                (C('Salsa de chile'), 0.5), (ACEITE, 0.5)],
        'prep': ('1. Calentar las tortillas integrales en el comal con el '
                 'queso panela encima hasta fundir.\n'
                 '2. Doble y servir con lechuga y salsa de chile.\n'
                 'Cena ≥1.5-2 h antes de dormir (nota del documento).'),
    },
    {
        'nombre': 'Gelatina sin azúcar',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Gelatina'), 1)],
        'prep': ('1. Preparar la gelatina sin azúcar según el empaque y '
                 'refrigerar hasta cuajar.\n'
                 'Nota: el SMAE solo trae gelatina con azúcar (1 eq de '
                 'azúcares); con versión light el aporte real es menor.\n'
                 'Postre ligero del documento.'),
    },
    {
        'nombre': 'Tostadas de atún con aguacate',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Tortilla de maíz'), 2), (C('Atún en aceite drenado'), 2),
                (C('Aguacate mediano'), 1), (C('Jitomate bola'), 0.5),
                (C('Lechuga Romana'), 0.5), (C('Limon real'), 0.25)],
        'prep': ('1. Horneadas las tortillas de maíz hasta quedar crujientes '
                 '(o usar tostadas horneadas).\n'
                 '2. Mezclar el atún con el limón y esparcir sobre las '
                 'tostadas.\n'
                 '3. Cubrir con lechuga, jitomate y rebanadas de '
                 'aguacate.\n'
                 'Versión mexicana del «sándwich de atún» del documento.'),
    },
    {
        'nombre': 'Omelette de hongos y espinaca',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Huevo entero fresco'), 2), (C('Hongos crudos'), 1),
                (C('Espinaca cruda'), 1), (C('Queso panela Lala Light'), 1),
                (ACEITE, 1)],
        'prep': ('1. Saltear los hongos y la espinaca con el aceite 3 '
                 'minutos.\n'
                 '2. Batir los huevos, verter en el sartén antiadherente y '
                 'cocinar a fuego medio.\n'
                 '3. Rellenar con las verduras y el queso panela; doblar.\n'
                 'Como la tortilla francesa del documento, con relleno '
                 'mexicano.'),
    },
    {
        'nombre': 'Frijoles refritos light',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Frijoles refritos, caseros o enlatados'), 1.5),
                (C('Queso panela Lala Light'), 0.5), (ACEITE, 0.5)],
        'prep': ('1. Calentar los frijoles refritos (sin manteca) con el '
                 'aceite.\n'
                 '2. Servir con el queso panela desmoronado encima.\n'
                 'Guarnición proteica de la cena.'),
    },
    {
        'nombre': 'Sopa de verduras con calabacita',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Calabacita alargada cruda'), 1),
                (C('Zanahoria picada cruda'), 0.5), (C('Coliflor cruda'), 1),
                (C('Jitomate bola'), 0.5), (ACEITE, 0.5)],
        'prep': ('1. Picar las verduras y cocerlas en caldo 10 minutos.\n'
                 '2. Acitronar el jitomate con el aceite y agregar a la '
                 'sopa.\n'
                 '3. Sazonar y servir caliente.\n'
                 'Como las sopas de verduras del documento.'),
    },
    {
        'nombre': 'Tacos de pescado estilo Ensenada ligeros',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Tortilla de maíz'), 2), (C('Filete de mojarra'), 3),
                (C('Col cruda picada'), 0.5), (C('Crema ligera'), 0.5),
                (C('Aguacate mediano'), 0.5), (C('Limon real'), 0.25),
                (ACEITE, 0.5)],
        'prep': ('1. Sazonar el pescado y cocinarlo a la plancha con el '
                 'aceite (sin capear).\n'
                 '2. Calentar las tortillas y armar los tacos: pescado, '
                 'col rebanada, crema ligera y aguacate.\n'
                 '3. Terminar con limón y salsa al gusto.\n'
                 'Versión ligera del taco de pescado (sin empanizado).'),
    },
    {
        'nombre': 'Tacos ligeros de tinga de pollo',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Tortilla de maíz'), 3), (C('Pollo deshebrado'), 2),
                (C('Jitomate bola'), 0.5), (C('Cebolla blanca rebanada'),
                                            0.5),
                (C('Chile chipotle seco'), 0.15), (C('Lechuga Romana'), 0.5),
                (ACEITE, 0.5)],
        'prep': ('1. Preparar la tinga (ver receta de Comida) con la mitad '
                 'de los ingredientes.\n'
                 '2. Calentar las tortillas y armar los tacos con lechuga '
                 'picada.\n'
                 '3. Acompañar con agua natural o té sin azúcar.'),
    },
    {
        'nombre': 'Sándwich integral de pechuga de pavo',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Pan integral'), 3), (C('Pechuga de pavo'), 2),
                (C('Jitomate bola'), 0.5), (C('Lechuga Romana'), 0.5),
                (C('Aguacate mediano'), 0.5), (C('Limon real'), 0.25)],
        'prep': ('1. Tostar el pan integral.\n'
                 '2. Armar el sándwich con la pechuga de pavo, jitomate, '
                 'lechuga y el aguacate machacado con limón (en lugar de '
                 'mayonesa).\n'
                 'Como el «sándwich de lomo en papillote» del documento, '
                 'con pavo magro.'),
    },
    {
        'nombre': 'Enchiladas verdes ligeras',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Tortilla de maíz'), 3), (C('Pollo deshebrado'), 2),
                (C('Tomate verde'), 2), (C('Chile serrano'), 0.25),
                (C('Crema ligera'), 0.5), (C('Queso panela Lala Light'),
                                          0.5),
                (C('Cebolla blanca rebanada'), 0.25), (ACEITE, 1)],
        'prep': ('1. Hervir el tomate verde con el chile serrano 5 '
                 'minutos; licuar con la cebolla y sal.\n'
                 '2. Cocinar la salsa 5 minutos con el aceite.\n'
                 '3. Pasar las tortillas por la salsa caliente, rellenar '
                 'con el pollo y doblar.\n'
                 '4. Servir con hilos de crema ligera y queso panela.\n'
                 'Cena mexicana de domingo, horneada y sin freír.'),
    },
    # ------------------------------ FRUTAS -------------------------------- #
    {
        'nombre': 'Fruta: melón',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Melon picado'), 2)],
        'prep': ('2 tazas de melón picado como postre.\n'
                 '1 eq de fruta = 1 taza picada (SMAE).'),
    },
    {
        'nombre': 'Fruta: papaya',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Papaya picada'), 1.5)],
        'prep': ('1½ tazas de papaya picada como postre de la comida.'),
    },
    {
        'nombre': 'Fruta: sandía',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Sandia picada'), 2)],
        'prep': ('2 tazas de sandía picada como postre de la comida.'),
    },
    {
        'nombre': 'Fruta: mango',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Mango ataulfo'), 1)],
        'prep': ('Mango ataulfo (½ pieza por equivalente) como postre.'),
    },
    {
        'nombre': 'Fruta: guayaba',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Guayaba'), 2)],
        'prep': ('6 guayabas por equivalente; 2 eq como postre.'),
    },
    {
        'nombre': 'Fruta: tuna',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Tuna'), 1)],
        'prep': ('2 tunas por equivalente; postre de temporada.'),
    },
    {
        'nombre': 'Fruta: manzana',
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Manzana'), 1)],
        'prep': ('1 manzana (1 eq de fruta) como postre.'),
    },
    {
        'nombre': 'Fruta: pera',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Pera'), 2)],
        'prep': ('1 eq = ½ pera; 2 eq = 1 pera de postre.'),
    },
    {
        'nombre': 'Fruta: fresas',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Fresa rebanada'), 2)],
        'prep': ('2 tazas de fresas rebanadas como postre de la cena.'),
    },
    {
        'nombre': 'Fruta: naranja',
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Naranja sin semilla'), 2)],
        'prep': ('2 naranjas sin semilla (2 eq de fruta) como postre.'),
    },
]

# ===========================================================================
# PLANTILLA SEMANAL (grilla del documento: 7 días × 5 tiempos)
# ===========================================================================
TIEMPOS = ['Desayuno', 'Colación Matutina', 'Comida', 'Colación Vespertina',
           'Cena']
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado',
        'Domingo']

DESAYUNOS = {
    'Lunes': 'Avena con leche, plátano y amaranto',
    'Martes': 'Huevos rancheros ligeros con frijol',
    'Miércoles': 'Molletes integrales con queso panela',
    'Jueves': 'Avena con leche, plátano y amaranto',
    'Viernes': 'Huevos rancheros ligeros con frijol',
    'Sábado': 'Molletes integrales con queso panela',
    'Domingo': 'Avena con leche, plátano y amaranto',
}
COLACION_MATUTINA = ['Yogurt con granola y papaya']
COLACION_VESPERTINA = ['Frutos secos con yogurt griego']

COMIDAS = {
    'Lunes': ['Sopa de fideo con jitomate', 'Pollo a la mexicana',
              'Arroz rojo', 'Tortillas de maíz al comal', 'Fruta: melón'],
    'Martes': ['Ensalada de nopales asados con queso panela',
               'Rajas poblanas con elote y crema ligera',
               'Frijoles de la olla', 'Arroz blanco', 'Fruta: papaya'],
    'Miércoles': ['Arroz integral con ejotes y zanahoria',
                  'Pescado a la veracruzana', 'Fruta: sandía'],
    'Jueves': ['Sopa azteca ligera', 'Pechuga en salsa de chile morita',
               'Arroz blanco', 'Tortillas de maíz al comal', 'Fruta: mango'],
    'Viernes': ['Tinga de pollo', 'Arroz blanco',
                'Tortillas de maíz al comal', 'Fruta: guayaba'],
    'Sábado': ['Lentejas guisadas', 'Mojarra empapelada con verduras',
               'Tortillas de maíz al comal', 'Fruta: tuna'],
    'Domingo': ['Sopa de conchitas con verduras',
                'Chile relleno de queso panela en caldillo', 'Arroz blanco',
                'Tortillas de maíz al comal', 'Fruta: manzana'],
}

CENAS = {
    'Lunes': ['Quesadillas integrales de queso panela',
              'Gelatina sin azúcar', 'Fruta: papaya'],
    'Martes': ['Tostadas de atún con aguacate', 'Fruta: naranja'],
    'Miércoles': ['Omelette de hongos y espinaca', 'Frijoles refritos light',
                  'Fruta: pera', 'Fruta: tuna'],
    'Jueves': ['Sopa de verduras con calabacita',
               'Tacos de pescado estilo Ensenada ligeros'],
    'Viernes': ['Tacos ligeros de tinga de pollo', 'Fruta: melón'],
    'Sábado': ['Sándwich integral de pechuga de pavo', 'Fruta: fresas'],
    'Domingo': ['Enchiladas verdes ligeras', 'Fruta: melón'],
}

NOMBRE_PLANTILLA = 'menusemanal1 · Gimnasio 3x/semana (SMAE mexicano)'


def construir_ingredientes(p, catalogo):
    ingredientes, tot = [], {c: 0.0 for c in CAMPOS}
    for (tipo, ref), eq in p['ing']:
        if tipo == 'cat':
            base = catalogo.get(normalizar(ref))
            if base is None:
                raise KeyError(f'"{ref}" no está en el SMAE ({p["nombre"]})')
        else:
            base = ref
        reg = {'subgrupo_idx': base['subgrupo_idx'], 'eq_cantidad': eq}
        for c in CAMPOS:
            reg[c] = round(float(base[c] or 0), 3)
            tot[c] += reg[c] * eq
        reg.update({
            'alimento': base['alimento'],
            'grupo': base['grupo'],
            'unidad': base['unidad'],
            'cantidad_sugerida': base['cantidad_sugerida'],
            'peso_bruto_g': base['peso_bruto_g'],
            'peso_neto_g': base['peso_neto_g'],
            'cantidad_txt': cantidad_casera(
                eq, base['cantidad_sugerida'], base['unidad']),
            'conv': f'{eq:g} eq',
        })
        ingredientes.append(reg)
    return ingredientes, {c: round(tot[c], 2) for c in CAMPOS}


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    catalogo = cargar_catalogo(con)
    if not DRY:
        shutil.copy(DB, DB.replace('.db', '_respaldo_menusemanal1.db'))

    filas = []
    for p in PLATILLOS:
        ingredientes, tot = construir_ingredientes(p, catalogo)
        filas.append({**p, 'ingredientes': ingredientes, 'totales': tot})
    por_nombre = {f['nombre']: f['ingredientes'] for f in filas}

    for f in filas:
        print(f'  {f["tiempo"]:19} | {f["nombre"]:52} | '
              f'{f["totales"]["energia_kcal"]:5.0f} kcal')
        for r in f['ingredientes']:
            print(f'        {r["eq_cantidad"]:>5g} eq  {r["cantidad_txt"]:16} '
                  f'{r["alimento"]}')
    if DRY:
        con.close()
        return 0

    with con:
        for f in filas:
            datos = (json.dumps(f['ingredientes'], ensure_ascii=False),
                     json.dumps(f['totales'], ensure_ascii=False), f['prep'])
            fila = con.execute(
                'SELECT id_platillo FROM platillos WHERE nombre = ? AND '
                'tiempo_comida = ?', (f['nombre'], f['tiempo'])).fetchone()
            if fila:
                con.execute(
                    'UPDATE platillos SET ingredientes = ?, totales = ?, '
                    'modo_preparacion = ?, '
                    "actualizado_en = datetime('now', 'localtime') "
                    'WHERE id_platillo = ?',
                    datos + (fila[0],))
            else:
                con.execute(
                    'INSERT INTO platillos (nombre, tiempo_comida, '
                    'ingredientes, totales, modo_preparacion, '
                    'imagen_nombre, imagen_blob, creado_en, actualizado_en) '
                    "VALUES (?, ?, ?, ?, ?, NULL, NULL, "
                    "datetime('now', 'localtime'), "
                    "datetime('now', 'localtime'))",
                    (f['nombre'], f['tiempo']) + datos)

    # plantilla semanal (7 días × 5 tiempos)
    dias, kcal_dias = {}, []
    for dia in DIAS:
        tiempos = [[DESAYUNOS[dia]], COLACION_MATUTINA, COMIDAS[dia],
                   COLACION_VESPERTINA, CENAS[dia]]
        plats, alimentos, total = {}, {}, 0.0
        for i, nombres in enumerate(tiempos):
            plats[str(i)] = ' + '.join(nombres)
            lista = []
            for n in nombres:
                ings = por_nombre.get(n)
                if ings is None:
                    raise KeyError(f'platillo ausente: {n} ({dia})')
                lista.extend(dict(r) for r in ings)
            alimentos[str(i)] = lista
            total += sum(r['energia_kcal'] * r['eq_cantidad'] for r in lista)
        dias[dia] = {'platillos': plats, 'alimentos': alimentos}
        kcal_dias.append(total)
        print(f'  {dia}: {total:.0f} kcal')
    kcal = sum(kcal_dias) / len(kcal_dias)
    with con:
        con.execute('DELETE FROM menus_guardados WHERE nombre = ?',
                    (NOMBRE_PLANTILLA,))
        con.execute(
            'INSERT INTO menus_guardados (nombre, kcal, detalle, creado_en) '
            "VALUES (?, ?, ?, datetime('now', 'localtime'))",
            (NOMBRE_PLANTILLA, round(kcal), json.dumps(
                {'tiempos': TIEMPOS, 'dias': dias}, ensure_ascii=False)))
    con.close()
    print(f'PLANTILLA: {NOMBRE_PLANTILLA} | {kcal:.0f} kcal/día promedio')
    print('LISTO')
    return 0


if __name__ == '__main__':
    sys.exit(main())
