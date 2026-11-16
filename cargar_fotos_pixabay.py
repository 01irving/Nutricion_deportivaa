# -*- coding: utf-8 -*-
"""
Descarga fotos de Pixabay para los platillos, platillo por platillo,
eligiendo la mejor coincidencia por nombre y guardándolas en la BD.

* Usa la API OFICIAL de Pixabay (clave gratuita de pixabay.com); el
  scraping del sitio viola sus términos y no se hace.
* Solo reemplaza las ilustraciones generadas y las fotos de Commons
  anteriores; las fotos originales del usuario quedan intactas.
* Coincidencia: términos del platillo en español + traducción al
  inglés, puntúa los 'tags' y el nombre de cada resultado y elige el
  de mayor puntaje. El crédito (fotógrafo y Pixabay) queda en
  imagen_nombre e imagenes_creditos.json.
* Reanudable y con respaldo automático de la BD.

Uso:
    python cargar_fotos_pixabay.py --pixabay-key CLAVE
         [--db <ruta>] [--dry-run] [--max N] [--tiempo "Comida"]
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
KEY = sys.argv[sys.argv.index('--pixabay-key') + 1] if '--pixabay-key' in sys.argv else None
if '--db' in sys.argv:
    DB = sys.argv[sys.argv.index('--db') + 1]

API = 'https://pixabay.com/api/'
UA = 'NutricionDeportiva-img-loader/1.0'
PAUSA = 1.2          # la API gratuita permite ~100 peticiones por minuto
ANCHO = 640

# traducciones español -> inglés para buscar en Pixabay (catálogo en
# inglés con fotos de comida de todo el mundo)
ES_EN = {
    'pollo': 'chicken', 'arroz': 'rice', 'atún': 'tuna', 'atun': 'tuna',
    'huevo': 'egg', 'huevos': 'eggs', 'batido': 'smoothie',
    'licuado': 'smoothie', 'ensalada': 'salad', 'sopa': 'soup',
    'pasta': 'pasta', 'espagueti': 'spaghetti', 'espaguetí': 'spaghetti',
    'tacos': 'tacos', 'taco': 'tacos', 'pescado': 'fish', 'res': 'beef',
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
    'pera': 'pear', 'kiwi': 'kiwi', 'mango': 'mango',
    'whey': 'protein shake', 'crema': 'cream soup', 'caldo': 'broth',
    'pozole': 'pozole', 'mole': 'mole', 'tamales': 'tamales',
    'chilaquiles': 'chilaquiles', 'enchiladas': 'enchiladas',
    'hamburguesa': 'hamburger', 'burrito': 'burrito',
    'quesadilla': 'quesadilla', 'flan': 'flan', 'ceviche': 'ceviche',
    'guacamole': 'guacamole', 'elote': 'corn', 'esquites': 'corn',
    'champiñones': 'mushrooms', 'camote': 'sweet potato',
    'jamaica': 'hibiscus tea', 'agua': 'agua fresca drink',
    'frutas': 'fruit', 'fruta': 'fruit', 'atole': 'atole',
    'barrita': 'protein bar', 'galletas': 'cookies', 'jitomate': 'tomato',
    'tostada': 'toast', 'papa': 'potato', 'pepino': 'cucumber',
    'calabacitas': 'grilled zucchini', 'calabacita': 'zucchini',
    'espárragos': 'asparagus', 'esparrazos': 'asparagus',
    'compota': 'fruit compote', 'sincronizadas': 'quesadilla ham cheese',
    'toronja': 'grapefruit', 'romero': 'rosemary',
    'aguacate': 'avocado', 'dátil': 'dates', 'datil': 'dates',
    'dátiles': 'dates', 'maca': 'maca powder', 'chía': 'chia pudding',
    'chia': 'chia pudding', 'lasaña': 'lasagna', 'lasagna': 'lasagna',
    'espinaca': 'spinach', 'frutos rojos': 'berries',
    'menta': 'mint tea', 'hierbabuena': 'mint tea',
    'nueces': 'walnuts', 'nuez': 'walnuts', 'almendras': 'almonds',
    'almendra': 'almonds', 'cítricos': 'citrus fruits',
    'citricos': 'citrus fruits', 'tuna': 'prickly pear cactus fruit',
    'vapor': 'steamed', 'asadas': 'grilled', 'asado': 'grilled',
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
    for p in palabras:
        if p in ES_EN:
            return p
    return palabras[0] if palabras else ''


def terminos_pixabay(palabras):
    """Términos para la API: español principal traducido + resto."""
    en = [ES_EN.get(p, p) for p in palabras[:3]]
    return ' '.join(en)


def peticion(url, reintentos=3):
    for intento in range(reintentos):
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        try:
            with urllib.request.urlopen(req, timeout=30, context=CTX_SSL) as r:
                return json.load(r)
        except urllib.error.HTTPError as error:
            if error.code == 429 and intento < reintentos - 1:
                espera = 30 * (intento + 1)
                print(f'    429: espero {espera}s...')
                time.sleep(espera)
                continue
            raise
    return {}


def limpiar_html(s):
    return re.sub(r'<[^>]+>', '', str(s or '')).strip()


def mejor_para(nombre):
    """Busca en Pixabay y regresa la foto con mayor puntaje de
    coincidencia con las palabras del platillo. Primer intento exigiendo
    el alimento principal; si nadie pasa, reintento aceptando la mejor
    coincidencia por palabras clave (sin exigir principal)."""
    palabras = palabras_de(nombre)
    if not palabras:
        return None
    principal = principal_de(palabras)
    principal_en = ES_EN.get(principal, principal)
    termino = terminos_pixabay(palabras)

    def buscar(termino, exigir_principal):
        params = {
            'key': KEY, 'q': termino, 'image_type': 'photo',
            'category': 'food', 'safesearch': 'true', 'per_page': '8',
            'order': 'popular',
        }
        data = peticion(API + '?' + urllib.parse.urlencode(params))
        hits = data.get('hits') or []
        mejor, mejor_score = None, 0
        for h in hits:
            texto = f"{h.get('tags', '')} {h.get('user', '')}".lower()
            score = 0
            for p in palabras[:4]:
                en = ES_EN.get(p, '')
                if p in texto or (en and en in texto):
                    score += 2
            if exigir_principal:
                if principal_en in texto:
                    score += 3
                else:
                    continue
            score += min((h.get('downloads') or 0) // 5000, 1)
            if score > mejor_score:
                mejor, mejor_score = h, score
        if mejor is None or mejor_score < 3:
            return None
        url = mejor.get('largeImageURL') or mejor.get('webformatURL')
        return {
            'url': url,
            'tags': mejor.get('tags') or '',
            'autor': mejor.get('user') or 'desconocido',
            'titulo': f"{mejor.get('tags', '')} (Pixabay #{mejor.get('id')})",
        }

    foto = buscar(termino, True)
    if not foto:
        # reintento: mismos términos sin exigir el alimento principal
        time.sleep(PAUSA)
        foto = buscar(termino, False)
    if not foto:
        # reintento final: solo las dos palabras clave
        cortas = palabras[:2]
        if len(cortas) >= 2:
            time.sleep(PAUSA)
            foto = buscar(terminos_pixabay(cortas), False)
    return foto


def descargar(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60, context=CTX_SSL) as r:
        datos = r.read()
    imagen = Image.open(io.BytesIO(datos)).convert('RGB')
    imagen.thumbnail((640, 640))
    bufer = io.BytesIO()
    imagen.save(bufer, 'JPEG', quality=82)
    return bufer.getvalue()


def main():
    if not KEY:
        print('Falta la clave: regístrate gratis en pixabay.com, abre '
              'https://pixabay.com/api/docs/ y copia tu KEY.')
        print('Uso: python cargar_fotos_pixabay.py --pixabay-key CLAVE '
              '[--db <ruta>] [--dry-run] [--max N] [--tiempo "Comida"]')
        return 1

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    if not DRY:
        respaldo = DB.replace(
            '.db', f'_respaldo_pixabay_{datetime.now():%Y%m%d_%H%M%S}.db')
        import shutil
        shutil.copy(DB, respaldo)
        print(f'Respaldo: {respaldo}')

    # solo reemplaza ilustraciones y fotos de Commons; las fotos
    # originales del usuario (113) quedan intactas
    consulta = ('SELECT id_platillo, nombre, tiempo_comida FROM platillos '
                "WHERE imagen_blob IS NULL OR imagen_nombre LIKE "
                "'Ilustración generada%' OR imagen_nombre LIKE "
                "'%Wikimedia Commons%'")
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
        foto = mejor_para(f['nombre'])
        if not foto:
            sin_encontrar.append(f['nombre'])
            print(f'  SIN COINCIDENCIA | {f["nombre"][:50]}')
            time.sleep(PAUSA)
            continue
        if DRY:
            print(f'  DRY | {f["nombre"][:36]:36} | '
                  f'{foto["tags"][:52]}')
            time.sleep(PAUSA)
            continue
        try:
            blob = descargar(foto['url'])
        except Exception as error:
            print(f'  DESCARGA FALLO ({foto["tags"][:40]}): {error}')
            time.sleep(5)
            continue
        atribucion = (f"Foto: {foto['autor']} — Pixabay ({foto['tags'][:60]})")
        with con:
            con.execute(
                'UPDATE platillos SET imagen_blob = ?, imagen_nombre = ?, '
                "actualizado_en = datetime('now', 'localtime') "
                'WHERE id_platillo = ?',
                (sqlite3.Binary(blob), atribucion, f['id_platillo']))
        creditos[f['nombre']] = {
            'fuente': 'Pixabay',
            'autor': foto['autor'],
            'tags': foto['tags'],
            'url': foto['url'],
            'platillo': f['nombre'],
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        descargadas += 1
        print(f'  OK {descargadas:3} | {f["nombre"][:36]:36} | '
              f'{foto["tags"][:52]}')
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
