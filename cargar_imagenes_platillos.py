# -*- coding: utf-8 -*-
"""
Busca en Wikimedia Commons imágenes que COINCIDAN con el nombre de cada
platillo (mejor coincidencia por puntuación, en español e inglés) y las
guarda como imagen_blob con el crédito de autor y licencia.

* Solo reemplaza las ilustraciones generadas y fotos de Commons
  anteriores; las fotos originales del usuario quedan intactas.
* El título de la foto debe contener el alimento principal del platillo
  (en español o su traducción al inglés, que da muchos más resultados).
* Puntuación: suma los aciertos de palabras clave en el título y elige
  la mejor; si nadie pasa el umbral, el platillo queda como está.
* Atribución en imagen_nombre e imagenes_creditos.json.
* Reanudable (los que ya tienen foto de Commons se re-buscan solo si se
  pasa --rehacer-todas; por defecto solo ilustraciones y Commons).

Uso:
    python cargar_imagenes_platillos.py [--db <ruta>] [--dry-run]
         [--max N] [--tiempo "Posentreno"] [--desde-creditos]
"""
import io
import json
import os
import re
import sqlite3
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

from PIL import Image

import certifi

CTX_SSL = ssl.create_default_context(cafile=certifi.where())

RUTA = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(RUTA, 'Nutrición_deportiva.db')
DRY = '--dry-run' in sys.argv
MAX = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else None
SOLO = sys.argv[sys.argv.index('--tiempo') + 1] if '--tiempo' in sys.argv else None
REHACER = '--rehacer-todas' in sys.argv
if '--db' in sys.argv:
    DB = sys.argv[sys.argv.index('--db') + 1]
DESDE_CREDITOS = '--desde-creditos' in sys.argv

API = 'https://commons.wikimedia.org/w/api.php'
UA = 'NutricionDeportiva-img-loader/1.0 (app profesional de nutricion)'
PAUSA = 1.0
ANCHO = 480

# traducciones español -> inglés para buscar en Commons (los títulos en
# inglés son mucho más numerosos)
ES_EN = {
    'pollo': 'chicken', 'arroz': 'rice', 'atún': 'tuna', 'atun': 'tuna',
    'huevo': 'egg', 'huevos': 'eggs', 'batido': 'smoothie',
    'licuado': 'smoothie', 'ensalada': 'salad', 'sopa': 'soup',
    'pasta': 'pasta', 'espagueti': 'spaghetti', 'espaguetí': 'spaghetti',
    'tacos': 'tacos', 'taco': 'taco', 'pescado': 'fish', 'res': 'beef',
    'frijoles': 'beans', 'frijol': 'beans', 'tortilla': 'tortilla',
    'plátano': 'banana', 'platano': 'banana', 'fresa': 'strawberry',
    'fresas': 'strawberries', 'manzana': 'apple', 'naranja': 'orange',
    'mandarina': 'mandarin', 'papaya': 'papaya', 'guayaba': 'guava',
    'uva': 'grape', 'uvas': 'grapes', 'salmón': 'salmon', 'salmon': 'salmon',
    'camarón': 'shrimp', 'camarones': 'shrimp', 'queso': 'cheese',
    'jamón': 'ham', 'pavo': 'turkey', 'cerdo': 'pork', 'lomo': 'pork loin',
    'avena': 'oatmeal', 'pan': 'bread', 'verduras': 'vegetables',
    'brócoli': 'broccoli', 'zanahoria': 'carrot', 'leche': 'milk',
    'yogurt': 'yogurt', 'lentejas': 'lentils', 'garbanzo': 'chickpeas',
    'sandía': 'watermelon', 'melon': 'melon', 'melón': 'melon',
    'pera': 'pear', 'kiwi': 'kiwi', 'mango': 'mango', 'guayaba': 'guava',
    'whey': 'protein shake', 'crema': 'cream soup', 'caldo': 'broth',
    'pozole': 'pozole', 'mole': 'mole', 'tamales': 'tamales',
    'chilaquiles': 'chilaquiles', 'enchiladas': 'enchiladas',
    'hamburguesa': 'hamburger', 'burrito': 'burrito',
    'quesadilla': 'quesadilla', 'flan': 'flan', 'ceviche': 'ceviche',
    'guacamole': 'guacamole', 'elote': 'corn', 'esquites': 'corn',
    'champiñones': 'mushrooms', 'camote': 'sweet potato',
    'jamaica': 'hibiscus water', 'agua': 'agua fresca',
    'frutas': 'fruit', 'papilla': 'baby food', 'atole': 'atole',
    'barrita': 'protein bar', 'galletas': 'cookies', 'jitomate': 'tomato',
    'carnitas': 'carnitas', 'salsa': 'salsa', 'tostada': 'toast',
}

