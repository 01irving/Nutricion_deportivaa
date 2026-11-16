# -*- coding: utf-8 -*-
"""
Descarga imágenes libres (Wikimedia Commons) para los platillos que no
tienen foto y las guarda como imagen_blob en la BD.

* Busca por las palabras clave del nombre del platillo en Commons
  (licencias libres: dominio público o CC BY / CC BY-SA).
* Descarga una miniatura de 480-640 px, la convierte a JPEG y la guarda
  como blob; el crédito (título del archivo, autor y licencia) queda en
  imagen_nombre y en imagenes_creditos.json para respetar la atribución.
* Reanudable: los platillos que ya tienen blob se saltan.

Uso:
    python cargar_imagenes_platillos.py [--db <ruta>] [--dry-run]
         [--max N] [--tiempo "Posentreno"]
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

# el almacén de certificados del sistema viene vencido en este equipo:
# se usa el bundle de certifi para verificar TLS
import certifi

CTX_SSL = ssl.create_default_context(cafile=certifi.where())

RUTA = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(RUTA, 'Nutrición_deportiva.db')
DRY = '--dry-run' in sys.argv
MAX = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else None
SOLO = sys.argv[sys.argv.index('--tiempo') + 1] if '--tiempo' in sys.argv else None
if '--db' in sys.argv:
    DB = sys.argv[sys.argv.index('--db') + 1]
# --desde-creditos: aplica al DB actual las imagenes ya resueltas en
# imagenes_creditos.json (por nombre del platillo), sin volver a buscar
DESDE_CREDITOS = '--desde-creditos' in sys.argv

API = 'https://commons.wikimedia.org/w/api.php'
UA = 'NutricionDeportiva-img-loader/1.0 (app profesional de nutricion)'
PAUSA = 1.0          # segundos entre peticiones (cortesía con la API)
ANCHO = 480

STOP = {
    'de', 'con', 'y', 'al', 'en', 'sin', 'la', 'el', 'los', 'las', 'a',
    'para', 'del', 'taza', 'tazas', 'pieza', 'piezas', 'cucharada',
    'cucharadita', 'rebanada', 'rebanadas', 'lata', 'vaso', 'vasos',
    'integral', 'natural', 'descremada', 'equivalentes', 'eq', 'menú',
    'menu', 'segunda', 'primera', 'tercera', 'cuarta', 'opción', 'opcion',
}

PALABRAS_CLAVE_RE = re.compile(r'\(([^)]*)\)|·')


def terminos_busqueda(nombre):
    # quita "(Menú 3 · Segunda)" y similares antes de partir en palabras
    limpio = PALABRAS_CLAVE_RE.sub(' ', nombre)
    palabras = [
        p for p in re.split(r'[\s,]+', limpio.lower())
        if p and p not in STOP and not p.isdigit()
    ]
    return palabras[:3]


def relevant(titulo, palabras):
    """El título de Commons debe contener al menos una palabra clave del
    platillo (evita estaciones de tren y cervezas con 'agua' en el nombre)."""
    t = re.sub(r'[^a-záéíóúüñ ]', ' ', titulo.lower())
    return any(p in t for p in palabras)


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


def limpiar_html(s):
    return re.sub(r'<[^>]+>', '', str(s or '')).strip()


def buscar_imagen(termino, palabras):
    """Busca en Commons y devuelve el primer JPEG/PNG relevante."""
    params = {
        'action': 'query', 'format': 'json',
        'generator': 'search', 'gsrsearch': termino + ' filetype:bitmap',
        'gsrnamespace': '6', 'gsrlimit': '6',
        'prop': 'imageinfo', 'iiprop': 'url|mime|size|extmetadata',
        'iiurlwidth': str(ANCHO),
    }
    data = peticion(params)
    paginas = list((data.get('query') or {}).get('pages', {}).values())
    paginas.sort(key=lambda p: p.get('index', 99))
    for p in paginas:
        titulo = p.get('title') or ''
        ii = (p.get('imageinfo') or [{}])[0]
        if ii.get('mime') not in ('image/jpeg', 'image/png'):
            continue
        if (ii.get('width') or 0) < 250:
            continue
        if not relevant(titulo, palabras):
            continue
        # descarta mapas, logos, diagramas y escudos
        malas = ('mapa', 'map ', 'logo', 'bandera', 'escudo', 'diagrama',
                 'diagram', 'icono', 'coat of arms', 'chart', 'drawing')
        if any(m in titulo.lower() for m in malas):
            continue
        meta = ii.get('extmetadata') or {}
        autor = limpiar_html((meta.get('Artist') or {}).get('value')) or 'Autor desconocido'
        licencia = limpiar_html((meta.get('LicenseShortName') or {}).get('value')) or 'Licencia libre'
        return {
            'titulo': titulo,
            'url': ii.get('thumburl') or ii.get('url'),
            'autor': autor[:80],
            'licencia': licencia[:40],
        }
    return None


def descargar(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40, context=CTX_SSL) as r:
        datos = r.read()
    imagen = Image.open(io.BytesIO(datos)).convert('RGB')
    imagen.thumbnail((640, 640))
    bufer = io.BytesIO()
    imagen.save(bufer, 'JPEG', quality=82)
    return bufer.getvalue()


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    total_sin = con.execute(
        'SELECT COUNT(*) FROM platillos WHERE imagen_blob IS NULL'
    ).fetchone()[0]
    print(f'platillos sin imagen: {total_sin}')

    # reemplaza SOLO las ilustraciones generadas; las fotos originales
    # (113) y cualquier imagen que el usuario haya subido quedan intactas
    consulta = ('SELECT id_platillo, nombre, tiempo_comida FROM platillos '
                "WHERE imagen_blob IS NULL OR imagen_nombre LIKE "
                "'Ilustración generada%'")
    parametros = []
    if SOLO:
        consulta += ' AND tiempo_comida LIKE ?'
        parametros.append('%' + SOLO + '%')
    consulta += ' ORDER BY tiempo_comida, nombre'
    if MAX:
        consulta += ' LIMIT ?'
        parametros.append(MAX)
    filas = con.execute(consulta, parametros).fetchall()

    if DESDE_CREDITOS:
        creditos_ruta = os.path.join(RUTA, 'imagenes_creditos.json')
        creditos = json.load(open(creditos_ruta, encoding='utf-8'))
        descargadas = 0
        sin_creditos = []
        for f in filas:
            entrada = creditos.get(f['nombre'])
            if not entrada or not entrada.get('url'):
                sin_creditos.append(f['nombre'])
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
            print(f'  OK {descargadas:3} | {f["nombre"][:36]:36} | '
                  f'{entrada["archivo_comunes"][:52]}')
            time.sleep(0.3)
        con.close()
        print(f'\naplicadas desde creditos: {descargadas} | sin creditos: '
              f'{len(sin_creditos)}')
        print('LISTO')
        return 0

    creditos_ruta = os.path.join(
        RUTA, 'imagenes_creditos.json'
    )
    creditos = {}
    if os.path.exists(creditos_ruta):
        try:
            creditos = json.load(open(creditos_ruta, encoding='utf-8'))
        except Exception:
            creditos = {}
    sin_encontrar = []
    descargadas = 0

    for f in filas:
        palabras = terminos_busqueda(f['nombre'])
        if not palabras:
            sin_encontrar.append(f['nombre'])
            continue
        termino = ' '.join(palabras)
        try:
            imagen_meta = buscar_imagen(termino, palabras)
        except Exception as error:
            print(f'  BUSQUEDA FALLO ({termino}): {error}')
            time.sleep(10)
            continue
        if not imagen_meta:
            # reintento con menos palabras
            cortas = palabras[:2]
            if len(cortas) >= 2:
                try:
                    time.sleep(1)
                    imagen_meta = buscar_imagen(' '.join(cortas), palabras)
                    time.sleep(PAUSA)
                except Exception:
                    pass
        if not imagen_meta:
            sin_encontrar.append(f['nombre'])
            print(f'  SIN RESULTADO | {f["nombre"][:50]} | ({termino})')
            time.sleep(PAUSA)
            continue
        if DRY:
            print(f'  DRY | {f["nombre"][:40]:40} | {imagen_meta["titulo"][:60]}')
            time.sleep(1)
            continue
        try:
            blob = descargar(imagen_meta['url'])
        except Exception as error:
            print(f'  DESCARGA FALLO ({imagen_meta["titulo"][:40]}): {error}')
            time.sleep(2)
            continue
        atribucion = (f"{imagen_meta['titulo'].replace('Archivo:', '')} — "
                      f"{imagen_meta['autor']}, {imagen_meta['licencia']}, "
                      'Wikimedia Commons')
        with con:
            con.execute(
                'UPDATE platillos SET imagen_blob = ?, imagen_nombre = ?, '
                "actualizado_en = datetime('now', 'localtime') "
                'WHERE id_platillo = ?',
                (sqlite3.Binary(blob), atribucion, f['id_platillo']))
        creditos[f['nombre']] = {
            'archivo_comunes': imagen_meta['titulo'],
            'autor': imagen_meta['autor'],
            'licencia': imagen_meta['licencia'],
            'url': imagen_meta['url'],
            'platillo': f['nombre'],
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        descargadas += 1
        print(f'  OK {descargadas:3} | {f["nombre"][:36]:36} | '
              f'{imagen_meta["titulo"][:52]}')
        time.sleep(PAUSA)

    if not DRY:
        with open(creditos_ruta, 'w', encoding='utf-8') as fh:
            json.dump(creditos, fh, ensure_ascii=False, indent=1)
    con.close()

    print(f'\ndescargadas: {descargadas} | sin resultado: '
          f'{len(sin_encontrar)}')
    if sin_encontrar:
        print('platillos sin imagen encontrada:')
        for n in sin_encontrar[:20]:
            print('  -', n)
        if len(sin_encontrar) > 20:
            print(f'  ... y {len(sin_encontrar) - 20} más')
    print('LISTO')
    return 0


if __name__ == '__main__':
    sys.exit(main())
