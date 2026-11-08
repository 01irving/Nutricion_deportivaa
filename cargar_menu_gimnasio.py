"""
Carga el "Menú general para persona que acude 3 veces/semana al gimnasio"
(PDF) al catálogo de platillos del software, adaptado al español de México
y expresado en equivalentes SMAE.

Uso:
    python cargar_menu_gimnasio.py [--dry-run]

* Cada ingrediente es un alimento del SMAE con su número de equivalentes;
  la cantidad casera (cantidad_txt) se calcula como
  equivalentes × cantidad sugerida SMAE (p. ej. 4 eq × ⅓ taza = 1⅓ tazas).
* Renombra los platillos de la carga anterior (nombres de España) para
  conservar su id, y luego inserta/actualiza por nombre + tiempo.
* Guarda la plantilla semanal (7 días × 5 tiempos) en menus_guardados.
"""
import json
import os
import shutil
import sqlite3
import sys
import unicodedata

RUTA = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(RUTA, 'Nutrición_deportiva.db')
IMG = os.path.join(RUTA, 'img_platillos_nuevo')
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
    """Equivalentes × porción SMAE en medida casera: '1⅓ tazas', '150 g'.

    Usa fracciones unicode y un solo número para que las fichas de
    impresión puedan escalarla (1, 4 y 6 personas)."""
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
YOGURT_NATURAL = X('Yogurt natural entero', 'Leche entera', 1, 'taza', 245,
                   149, 8.5, 8.0, 11.4, 0, 11.4, 66, 1.2, 17, 0.1, 296,
                   380, 113)
YOGURT_GRIEGO = X('Yogurt griego natural sin azúcar', 'Leche entera', 0.5,
                  'taza', 120, 115, 10.6, 5.6, 4.2, 0, 4.2, 30, 0, 8, 0.1,
                  120, 160, 40)

ACEITE = C('Aceite de oliva extra virgen')   # 1 eq = 1 cucharadita