STOP = {
    'de', 'con', 'y', 'al', 'en', 'sin', 'la', 'el', 'los', 'las', 'a',
    'para', 'del', 'taza', 'tazas', 'pieza', 'piezas', 'cucharada',
    'cucharadita', 'rebanada', 'rebanadas', 'lata', 'vaso', 'vasos',
    'integral', 'natural', 'descremada', 'equivalentes', 'eq', 'menú',
    'menu', 'segunda', 'primera', 'tercera', 'cuarta', 'opción', 'opcion',
}


def normalizar(s):
    s = s.lower()
    s = re.sub(r'\(([^)]*)\)', ' ', s)      # quita "(Menú 3 · Segunda)"
    s = s.replace('·', ' ')
    return s


def palabras_de(nombre):
    limpio = normalizar(nombre)
    return [p for p in re.split(r'[\s,]+', limpio)
            if p and p not in STOP and not p.isdigit()]


def principal_de(palabras):
    """El alimento principal del platillo (el primero que esté en el
    diccionario de traducciones)."""
    for p in palabras:
        if p in ES_EN:
            return p
    return palabras[0] if palabras else ''


def limpiar_html(s):
    return re.sub(r'<[^>]+>', '', str(s or '')).strip()


def peticion(params, reintentos=3):
    url = API + '?' + urllib.parse.urlencode(params)
    for intento in range(reintentos):
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        try:
            with urllib.request.urlopen(req, timeout=25,
                                        context=CTX_SSL) as r:
                return json.load(r)
        except urllib.error.HTTPError as error:
            if error.code == 429 and intento < reintentos - 1:
                espera = 30 * (intento + 1)
                print(f'    429 too many requests: espero {espera}s...')
                time.sleep(espera)
                continue
            raise
    return {}


def descargar(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40, context=CTX_SSL) as r:
        datos = r.read()
    imagen = Image.open(io.BytesIO(datos)).convert('RGB')
    imagen.thumbnail((640, 640))
    bufer = io.BytesIO()
    imagen.save(bufer, 'JPEG', quality=82)
    return bufer.getvalue()


def buscar_candidatos(termino):
    """Busca en Commons y regresa TODOS los JPEG/PNG razonables."""
    params = {
        'action': 'query', 'format': 'json',
        'generator': 'search', 'gsrsearch': termino + ' filetype:bitmap',
        'gsrnamespace': '6', 'gsrlimit': '8',
        'prop': 'imageinfo', 'iiprop': 'url|mime|size|extmetadata',
        'iiurlwidth': str(ANCHO),
    }
    data = peticion(params)
    paginas = list((data.get('query') or {}).get('pages', {}).values())
    paginas.sort(key=lambda p: p.get('index', 99))
    candidatos = []
    for p in paginas:
        titulo = p.get('title') or ''
        bajo = titulo.lower()
        ii = (p.get('imageinfo') or [{}])[0]
        if ii.get('mime') not in ('image/jpeg', 'image/png'):
            continue
        if (ii.get('width') or 0) < 250:
            continue
        malas = ('mapa', 'map ', 'logo', 'bandera', 'escudo', 'diagrama',
                 'diagram', 'icono', 'coat of arms', 'chart', 'drawing',
                 'plant ', 'station', 'beer', 'street')
        if any(m in bajo for m in malas):
            continue
        meta = ii.get('extmetadata') or {}
        candidatos.append({
            'titulo': titulo,
            'url': ii.get('thumburl') or ii.get('url'),
            'autor': limpiar_html((meta.get('Artist') or {}).get('value'))[:80]
                     or 'Autor desconocido',
            'licencia': limpiar_html((meta.get('LicenseShortName') or {})
                                     .get('value'))[:40] or 'Licencia libre',
        })
    return candidatos


def puntuar(candidato, palabras, principal_es, principal_en):
    titulo = re.sub(r'[^a-záéíóúüñ ]', ' ', candidato['titulo'].lower())
    score = 0
    for p in palabras:
        en = ES_EN.get(p, '')
        if p in titulo:
            score += 2
        if en and en in titulo:
            score += 2
    if principal_es and (principal_es in titulo or
                         (principal_en and principal_en in titulo)):
        score += 3   # obligatorio tener el alimento principal
    else:
        return 0
    return score


