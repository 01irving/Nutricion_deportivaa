# -*- coding: utf-8 -*-
"""Re-parsea localmente TODOS los PDF ya descargados en D:\\Biblioteca\\menu
con el parser vigente y reconstruye _extraccion_smae/_datos_smae.json desde
cero (sin red). Tambien re-extrae las fotos de cada platillo."""
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _descargar_pdfs_smae import parse_pdf, normalizar, SALIDA, DATOS

CARPETA_PDF = Path(r'D:\Biblioteca\menu')

def main():
    pdfs = sorted(CARPETA_PDF.glob('*.pdf'))
    print('PDF encontrados: %d' % len(pdfs), flush=True)
    datos = {'menus': {}, 'platillos': {}}
    errores = 0
    for n, pdf in enumerate(pdfs):
        m = re.match(r'^(\d+)_(.*)\.pdf$', pdf.name)
        id_menu = m.group(1) if m else pdf.stem
        nombre_menu = (m.group(2).replace('_', ' ') if m else pdf.stem)
        try:
            pend = ['']
            parse_pdf(pdf, datos, pend, nombre_menu)
        except Exception as e:
            errores += 1
            print('  ERROR %s: %s' % (pdf.name[:50], str(e)[:90]), flush=True)
        if (n + 1) % 50 == 0:
            print('  %d/%d | menus %d | platillos %d' % (
                n + 1, len(pdfs), len(datos['menus']), len(datos['platillos'])),
                flush=True)
    DATOS.parent.mkdir(exist_ok=True)
    DATOS.write_text(json.dumps(datos, ensure_ascii=False), encoding='utf-8')
    print('RE-PARSE COMPLETO: %d menus, %d platillos, %d errores' % (
        len(datos['menus']), len(datos['platillos']), errores))
    print('guardado en %s' % DATOS)

if __name__ == '__main__':
    main()