# ===========================================================================
# PLATILLOS — ing: (alimento SMAE, equivalentes)
# ===========================================================================
PLATILLOS = [
    # ------------------------------ DESAYUNO ------------------------------ #
    {
        'nombre': 'Yogurt natural con muesli y fruta',
        'antes': ('Yogur con muesli y fruta de temporada', 'Desayuno'),
        'tiempo': 'Desayuno', 'img': '',
        'ing': [(YOGURT_NATURAL, 0.5), (C('Mueslix con manzana y almendra'),
                                         1), (C('Manzana'), 1)],
        'prep': ('Opción 1 de desayuno.\n'
                 '1. Servir ½ taza de yogurt natural (o kéfir) en un tazón.\n'
                 '2. Agregar ¼ de taza de muesli sin azúcar (o granola).\n'
                 '3. Picar la manzana (o fruta de temporada) encima.\n'
                 '4. Acompañar con café, té o infusión sin azúcar.\n'
                 'Fuente: documento del menú.'),
    },
    {
        'nombre': 'Pan integral tostado con aceite de oliva y jamón',
        'antes': ('Tostada integral con aceite y jamón', 'Desayuno'),
        'tiempo': 'Desayuno', 'img': 'tostada_jamon.jpg',
        'ing': [(C('Pan integral'), 2), (ACEITE, 1), (C('Jamón de pierna'),
                                                      1.5),
                (C('Mandarina reyna'), 1)],
        'prep': ('Opción 2 de desayuno.\n'
                 '1. Tostar las rebanadas de pan integral (o multigrano).\n'
                 '2. Untarlas con la cucharadita de aceite de oliva.\n'
                 '3. Colocar encima las rebanadas de jamón.\n'
                 '4. Acompañar con la fruta y café, leche o té.\n'
                 'Fuente: documento del menú; sapienciaiberica.com.'),
    },
    {
        'nombre': 'Huevos revueltos con jamón, aguacate y pan integral',
        'antes': ('Revuelto de jamón con aguacate y pan', 'Desayuno'),
        'tiempo': 'Desayuno', 'img': 'revuelto_aguacate.jpg',
        'ing': [(C('Huevo entero fresco'), 2), (C('Jamón de pavo'), 1),
                (C('Aguacate California'), 1), (C('Pan de caja integral'), 1),
                (ACEITE, 0.5)],
        'prep': ('Opción 3 de desayuno.\n'
                 '1. Batir los huevos con una pizca de sal.\n'
                 '2. Picar el jamón (o usar pechuga de pavo o atún).\n'
                 '3. Cocinar en sartén antiadherente con el aceite a fuego '
                 'medio, moviendo hasta que cuajen.\n'
                 '4. Servir con el aguacate en rebanadas y el pan tostado; '
                 'acompañar con té o café.\n'
                 'Fuente: documento del menú; myrealfood.app.'),
    },
    # -------------------------- COLACIÓN MATUTINA ------------------------- #
    {
        'nombre': 'Yogurt natural con salvado de avena y fruta',
        'antes': ('Yogur con salvado de avena y fruta', 'Media mañana'),
        'tiempo': 'Colación Matutina', 'img': '',
        'ing': [(YOGURT_NATURAL, 0.5), (C('Salvado de Avena'), 0.67),
                (C('Mandarina reyna'), 1)],
        'prep': ('1. Mezclar ½ taza de yogurt natural con 2 cucharadas de '
                 'salvado de avena.\n'
                 '2. Acompañar con 1 fruta de temporada.\n'
                 'Fuente: documento del menú.'),
    },
    # ------------------------------- COMIDA ------------------------------- #
    {
        'nombre': 'Ensalada verde mixta',
        'antes': ('Ensalada verde mixta', 'Comida'),
        'tiempo': 'Comida', 'img': 'ensalada_verde.jpg',
        'ing': [(C('Arugula cruda'), 0.5), (C('Espinaca cruda picada'), 0.5),
                (C('Jitomate bola'), 1), (C('Pepino con cascara rebanado'),
                                          0.5), (ACEITE, 1)],
        'prep': ('1. Lavar y desinfectar la arúgula y la espinaca (el menú '
                 'pide una base verde distinta a la lechuga).\n'
                 '2. Agregar el jitomate y el pepino en rebanadas.\n'
                 '3. Aderezar con el aceite de oliva, limón o vinagre y '
                 'sal.\n'
                 'Fuente: documento del menú.'),
    },
    {
        'nombre': 'Ensalada de jitomate con albahaca',
        'antes': ('Ensalada de tomate con albahaca', 'Comida'),
        'tiempo': 'Comida', 'img': 'ensalada_tomate.jpg',
        'ing': [(C('Jitomate bola'), 1.5), (ACEITE, 1)],
        'prep': ('1. Rebanar el jitomate maduro.\n'
                 '2. Agregar hojas de albahaca fresca, sal y el aceite de '
                 'oliva.\n'
                 'Fuente: documento del menú.'),
    },
    {
        'nombre': 'Papa cocida en microondas',
        'antes': ('Patata cocida al microondas', 'Comida'),
        'tiempo': 'Comida', 'img': 'pure_patata.jpg',
        'ing': [(C('Papa cocida sin cascara'), 3)],
        'prep': ('1. Lavar la papa y picarla con un tenedor.\n'
                 '2. Envolverla en servilleta húmeda o en un recipiente '
                 'tapado apto para microondas.\n'
                 '3. Cocinar a potencia máxima 8-10 minutos, hasta que esté '
                 'suave al picarla.\n'
                 '4. Servir con perejil picado y sal.\n'
                 'Fuente: documento del menú.'),
    },
    {
        'nombre': 'Gazpacho (sopa fría de jitomate)',
        'antes': ('Gazpacho andaluz', 'Comida'),
        'tiempo': 'Comida', 'img': 'gazpacho.jpg',
        'ing': [(C('Jitomate bola'), 2.5), (C('Pepino con cascara rebanado'),
                                            0.5),
                (C('Pimiento verde crudo chico'), 0.5), (C('Pan blanco'), 1),
                (ACEITE, 1)],
        'prep': ('1. Trocear el jitomate, el pimiento, el pepino y ½ diente '
                 'de ajo.\n'
                 '2. Licuar con el pan remojado, el aceite, un chorrito de '
                 'vinagre y sal hasta que quede terso.\n'
                 '3. Colar (opcional) y refrigerar al menos 1 hora.\n'
                 '4. Servir muy frío (1 vaso), acompañado de pan.\n'
                 'Fuente: directoalpaladar.com — gazpacho andaluz '
                 'tradicional.'),
    },
    {
        'nombre': 'Crema de alubias',
        'antes': ('Crema de judías blancas', 'Comida'),
        'tiempo': 'Comida', 'img': 'crema_judias.jpg',
        'ing': [(C('Alubia cocida (chica o grande)'), 0.75),
                (C('Apio crudo'), 0.25), (C('Cebolla blanca rebanada'), 0.75),
                (ACEITE, 1), (C('leche semidescremada'), 0.25),
                (C('Crema ligera'), 2)],
        'prep': ('Receta del documento (alubias = frijol blanco).\n'
                 '1. Acitronar el apio y la cebolla picados en el aceite.\n'
                 '2. Cuando tomen color, agregar las alubias cocidas y '
                 'escurridas, la leche (o caldo), nuez moscada, sal y '
                 'pimienta; todo menos la crema.\n'
                 '3. Hervir unos 25 minutos.\n'
                 '4. Licuar hasta obtener una crema tersa.\n'
                 '5. Antes de servir, incorporar la crema y mover.\n'
                 'Fuente: documento del menú (receta destacada).'),
    },
    {
        'nombre': 'Puré de papa',
        'antes': ('Puré de patata', 'Comida'),
        'tiempo': 'Comida', 'img': 'pure_patata.jpg',
        'ing': [(C('Papa cocida sin cascara'), 3),
                (C('leche semidescremada'), 0.5), (ACEITE, 1)],
        'prep': ('1. Pelar y cortar la papa en trozos iguales.\n'
                 '2. Cocer en agua con sal unos 20 minutos, hasta que esté '
                 'suave.\n'
                 '3. Escurrir y machacar con la leche caliente.\n'
                 '4. Incorporar el aceite (o mantequilla) y sazonar con sal '
                 'y nuez moscada.\n'
                 'Fuente: recetasdecocina.elmundo.es / '
                 'estoyhechouncocinillas.com.'),
    },
    {
        'nombre': 'Brochetas de langostinos',
        'antes': ('Brochetas de langostinos', 'Comida'),
        'tiempo': 'Comida', 'img': 'brochetas_langostinos.jpg',
        'ing': [(C('langostino'), 1), (ACEITE, 1)],
        'prep': ('1. Mezclar la marinada: ajo machacado, el aceite, '
                 'pimentón, comino, una pizca de chile en polvo y ralladura '
                 'de naranja.\n'
                 '2. Pelar y desvenar los langostinos; salpimentar.\n'
                 '3. Ensartarlos en palitos de brocheta (remojados en agua '
                 'si son de madera).\n'
                 '4. Asar en plancha o parrilla caliente 2-3 minutos por '
                 'lado, barnizando con la marinada, hasta que se pongan '
                 'rosados.\n'
                 'Fuente: bonviveur.com — brochetas de langostinos.'),
    },
    {
        'nombre': 'Pasta integral con champiñones salteados',
        'antes': ('Pasta integral con champiñones salteados', 'Comida'),
        'tiempo': 'Comida', 'img': 'pasta_champinones.jpg',
        'ing': [(C('Pasta integral cocida'), 4),
                (C('Champiñón crudo entero'), 1.5), (ACEITE, 1)],
        'prep': ('1. Cocer la pasta integral en agua con sal según el '
                 'empaque; escurrir y reservar un poco del agua.\n'
                 '2. Saltear los champiñones rebanados con ajo y el aceite '
                 'a fuego alto 4-5 minutos.\n'
                 '3. Mezclar con la pasta y un chorrito del agua de '
                 'cocción; terminar con perejil.\n'
                 'Fuente: recetasdecocina.elmundo.es — pasta con '
                 'champiñones.'),
    },
    {
        'nombre': 'Pechuga de pollo al horno con espárragos',
        'antes': ('Pollo al horno con espárragos verdes', 'Comida'),
        'tiempo': 'Comida', 'img': 'pollo_esparragos.jpg',
        'ing': [(C('Pechuga de pollo sin piel aplanada'), 4),
                (C('Espárragos crudos'), 2), (ACEITE, 1)],
        'prep': ('1. Precalentar el horno a 200 °C.\n'
                 '2. Sazonar la pechuga con sal, pimienta, pimentón, ajo '
                 'picado y la mitad del aceite.\n'
                 '3. Hornear 20-25 minutos.\n'
                 '4. Quitar la parte dura de los espárragos, agregarlos a '
                 'la charola con el resto del aceite, sal y unas gotas de '
                 'limón.\n'
                 '5. Hornear 12-15 minutos más.\n'
                 'Fuente: gastronomiaycia.com.'),
    },
    {
        'nombre': 'Salmón en papillote con cítricos',
        'antes': ('Papillote de salmón a los cítricos', 'Comida'),
        'tiempo': 'Comida', 'img': 'salmon_papillote.jpg',
        'ing': [(C('Salmón'), 5), (C('Poro crudo'), 2),
                (C('Jugo de naranja natural'), 0.5), (ACEITE, 1)],
        'prep': ('Receta del documento.\n'
                 '1. Precalentar el horno a 180 °C.\n'
                 '2. Lavar y rebanar finamente el poro; colocarlo sobre un '
                 'trozo de papel aluminio y poner encima el salmón.\n'
                 '3. Agregar el aceite, sal, ralladura de limón y el jugo '
                 'de naranja.\n'
                 '4. Cerrar el papel sellando bien las orillas.\n'
                 '5. Hornear unos 10 minutos, hasta que el papel se infle.\n'
                 'Fuente: documento del menú (receta destacada).'),
    },
    {
        'nombre': 'Espagueti integral con carne molida magra y verduras',
        'antes': ('Espaguetis integrales con carne magra y verduras',
                  'Comida'),
        'tiempo': 'Comida', 'img': 'espaguetis_carne.jpg',
        'ing': [(C('Espagueti integral cocido'), 4), (C('Filete de res'), 3.5),
                (C('Jitomate bola'), 2), (C('Cebolla blanca rebanada'), 0.5),
                (C('Pimiento rojo crudo chico'), 1), (ACEITE, 1)],
        'prep': ('1. Cocer el espagueti integral en agua con sal; '
                 'escurrir.\n'
                 '2. Acitronar la cebolla, el pimiento y el ajo en el '
                 'aceite.\n'
                 '3. Agregar la carne de res molida magra y dorar.\n'
                 '4. Incorporar el jitomate licuado; cocinar 10 minutos con '
                 'albahaca, sal y pimienta.\n'
                 '5. Mezclar con el espagueti y servir.\n'
                 'Fuente: recetasgratis.net — espaguetis con salsa de '
                 'tomate y carne picada.'),
    },
    {
        'nombre': 'Arroz integral o quinoa con verduras salteadas',
        'antes': ('Arroz integral o quinoa con verduras salteadas', 'Comida'),
        'tiempo': 'Comida', 'img': 'arroz_verduras.jpg',
        'ing': [(C('Arroz integral cocido'), 3),
                (C('Calabacita alargada cruda'), 1),
                (C('Berenjena picada cocida'), 1), (C('Brócoli crudo'), 1),
                (ACEITE, 1.5)],
        'prep': ('1. Cocer el arroz integral 20-25 minutos (o la quinoa '
                 '10-12 minutos).\n'
                 '2. Cortar las verduras en trozos parejos.\n'
                 '3. Saltearlas en wok o sartén grande a fuego alto con el '
                 'aceite, 4-5 minutos, moviendo.\n'
                 '4. Agregar el arroz y unas gotas de salsa de soya; '
                 'saltear 2 minutos más.\n'
                 'Fuente: bonviveur.com — arroz con verduras.'),
    },
    {
        'nombre': 'Filete de pescado blanco al horno o a la plancha',
        'antes': ('Pescado blanco al horno o a la plancha', 'Comida'),
        'tiempo': 'Comida', 'img': 'pescado_papillote.jpg',
        'ing': [(C('Filete de robalo'), 3.75), (ACEITE, 1)],
        'prep': ('Usar robalo, tilapia, huachinango o merluza.\n'
                 '1. Sazonar el filete con sal, pimienta y perejil picado.\n'
                 'Al horno: colocar en una charola con el aceite y limón; '
                 'hornear a 200 °C 12-15 minutos.\n'
                 'A la plancha: dorar 3-4 minutos por lado con el aceite.\n'
                 '2. Servir con limón.\n'
                 'Fuente: recetasgratis.net.'),
    },
    {
        'nombre': 'Ensalada de pasta con calamar',
        'antes': ('Ensalada variada de pasta con sepia', 'Comida'),
        'tiempo': 'Comida', 'img': 'ensalada_pasta.jpg',
        'ing': [(C('Pasta integral cocida'), 4), (C('Calamar crudo'), 3.33),
                (C('Jitomate bola'), 1), (ACEITE, 1.5)],
        'prep': ('1. Cocer la pasta integral, escurrir y dejar enfriar.\n'
                 '2. Secar bien el calamar en cubos y asarlo en plancha a '
                 'fuego alto con ajo y perejil, 2-3 minutos.\n'
                 '3. Saltear un minuto los jitomates cherry.\n'
                 '4. Mezclar todo con el aceite, sal y perejil; servir '
                 'tibia o fría.\n'
                 'Fuente: recetasdecocina.elmundo.es — sepia a la plancha.'),
    },
    {
        'nombre': 'Calamar a la plancha con ajo y perejil',
        'antes': ('Sepia a la plancha con ajo y perejil', 'Comida'),
        'tiempo': 'Comida', 'img': 'sepia_plancha.jpg',
        'ing': [(C('Calamar crudo'), 3.33), (C('Perejil crudo picado'), 0.25),
                (ACEITE, 1)],
        'prep': ('1. Limpiar el calamar, cortarlo en cubos o aros y secarlo '
                 'muy bien con papel.\n'
                 '2. Picar el ajo y el perejil y mezclarlos con el aceite.\n'
                 '3. Asar en plancha muy caliente 2-3 minutos por lado.\n'
                 '4. Bañar con el ajo-perejil y unas gotas de limón.\n'
                 'Fuente: recetasdecocina.elmundo.es / directoalpaladar.com.'),
    },
    # ------------------------- COLACIÓN VESPERTINA ------------------------ #
    {
        'nombre': 'Almendras y nueces con yogurt griego',
        'antes': ('Frutos secos con yogur griego', 'Merienda'),
        'tiempo': 'Colación Vespertina', 'img': '',
        'ing': [(C('Almendra'), 1.5), (C('Nuez'), 1), (YOGURT_GRIEGO, 1)],
        'prep': ('1. Servir las almendras y las nueces naturales o '
                 'tostadas (unos 30 g).\n'
                 '2. Acompañar con ½ taza de yogurt griego sin azúcar.\n'
                 'Fuente: documento del menú.'),
    },
    # -------------------------------- CENA -------------------------------- #
    {
        'nombre': 'Sopa o crema de verduras',
        'antes': ('Puré o sopa de verduras', 'Cena'),
        'tiempo': 'Cena', 'img': 'sopa_verduras.jpg',
        'ing': [(C('Calabacita alargada cruda'), 1),
                (C('Zanahoria picada cruda'), 1), (C('Poro crudo'), 1),
                (C('Acelga cruda'), 0.5), (C('Papa cocida sin cascara'), 1),
                (ACEITE, 1)],
        'prep': ('1. Picar ajo, poro y apio; sofreír en el aceite.\n'
                 '2. Agregar el resto de las verduras en cubos y cubrir con '
                 'agua o caldo.\n'
                 '3. Cocinar a fuego medio 25-30 minutos.\n'
                 '4. Para crema, licuar; para sopa, servir con las verduras '
                 'en trozo.\n'
                 'Fuente: estoyhechouncocinillas.com — sopa de verduras.'),
    },
    {
        'nombre': 'Omelette de atún',
        'antes': ('Tortilla francesa con atún', 'Cena'),
        'tiempo': 'Cena', 'img': 'tortilla_atun.jpg',
        'ing': [(C('Huevo entero fresco'), 2), (C('Atún en agua drenado'), 1),
                (ACEITE, 0.5)],
        'prep': ('1. Escurrir bien el atún y desmenuzarlo.\n'
                 '2. Batir los huevos con una pizca de sal.\n'
                 '3. Mezclar el atún con el huevo.\n'
                 '4. Cocinar en sartén antiadherente con el aceite a fuego '
                 'medio; doblar a la mitad y servir.\n'
                 'Fuente: estoyhechouncocinillas.com — tortilla francesa '
                 'con atún.'),
    },
    {
        'nombre': 'Omelette sencillo',
        'antes': ('Tortilla francesa', 'Cena'),
        'tiempo': 'Cena', 'img': 'tortilla_atun.jpg',
        'ing': [(C('Huevo entero fresco'), 2), (ACEITE, 0.5)],
        'prep': ('1. Batir bien los huevos con una pizca de sal.\n'
                 '2. Cocinar en sartén antiadherente con el aceite a fuego '
                 'medio, 1-2 minutos por lado.\n'
                 '3. Doblar y servir.\n'
                 'Fuente: documento del menú.'),
    },
    {
        'nombre': 'Ensalada de corazones de lechuga',
        'antes': ('Ensalada de cogollos', 'Cena'),
        'tiempo': 'Cena', 'img': 'ensalada_verde.jpg',
        'ing': [(C('Corazón de lechuga crudo'), 1), (ACEITE, 1)],
        'prep': ('1. Lavar, desinfectar y partir los corazones de lechuga.\n'
                 '2. Aderezar con el aceite, limón o vinagre y sal.\n'
                 'Fuente: documento del menú.'),
    },
    {
        'nombre': 'Pescado empapelado con verduras',
        'antes': ('Pescado blanco en papillote con verduras', 'Cena'),
        'tiempo': 'Cena', 'img': 'pescado_papillote.jpg',
        'ing': [(C('Filete de robalo'), 3.75),
                (C('Zanahoria picada cruda'), 1), (C('Poro crudo'), 1),
                (C('Calabacita alargada cruda'), 1), (ACEITE, 1)],
        'prep': ('1. Precalentar el horno a 190 °C.\n'
                 '2. Cortar un rectángulo de papel aluminio o papel para '
                 'hornear y poner las verduras en juliana como cama.\n'
                 '3. Colocar encima el filete sazonado, el aceite, limón y '
                 'hierbas.\n'
                 '4. Cerrar doblando bien las orillas para que no escape el '
                 'vapor.\n'
                 '5. Hornear 12-15 minutos; abrir en la mesa.\n'
                 'Fuente: recetasgratis.net — merluza en papillote con '
                 'verduras.'),
    },
    {
        'nombre': 'Verduras salteadas al wok',
        'antes': ('Verduras salteadas al wok', 'Cena'),
        'tiempo': 'Cena', 'img': 'wok_verduras.jpg',
        'ing': [(C('Calabacita alargada cruda'), 1),
                (C('Berenjena picada cocida'), 1), (C('Brócoli crudo'), 1),
                (C('Pimiento rojo crudo chico'), 1), (ACEITE, 1.5)],
        'prep': ('1. Cortar calabacita, berenjena, brócoli y pimiento en '
                 'trozos parejos.\n'
                 '2. Calentar el wok a fuego alto con el aceite.\n'
                 '3. Saltear 4-5 minutos moviendo; deben quedar al dente.\n'
                 '4. Sazonar con sal, pimienta y unas gotas de salsa de '
                 'soya o limón.\n'
                 'Fuente: bonviveur.com — salteado de verduras.'),
    },
    {
        'nombre': 'Filete de cerdo con costra de perejil',
        'antes': ('Solomillo de cerdo rebozado en perejil', 'Cena'),
        'tiempo': 'Cena', 'img': 'solomillo_perejil.jpg',
        'ing': [(C('Lomo de cerdo'), 3), (C('Perejil crudo picado'), 0.5)],
        'prep': ('Receta del documento.\n'
                 '1. Lavar, secar y picar finamente el perejil.\n'
                 '2. Salpimentar el filete de cerdo entero.\n'
                 '3. Cubrirlo con el perejil, presionando con las manos para '
                 'que se pegue.\n'
                 '4. Cocinar en un recipiente apto para microondas a '
                 'potencia máxima 3 minutos de un lado.\n'
                 '5. Voltear y cocinar 4 minutos más.\n'
                 'Fuente: documento del menú (receta destacada).'),
    },
    {
        'nombre': 'Espárragos con aderezo de aguacate',
        'antes': ('Espárragos blancos con aliño de aguacate', 'Cena'),
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Espárragos crudos'), 2), (C('Aguacate California'), 1),
                (ACEITE, 0.5)],
        'prep': ('1. Cocer los espárragos en agua con sal 3-4 minutos y '
                 'escurrir (los de lata ya vienen cocidos).\n'
                 '2. Machacar el aguacate con el aceite, limón y sal hasta '
                 'que quede cremoso.\n'
                 '3. Servir los espárragos con el aderezo encima.\n'
                 'Fuente: documento del menú.'),
    },
    {
        'nombre': 'Hamburguesa de pescado',
        'antes': ('Hamburguesa de pescado', 'Cena'),
        'tiempo': 'Cena', 'img': 'hamburguesa_pescado.jpg',
        'ing': [(C('Filete de robalo'), 3), (C('Huevo entero fresco'), 0.5),
                (C('Pan molido'), 0.5), (ACEITE, 0.5)],
        'prep': ('1. Picar finamente el pescado y el perejil.\n'
                 '2. Mezclar con sal, ajo en polvo y pimienta.\n'
                 '3. Agregar el huevo batido y el pan molido.\n'
                 '4. Refrigerar la mezcla media hora.\n'
                 '5. Formar la hamburguesa y cocinar a la plancha con el '
                 'aceite, 3-4 minutos por lado.\n'
                 'Fuente: bonviveur.com — hamburguesas de pescado.'),
    },
    {
        'nombre': 'Sándwich de lomo de cerdo al horno',
        'antes': ('Sándwich de lomo en papillote', 'Cena'),
        'tiempo': 'Cena', 'img': 'sandwich_lomo.jpg',
        'ing': [(C('Pan integral'), 2), (C('Lomo de cerdo'), 3),
                (C('Arugula cruda'), 0.25), (C('Jitomate bola'), 0.5),
                (C('Pimiento cocido'), 0.5),
                (C('Cebolla blanca rebanada'), 0.25), (ACEITE, 1)],
        'prep': ('Receta del documento.\n'
                 '1. Salpimentar el lomo entero y envolverlo en papel '
                 'aluminio.\n'
                 '2. Hornear a 180 °C (precalentado) 20-30 minutos, hasta '
                 'que el papel se infle.\n'
                 '3. Dejar enfriar y rebanar.\n'
                 '4. Acitronar la cebolla con el aceite.\n'
                 '5. Armar el sándwich con el pan, arúgula, rebanadas de '
                 'jitomate, pimiento morrón asado, cebolla y el lomo.\n'
                 'Fuente: documento del menú (receta destacada).'),
    },
    {
        'nombre': 'Brochetas de camarón a la plancha',
        'antes': ('Brochetas de gambas a la plancha', 'Cena'),
        'tiempo': 'Cena', 'img': 'brochetas_gambas.jpg',
        'ing': [(C('Camaron crudo mediano'), 2.5), (ACEITE, 1)],
        'prep': ('1. Pelar y desvenar los camarones.\n'
                 '2. Marinar 10-15 minutos en refrigeración con el aceite, '
                 'ajo picado, jugo de limón, sal y pimienta.\n'
                 '3. Ensartar en palitos de brocheta.\n'
                 '4. Asar en plancha muy caliente; voltear cuando cambien '
                 'de color.\n'
                 'Fuente: petitchef.es — brochetas de gambas.'),
    },
    {
        'nombre': 'Calamar baby a la plancha',
        'antes': ('Sepia o chipirón a la plancha', 'Cena'),
        'tiempo': 'Cena', 'img': 'sepia_plancha.jpg',
        'ing': [(C('Chipirón (calamar) crudo'), 3.33),
                (C('Perejil crudo picado'), 0.25), (ACEITE, 1)],
        'prep': ('1. Limpiar los calamares y secarlos muy bien.\n'
                 '2. Asar en plancha muy caliente con el aceite, 2 minutos '
                 'por lado (o en brocheta alternando con camarones).\n'
                 '3. Aderezar con ajo, perejil y unas gotas de limón.\n'
                 'Fuente: recetasdecocina.elmundo.es.'),
    },
    {
        'nombre': 'Jitomate con queso fresco y aceite de oliva',
        'antes': ('Tomate aliñado con queso fresco', 'Cena'),
        'tiempo': 'Cena', 'img': 'ensalada_tomate.jpg',
        'ing': [(C('Jitomate bola'), 2), (C('Queso fresco'), 1), (ACEITE, 1)],
        'prep': ('1. Rebanar el jitomate y acomodarlo en un plato.\n'
                 '2. Desmoronar el queso fresco encima.\n'
                 '3. Aderezar con el aceite, sal y albahaca u orégano.\n'
                 'Fuente: documento del menú.'),
    },
    # --------------------------- POSTRES Y FRUTA -------------------------- #
    {
        'nombre': 'Fruta de temporada',
        'antes': ('Fruta de temporada', 'Comida'),
        'tiempo': 'Comida', 'img': 'macedonia_frutas.jpg',
        'ing': [(C('Manzana'), 1)],
        'prep': ('1 equivalente de fruta de temporada (manzana, mandarina, '
                 'guayaba, papaya…).\n'
                 'Fuente: documento del menú.'),
    },
    {
        'nombre': 'Coctel de frutas natural',
        'antes': ('Macedonia de frutas natural', 'Comida'),
        'tiempo': 'Comida', 'img': 'macedonia_frutas.jpg',
        'ing': [(C('Fresa rebanada'), 0.5), (C('Kiwi'), 0.5),
                (C('Papaya picada'), 0.5)],
        'prep': ('1. Lavar, pelar y picar la fruta.\n'
                 '2. Mezclar con unas gotas de jugo de naranja o limón.\n'
                 '3. Servir frío y sin azúcar.\n'
                 'Fuente: documento del menú.'),
    },
    {
        'nombre': 'Compota de manzana sin azúcar',
        'antes': ('Compota de manzana natural', 'Comida'),
        'tiempo': 'Comida', 'img': '',
        'ing': [(C('Manzana al vapor'), 1)],
        'prep': ('1. Pelar y picar la manzana.\n'
                 '2. Cocer tapada a fuego bajo (o en microondas) 12-15 '
                 'minutos, sin azúcar.\n'
                 '3. Machacar con un tenedor; servir tibia.\n'
                 'Fuente: documento del menú.'),
    },
    {
        'nombre': 'Gelatina light',
        'antes': ('Gelatina sin azúcares añadidos', 'Cena'),
        'tiempo': 'Cena', 'img': '',
        'ing': [(C('Gelatina'), 1)],
        'prep': ('1. Preparar la gelatina sin azúcar según el empaque.\n'
                 '2. Refrigerar 3-4 horas hasta que cuaje.\n'
                 'Nota: el SMAE solo trae gelatina con azúcar; se cuenta '
                 'como 1 equivalente de azúcares. Con gelatina light el '
                 'aporte real es menor.\n'
                 'Fuente: documento del menú.'),
    },
]