def mejor_para(nombre):
    """Busca en español e inglés y regresa el candidato con mayor
    puntuación (None si ninguno coincide con el alimento principal)."""
    palabras = palabras_de(nombre)
    if not palabras:
        return None, []
    principal = principal_de(palabras)
    principal_en = ES_EN.get(principal, '')

    mejor_cand, mejor_score = None, 0
    busquedas = [
        (' '.join(palabras[:3]), palabras[:3]),
        (principal_en or principal, [principal_en or principal]),
    ]
    vistos = set()
    for termino, claves in busquedas:
        try:
            for c in buscar_candidatos(termino):
                if c['titulo'] in vistos:
                    continue
                vistos.add(c['titulo'])
                score = puntuar(c, palabras, principal, principal_en)
                if score >= 3 and score > mejor_score:
                    mejor_cand, mejor_score = c, score
        except Exception as error:
            print(f'    BUSQUEDA FALLO ({termino}): {error}')
            time.sleep(10)
        time.sleep(PAUSA)
    return mejor_cand, []


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    if not DRY:
        respaldo = DB.replace(
            '.db', f'_respaldo_fotos_{datetime.now():%Y%m%d_%H%M%S}.db')
        import shutil
        shutil.copy(DB, respaldo)
        print(f'Respaldo: {respaldo}')

    if DESDE_CREDITOS:
        creditos_ruta = os.path.join(RUTA, 'imagenes_creditos.json')
        creditos = json.load(open(creditos_ruta, encoding='utf-8'))
        consulta = ('SELECT id_platillo, nombre, tiempo_comida FROM platillos '
                    "WHERE imagen_blob IS NULL OR imagen_nombre LIKE "
                    "'Ilustración generada%' OR imagen_nombre LIKE "
                    "'%Wikimedia Commons%'")
        filas = con.execute(consulta).fetchall()
        descargadas = 0
        for f in filas:
            entrada = creditos.get(f['nombre'])
            if not entrada or not entrada.get('url'):
                continue
            try:
                blob = descargar(entrada['url'])
            except Exception as error:
                print(f'  DESCARGA FALLO ({f["nombre"][:40]}): {error}')
                continue
            atribucion = (f"{entrada['archivo_comunes'].replace('Archivo:', '')}"
                          f" — {entrada['autor']}, {entrada['licencia']}, "
                          'Wikimedia Commons')
            with con:
                con.execute(
                    'UPDATE platillos SET imagen_blob = ?, imagen_nombre = ?, '
                    "actualizado_en = datetime('now', 'localtime') "
                    'WHERE id_platillo = ?',
                    (sqlite3.Binary(blob), atribucion, f['id_platillo']))
            descargadas += 1
        con.close()
        print(f'aplicadas desde creditos: {descargadas}')
        print('LISTO')
        return 0

    consulta = ('SELECT id_platillo, nombre, tiempo_comida FROM platillos '
                "WHERE imagen_blob IS NULL OR imagen_nombre LIKE "
                "'Ilustración generada%'")
    if REHACER:
        consulta += " OR imagen_nombre LIKE '%Wikimedia Commons%'"
    parametros = []
    if SOLO:
        consulta += ' AND tiempo_comida LIKE ?'
        parametros.append('%' + SOLO + '%')
    consulta += ' ORDER BY tiempo_comida, nombre'
    if MAX:
        consulta += ' LIMIT ?'
        parametros.append(MAX)
    filas = con.execute(consulta, parametros).fetchall()
    print(f'platillos a procesar: {len(filas)}')

    creditos_ruta = os.path.join(RUTA, 'imagenes_creditos.json')
    creditos = {}
    if os.path.exists(creditos_ruta):
        try:
            creditos = json.load(open(creditos_ruta, encoding='utf-8'))
        except Exception:
            creditos = {}
    sin_encontrar = []
    descargadas = 0

    for f in filas:
        candidato, _ = mejor_para(f['nombre'])
        if not candidato:
            sin_encontrar.append(f['nombre'])
            print(f'  SIN COINCIDENCIA | {f["nombre"][:50]}')
            time.sleep(PAUSA)
            continue
        if DRY:
            print(f'  DRY | {f["nombre"][:40]:40} | {candidato["titulo"][:58]}')
            time.sleep(PAUSA)
            continue
        try:
            blob = descargar(candidato['url'])
        except Exception as error:
            print(f'  DESCARGA FALLO ({candidato["titulo"][:40]}): {error}')
            time.sleep(5)
            continue
        atribucion = (f"{candidato['titulo'].replace('Archivo:', '')} — "
                      f"{candidato['autor']}, {candidato['licencia']}, "
                      'Wikimedia Commons')
        with con:
            con.execute(
                'UPDATE platillos SET imagen_blob = ?, imagen_nombre = ?, '
                "actualizado_en = datetime('now', 'localtime') "
                'WHERE id_platillo = ?',
                (sqlite3.Binary(blob), atribucion, f['id_platillo']))
        creditos[f['nombre']] = {
            'archivo_comunes': candidato['titulo'],
            'autor': candidato['autor'],
            'licencia': candidato['licencia'],
            'url': candidato['url'],
            'platillo': f['nombre'],
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        descargadas += 1
        print(f'  OK {descargadas:3} | {f["nombre"][:36]:36} | '
              f'{candidato["titulo"][:52]}')
        time.sleep(PAUSA)

    if not DRY:
        with open(creditos_ruta, 'w', encoding='utf-8') as fh:
            json.dump(creditos, fh, ensure_ascii=False, indent=1)
    con.close()
    print(f'\ndescargadas: {descargadas} | sin coincidencia: '
          f'{len(sin_encontrar)}')
    if sin_encontrar:
        print('platillos sin coincidencia (conservan su imagen actual):')
        for n in sin_encontrar[:20]:
            print('  -', n)
        if len(sin_encontrar) > 20:
            print(f'  ... y {len(sin_encontrar) - 20} más')
    print('LISTO')
    return 0


if __name__ == '__main__':
    sys.exit(main())