# ===========================================================================
# PLANTILLA SEMANAL (grilla del documento)
# ===========================================================================
TIEMPOS = ['Desayuno', 'Colación Matutina', 'Comida', 'Colación Vespertina',
           'Cena']
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado',
        'Domingo']

DESAYUNOS = {
    'Lunes': 'Yogurt natural con muesli y fruta',
    'Martes': 'Pan integral tostado con aceite de oliva y jamón',
    'Miércoles': 'Huevos revueltos con jamón, aguacate y pan integral',
    'Jueves': 'Yogurt natural con muesli y fruta',
    'Viernes': 'Pan integral tostado con aceite de oliva y jamón',
    'Sábado': 'Huevos revueltos con jamón, aguacate y pan integral',
    'Domingo': 'Yogurt natural con muesli y fruta',
}
COLACION_MATUTINA = ['Yogurt natural con salvado de avena y fruta']
COLACION_VESPERTINA = ['Almendras y nueces con yogurt griego']

COMIDAS = {
    'Lunes': ['Ensalada verde mixta', 'Brochetas de langostinos',
              'Papa cocida en microondas', 'Fruta de temporada'],
    'Martes': ['Gazpacho (sopa fría de jitomate)',
               'Pasta integral con champiñones salteados',
               'Pechuga de pollo al horno con espárragos',
               'Fruta de temporada'],
    'Miércoles': ['Crema de alubias', 'Ensalada verde mixta',
                  'Salmón en papillote con cítricos', 'Puré de papa',
                  'Fruta de temporada'],
    'Jueves': ['Ensalada de jitomate con albahaca',
               'Espagueti integral con carne molida magra y verduras',
               'Compota de manzana sin azúcar'],
    'Viernes': ['Arroz integral o quinoa con verduras salteadas',
                'Filete de pescado blanco al horno o a la plancha',
                'Coctel de frutas natural'],
    'Sábado': ['Ensalada de pasta con calamar',
               'Calamar a la plancha con ajo y perejil',
               'Fruta de temporada'],
    # El documento deja vacía la comida del domingo: se repite la del lunes
    'Domingo': ['Ensalada verde mixta', 'Brochetas de langostinos',
                'Papa cocida en microondas', 'Fruta de temporada'],
}

CENAS = {
    'Lunes': ['Sopa o crema de verduras', 'Omelette de atún',
              'Gelatina light'],
    'Martes': ['Ensalada de corazones de lechuga',
               'Pescado empapelado con verduras', 'Fruta de temporada'],
    'Miércoles': ['Verduras salteadas al wok',
                  'Filete de cerdo con costra de perejil',
                  'Fruta de temporada'],
    'Jueves': ['Espárragos con aderezo de aguacate', 'Omelette sencillo',
               'Fruta de temporada'],
    'Viernes': ['Verduras salteadas al wok', 'Hamburguesa de pescado',
                'Fruta de temporada'],
    'Sábado': ['Jitomate con queso fresco y aceite de oliva',
               'Sándwich de lomo de cerdo al horno', 'Fruta de temporada'],
    'Domingo': ['Sopa o crema de verduras', 'Calamar baby a la plancha',
                'Brochetas de camarón a la plancha', 'Fruta de temporada'],
}

NOMBRE_PLANTILLA = 'Gimnasio 3x/semana — menú general (PDF)'


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
        shutil.copy(DB, DB.replace('.db', '_respaldo_menu_gimnasio.db'))

    filas = []
    for p in PLATILLOS:
        ingredientes, tot = construir_ingredientes(p, catalogo)
        filas.append({**p, 'ingredientes': ingredientes, 'totales': tot})

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
        # 1) renombrar la carga anterior (conserva id e imagen)
        for f in filas:
            viejo, tiempo_viejo = f['antes']
            if (viejo, tiempo_viejo) == (f['nombre'], f['tiempo']):
                continue
            ya = con.execute(
                'SELECT 1 FROM platillos WHERE nombre = ? AND '
                'tiempo_comida = ?', (f['nombre'], f['tiempo'])).fetchone()
            if ya:
                con.execute('DELETE FROM platillos WHERE nombre = ? AND '
                            'tiempo_comida = ?', (viejo, tiempo_viejo))
            else:
                con.execute(
                    'UPDATE platillos SET nombre = ?, tiempo_comida = ? '
                    'WHERE nombre = ? AND tiempo_comida = ?',
                    (f['nombre'], f['tiempo'], viejo, tiempo_viejo))
        # 2) insertar / actualizar contenido
        for f in filas:
            blob, img_nombre = None, None
            if f['img']:
                ruta = os.path.join(IMG, f['img'])
                with open(ruta, 'rb') as fh:
                    blob = fh.read()
                img_nombre = f['img']
            datos = (json.dumps(f['ingredientes'], ensure_ascii=False),
                     json.dumps(f['totales'], ensure_ascii=False), f['prep'])
            fila = con.execute(
                'SELECT id_platillo FROM platillos WHERE nombre = ? AND '
                'tiempo_comida = ?', (f['nombre'], f['tiempo'])).fetchone()
            if fila:
                con.execute(
                    'UPDATE platillos SET ingredientes = ?, totales = ?, '
                    'modo_preparacion = ?, '
                    'imagen_nombre = COALESCE(?, imagen_nombre), '
                    'imagen_blob = COALESCE(?, imagen_blob), '
                    "actualizado_en = datetime('now', 'localtime') "
                    'WHERE id_platillo = ?',
                    datos + (img_nombre, blob, fila[0]))
            else:
                con.execute(
                    'INSERT INTO platillos (nombre, tiempo_comida, '
                    'ingredientes, totales, modo_preparacion, imagen_nombre, '
                    'imagen_blob, creado_en, actualizado_en) VALUES '
                    "(?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), "
                    "datetime('now', 'localtime'))",
                    (f['nombre'], f['tiempo']) + datos + (img_nombre, blob))

    # 3) plantilla semanal
    por_nombre = {f['nombre']: f['ingredientes'] for f in filas}
    dias, kcal_dias = {}, []
    for dia in DIAS:
        tiempos = [[DESAYUNOS[dia]], COLACION_MATUTINA, COMIDAS[dia],
                   COLACION_VESPERTINA, CENAS[dia]]
        plats, alimentos, total = {}, {}, 0.0
        for i, nombres in enumerate(tiempos):
            plats[str(i)] = ' + '.join(nombres)
            lista = [dict(r) for n in nombres for r in por_nombre[n]]
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
